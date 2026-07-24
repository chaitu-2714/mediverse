"""
MediVerse AI — Local loopback callback server for OAuth 2.0.
Runs a lightweight HTTP server on the client machine to capture JWT session redirect payloads from the FastAPI backend.
"""
from __future__ import annotations

import os
import json
import logging
import socket
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional, Callable

from config.settings import get_settings

logger = logging.getLogger("mediverse.auth.oauth_server")


class LocalOAuthCallbackServer:
    """
    Spawns a local loopback server to receive access and refresh token redirect payloads from the FastAPI backend.
    """

    def __init__(self, port: int = 52210) -> None:
        self.port = port
        self.settings = get_settings()
        self._server: Optional[HTTPServer] = None
        self._server_thread: Optional[Thread] = None
        self.on_success: Optional[Callable[[dict], None]] = None

    def start(self, success_callback: Callable[[dict], None]) -> None:
        """Start the loopback server in a background thread."""
        self.on_success = success_callback
        outer_self = self
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:
                # Silence standard logging to keep console clean
                pass

            def do_GET(self) -> None:
                try:
                    parsed_url = urllib.parse.urlparse(self.path)
                    query = urllib.parse.parse_qs(parsed_url.query)
                    
                    if parsed_url.path == "/auth/callback":
                        logger.info("Loopback server received request on /auth/callback. Parsing token payload...")
                        # Capture token payload redirected from FastAPI backend
                        token = query.get("token", [None])[0]
                        refresh_token = query.get("refresh_token", [None])[0]
                        user_id = query.get("user_id", [None])[0]
                        email = query.get("email", [None])[0]
                        username = query.get("username", [None])[0]
                        full_name = query.get("full_name", [""])[0]
                        role = query.get("role", ["medical_student"])[0]
                        is_onboarded = query.get("is_onboarded", ["false"])[0] == "true"
                        # Validate and print/log captured authentication payload
                        captured_payload = {
                            "success": True,
                            "token": token,
                            "refresh_token": refresh_token,
                            "user": {
                                "uid": user_id,
                                "email": email,
                                "name": urllib.parse.unquote(full_name) if full_name else "",
                                "provider": "google"
                            }
                        }
                        logger.info(f"Captured Authentication Payload in Loopback: {captured_payload}")
                        
                        if token and refresh_token:
                            auth_data = {
                                "token": token,
                                "refresh_token": refresh_token,
                                "uid": user_id,
                                "email": email,
                                "username": username,
                                "name": urllib.parse.unquote(full_name) if full_name else "",
                                "role": role,
                                "is_onboarded": is_onboarded
                            }
                            outer_self._serve_success_page(self)
                            if outer_self.on_success:
                                logger.info("Notifying PySide6 application with OAuth credentials.")
                                # Deliver authentication credentials to client
                                outer_self.on_success(auth_data)
                        else:
                            error_msg = f"Invalid token payload received from backend: 'token' or 'refresh_token' is missing. Payload: {captured_payload}"
                            logger.error(f"Authentication failed: {error_msg}")
                            outer_self._serve_error_page(self, error_msg, exception=None)
                    else:
                        self.send_response(404)
                        self.end_headers()
                        self.wfile.write(b"Not Found")
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    logger.error(f"Exception inside loopback CallbackHandler do_GET:\n{tb}")
                    outer_self._serve_error_page(self, str(e), exception=e)

        # Bind to 127.0.0.1 (not "localhost")
        for try_port in [self.port, self.port + 1, self.port + 2]:
            try:
                self._server = HTTPServer(("127.0.0.1", try_port), CallbackHandler)
                self.port = try_port
                break
            except Exception as e:
                logger.warning(f"Port {try_port} busy, trying next: {e}")
                
        if not self._server:
            raise RuntimeError("Failed to bind local loopback server to a free port.")

        self._server_thread = Thread(target=self._server.serve_forever, daemon=True)
        self._server_thread.start()
        logger.info(f"Local OAuth loopback server running on http://127.0.0.1:{self.port}/auth/callback")

    def stop(self) -> None:
        """Shutdown the loopback server."""
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._server_thread:
            self._server_thread.join(timeout=1.0)
            self._server_thread = None
        logger.info("Local OAuth loopback server stopped.")

    def preflight_check(self) -> Optional[str]:
        """
        Run a pre-flight diagnostic before opening the browser.
        Returns None if OK, or a descriptive error string if misconfigured.
        """
        from auth.services.env_validator import get_oauth_diagnostic
        return get_oauth_diagnostic()

    def open_browser(self, provider: str) -> None:
        """Launch browser pointing to FastAPI Google Sign-in proxy endpoint."""
        logger.info("Starting browser launch flow...")
        diag = self.preflight_check()
        if diag:
            logger.error(f"OAuth pre-flight FAILED — not opening browser.\n{diag}")
            raise RuntimeError(diag)

        provider_path = provider.lower()
        loopback_port = self.port
        auth_url = f"http://127.0.0.1:8000/auth/{provider_path}/signin?port={loopback_port}"
        logger.info(f"Target OAuth Redirect URI: http://127.0.0.1:8000/auth/{provider_path}/callback")
        logger.info(f"Browser opened (requesting URL: {auth_url})")
        webbrowser.open(auth_url)

    def _serve_success_page(self, handler: BaseHTTPRequestHandler) -> None:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html")
        handler.end_headers()
        
        bg_gradient = "linear-gradient(135deg, #090b16 0%, #151d2f 100%)"
        
        html = f"""<!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Succeeded</title>
            <style>
                body {{
                    background: {bg_gradient};
                    color: white;
                    font-family: 'Segoe UI', system-ui, sans-serif;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    margin: 0;
                }}
                .card {{
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 20px;
                    padding: 40px;
                    text-align: center;
                    max-width: 400px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                }}
                .logo {{
                    font-size: 40px;
                    color: #06b6d4;
                    margin-bottom: 20px;
                }}
                h1 {{ font-size: 22px; margin-bottom: 10px; }}
                p {{ color: rgba(255,255,255,0.6); font-size: 13.5px; line-height: 1.5; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="logo">⚕</div>
                <h1>SSO Verification Complete</h1>
                <p>Successfully established authentication link. You can close this browser tab and return to MediVerse AI.</p>
            </div>
            <script>
                // Attempt to close the browser tab automatically
                setTimeout(() => {{
                    window.close();
                }}, 1500);
            </script>
        </body>
        </html>
        """
        handler.wfile.write(html.encode("utf-8"))

    def _serve_error_page(self, handler: BaseHTTPRequestHandler, error_msg: str, exception: Optional[Exception] = None) -> None:
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html")
        handler.end_headers()
        
        if exception:
            import traceback
            tb = exception.__traceback__
            while tb and tb.tb_next:
                tb = tb.tb_next
            filename = tb.tb_frame.f_code.co_filename if tb else "Unknown File"
            line_number = tb.tb_lineno if tb else "Unknown Line"
            exc_type = type(exception).__name__
            exc_message = str(exception)
            stack_trace = traceback.format_exc()
            
            html = f"""<!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Exception Debugger</title>
                <style>
                    body {{
                        background: #0f172a;
                        color: #f1f5f9;
                        font-family: 'Consolas', monospace;
                        padding: 40px;
                        margin: 0;
                    }}
                    .error-container {{
                        background: #1e293b;
                        border: 2px solid #ef4444;
                        border-radius: 12px;
                        padding: 30px;
                        max-width: 900px;
                        margin: 0 auto;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                    }}
                    h1 {{
                        color: #ef4444;
                        margin-top: 0;
                        font-size: 24px;
                        border-bottom: 1px solid #ef4444;
                        padding-bottom: 10px;
                    }}
                    .field {{
                        margin-bottom: 15px;
                    }}
                    .label {{
                        font-weight: bold;
                        color: #f87171;
                    }}
                    .value {{
                        background: #0f172a;
                        padding: 5px 10px;
                        border-radius: 4px;
                        display: inline-block;
                    }}
                    pre {{
                        background: #0f172a;
                        padding: 20px;
                        border-radius: 8px;
                        overflow-x: auto;
                        border: 1px solid #334155;
                        font-size: 14px;
                        line-height: 1.5;
                    }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <h1>Authentication Exception Detected (Client-Side)</h1>
                    <div class="field"><span class="label">Exception Type:</span> <span class="value">{exc_type}</span></div>
                    <div class="field"><span class="label">Exception Message:</span> <span class="value">{exc_message}</span></div>
                    <div class="field"><span class="label">File Name:</span> <span class="value">{filename}</span></div>
                    <div class="field"><span class="label">Line Number:</span> <span class="value">{line_number}</span></div>
                    <div>
                        <span class="label">Stack Trace:</span>
                        <pre>{stack_trace}</pre>
                    </div>
                </div>
            </body>
            </html>
            """
        else:
            html = f"""<!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Failed</title>
                <style>
                    body {{
                        background: linear-gradient(135deg, #090b16 0%, #151d2f 100%);
                        color: white;
                        font-family: 'Segoe UI', system-ui, sans-serif;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        margin: 0;
                    }}
                    .card {{
                        background: rgba(255, 255, 255, 0.02);
                        border: 1px solid rgba(239, 68, 68, 0.3);
                        border-radius: 20px;
                        padding: 40px;
                        text-align: center;
                        max-width: 400px;
                        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                    }}
                    .logo {{ font-size: 40px; color: #ef4444; margin-bottom: 20px; }}
                    h1 {{ font-size: 22px; margin-bottom: 10px; }}
                    p {{ color: rgba(255,255,255,0.6); font-size: 13.5px; line-height: 1.5; }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="logo">⚠️</div>
                    <h1>SSO Link Aborted</h1>
                    <p>Could not link session. Error reference:<br><strong>{error_msg}</strong></p>
                </div>
            </body>
            </html>
            """
        handler.wfile.write(html.encode("utf-8"))
