"""
MediVerse AI — Document Intelligence Pipeline.
Orchestrates the 12-step document ingestion workflow.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional
from uuid import UUID

from ai_core.engines.ocr_engine import OCREngine, PageText
from ai_core.engines.nlp_engine import NLPEngine
from ai_core.engines.embedding_engine import EmbeddingEngine
from config.settings import get_settings
from config.constants import ProcessingStatus
from core.exceptions import DocumentProcessingError
from database.connection import get_db_session
from database.models.document_model import DocumentModel
from database.models.chunk_model import DocumentChunkModel
from database.repositories.document_repository import DocumentRepository
from database.repositories.chunk_repository import ChunkRepository, ProcessingQueueRepository
from vector_db.collections import MedicalDocumentCollection

logger = logging.getLogger("mediverse.ai.pipeline.document")


class DocumentPipeline:
    """
    Coordinates the ingestion of a medical document:
    Extract text -> OCR -> NLP -> Chunk -> Embed -> Store Postgres -> Store Chroma
    """

    def __init__(
        self,
        ocr_engine: OCREngine,
        nlp_engine: NLPEngine,
        embedding_engine: EmbeddingEngine,
    ) -> None:
        self._ocr = ocr_engine
        self._nlp = nlp_engine
        self._embedding = embedding_engine
        self._settings = get_settings()

    def process_document(
        self,
        document_id: UUID,
        on_progress: Optional[Callable[[int, str], None]] = None,
    ) -> None:
        """
        Execute the full document processing pipeline.
        Updates progress in the database and calls on_progress callback.
        """
        # 1. Fetch document
        with get_db_session() as session:
            doc_repo = DocumentRepository(session)
            queue_repo = ProcessingQueueRepository(session)
            
            doc = doc_repo.get_by_id(document_id)
            queue_item = queue_repo.get_by_document(document_id)
            
            if not doc:
                raise DocumentProcessingError("Initialization", f"Document {document_id} not found")

            doc_repo.update_embedding_status(document_id, ProcessingStatus.PROCESSING)
            
            file_path = doc.file_path
            doc_title = doc.title
            doc_category = doc.category
            
            def report_progress(percent: int, step: str) -> None:
                logger.debug(f"Doc {document_id} progress: {percent}% - {step}")
                if queue_item:
                    queue_repo.update_progress(queue_item.id, percent, step)
                if on_progress:
                    on_progress(percent, step)
                    
            try:
                # 2. Extract Text & OCR
                report_progress(10, "Extracting text and running OCR if needed")
                if doc.file_type == "pdf":
                    pages = self._ocr.extract_text_from_pdf(file_path)
                elif doc.file_type == "txt":
                    pages = self._ocr.extract_text_from_txt(file_path)
                elif doc.file_type in ["png", "jpg", "jpeg", "tiff", "bmp", "gif", "dcm", "dicom"]:
                    pages = self._ocr.extract_text_from_image(file_path)
                else:
                    raise DocumentProcessingError("Text Extraction", f"Unsupported file type: {doc.file_type}")

                if not pages:
                    raise DocumentProcessingError("Text Extraction", "No text extracted from document")

                # 3. NLP & Chunking
                report_progress(30, "NLP analysis and semantic chunking")
                chunks = self._chunk_pages(pages, self._settings.chunk_size, self._settings.chunk_overlap)
                
                if not chunks:
                    raise DocumentProcessingError("Chunking", "Document produced 0 chunks")
                    
                if len(chunks) > self._settings.max_chunks_per_doc:
                    logger.warning(f"Document {document_id} exceeded max chunks. Truncating to {self._settings.max_chunks_per_doc}.")
                    chunks = chunks[:self._settings.max_chunks_per_doc]

                # Run NLP on the full document text (or a sample if too large) to get global doc metadata
                full_text_sample = " ".join([p.text for p in pages[:20]])  # first 20 pages for metadata
                nlp_result = self._nlp.process(full_text_sample, max_keywords=15)
                
                # Update Document metadata in DB
                doc.language = nlp_result.language
                doc.keywords = nlp_result.keywords
                
                # Convert medical entities dict to JSON-serializable list of dicts
                entity_summary = {}
                for label, texts in nlp_result.medical_entities.items():
                    # Take top 10 unique entities per category for document summary
                    entity_summary[label] = list(set(texts))[:10]
                doc.medical_entities = entity_summary
                
                session.flush()

                # 4. Generate Embeddings
                report_progress(50, f"Generating vector embeddings for {len(chunks)} chunks")
                chunk_texts = [c["text"] for c in chunks]
                embeddings = self._embedding.embed_chunks_batch(chunk_texts)

                # 5. Store Metadata in PostgreSQL
                report_progress(80, "Storing metadata in PostgreSQL")
                chunk_repo = ChunkRepository(session)
                
                # Delete existing chunks if this is a re-index
                chunk_repo.delete_by_document(document_id)
                
                db_chunks = []
                for i, (chunk_data, vector) in enumerate(zip(chunks, embeddings)):
                    chunk_id = UUID(int=document_id.int + i) # stable UUID based on doc ID + index
                    db_chunks.append(DocumentChunkModel(
                        id=chunk_id,
                        document_id=document_id,
                        chunk_index=i,
                        content=chunk_data["text"],
                        page_number=chunk_data["page_number"],
                        token_count=len(chunk_data["text"].split()),
                        chroma_id=str(chunk_id)
                    ))
                
                chunk_repo.bulk_add(db_chunks)

                # 6. Store Embeddings in ChromaDB
                report_progress(90, "Storing vectors in ChromaDB")
                chroma_collection = MedicalDocumentCollection()
                
                # Delete old vectors if re-indexing
                chroma_collection.delete_by_document_id(str(document_id))
                
                chroma_ids = [str(c.id) for c in db_chunks]
                chroma_docs = [c.content for c in db_chunks]
                chroma_metadatas = [
                    {
                        "document_id": str(document_id),
                        "chunk_id": str(c.id),
                        "title": doc_title,
                        "category": doc_category,
                        "page_number": c.page_number,
                        "chunk_index": c.chunk_index,
                    }
                    for c in db_chunks
                ]
                
                chroma_collection.add_chunks(
                    ids=chroma_ids,
                    embeddings=embeddings,
                    documents=chroma_docs,
                    metadatas=chroma_metadatas
                )

                # 7. Finalize
                report_progress(100, "Indexing complete")
                doc_repo.update_embedding_status(document_id, ProcessingStatus.COMPLETE, is_indexed=True)
                
                if queue_item:
                    from datetime import datetime
                    queue_item.status = "done"
                    queue_item.completed_at = datetime.utcnow()
                
                logger.info(f"Document {document_id} processed successfully: {len(chunks)} chunks.")

            except Exception as e:
                logger.error(f"Failed to process document {document_id}: {e}")
                doc_repo.update_embedding_status(document_id, ProcessingStatus.FAILED, is_indexed=False)
                if queue_item:
                    queue_repo.update_progress(queue_item.id, 0, "Failed", status="failed")
                    queue_item.error_message = str(e)
                raise DocumentProcessingError("Pipeline Execution", str(e)) from e

    def _chunk_pages(self, pages: list[PageText], chunk_size: int, chunk_overlap: int) -> list[dict]:
        """
        Naive chunking by character count, respecting page boundaries where possible.
        Using LangChain's RecursiveCharacterTextSplitter would be better if we import it,
        but a simple implementation here avoids heavy dependencies in this class.
        """
        chunks = []
        for page in pages:
            text = page.text
            if not text:
                continue
                
            start = 0
            text_len = len(text)
            
            while start < text_len:
                end = start + chunk_size
                
                # If we're not at the end of the text, try to find a natural break point (period or space)
                if end < text_len:
                    # Look back up to chunk_overlap chars for a period
                    break_point = text.rfind('.', start, end)
                    if break_point != -1 and break_point > start + (chunk_size // 2):
                        end = break_point + 1
                    else:
                        # Fallback to space
                        break_point = text.rfind(' ', start, end)
                        if break_point != -1 and break_point > start + (chunk_size // 2):
                            end = break_point
                
                chunk_text = text[start:end].strip()
                if len(chunk_text) > 10: # minimum chunk size
                    chunks.append({
                        "text": chunk_text,
                        "page_number": page.page_number
                    })
                
                start = end - chunk_overlap
                # Prevent infinite loops if overlap >= chunk_size
                if start <= end - chunk_size:
                    start = end

        return chunks
