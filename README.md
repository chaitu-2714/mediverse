# MediVerse AI
## AI-Powered Medical Knowledge Intelligence Platform

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![PySide6](https://img.shields.io/badge/UI-PySide6-green.svg)](https://doc.qt.io/qtforpython-6/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

### Overview

MediVerse AI is an enterprise-grade desktop application for medical knowledge management, document intelligence, and AI-powered semantic search. It enables healthcare professionals, researchers, and medical students to upload, index, search, and understand medical documents using state-of-the-art NLP and Large Language Models.

**This is NOT a diagnosis system. This is NOT a chatbot.**
It is a professional medical knowledge intelligence platform.

---

### Key Features

- **Medical Knowledge Repository** — Categorized storage for WHO/CDC/ICMR guidelines, research papers, medical books, and SOPs
- **AI Document Processing** — Automated text extraction, OCR, NLP entity recognition, and chunking
- **Semantic Search** — Vector-based search returning relevant document chunks with page references
- **RAG-Powered AI Assistant** — Context-grounded responses using Llama 3.2 via Ollama
- **Evidence Engine** — Every AI response is traceable to source documents with similarity scores
- **Role-Based Access** — Admin, Doctor, Researcher, Medical Student roles
- **Enterprise Dashboard** — Real-time stats, analytics, and processing status

---

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Desktop UI | PySide6, Qt Material, QSS |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Vector DB | ChromaDB |
| Authentication | JWT, bcrypt, RBAC |
| LLM | Ollama + Llama 3.2 |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) |
| NLP | spaCy, NLTK, KeyBERT |
| OCR | PyMuPDF, EasyOCR |
| Framework | LangChain, LlamaIndex |

---

### Quick Start

See [INSTALL.md](INSTALL.md) for full installation instructions.

```bash
# 1. Clone and setup
git clone <repo>
cd mediverse_ai

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download NLP models
python -m spacy download en_core_web_sm

# 5. Configure environment
copy .env.example .env
# Edit .env with your PostgreSQL credentials

# 6. Initialize database
alembic upgrade head

# 7. Start Ollama (separate terminal)
ollama serve


# 8. Launch application
python main.py
```

---

### Architecture

See [docs/architecture/system_architecture.md](docs/architecture/system_architecture.md) for full architecture documentation.

---

### License

MIT License — See LICENSE file for details.
