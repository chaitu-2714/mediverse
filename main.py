"""
MediVerse AI — Main Entry Point.
Bootstraps the application, handles state transitions (Splash -> Login -> Main).
"""
import sys
import logging
from PySide6.QtWidgets import QApplication

from config.logging_config import setup_logging
from config.settings import get_settings
from database.connection import initialize_database
from ai_core.ai_engine import get_ai_engine
from auth.ui.splash_screen import SplashScreen
from auth.ui.login_window import LoginWindow
from auth.ui.register_window import RegisterWindow
from modules.main_window import MainWindow

# Setup root logger
setup_logging()
logger = logging.getLogger("mediverse.main")


class ApplicationController:
    """Manages the lifecycle of the application windows."""
    
    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        
        self.settings = get_settings()
        self.backend_process = None
        
        # Keep references to windows to prevent garbage collection
        self.splash: SplashScreen | None = None
        self.setup_win: QWidget | None = None
        self.login_win: LoginWindow | None = None
        self.register_win: RegisterWindow | None = None
        self.onboarding_win: QWidget | None = None
        self.main_win: MainWindow | None = None

    def start(self) -> None:
        """Begin application lifecycle."""
        logger.info("Starting MediVerse AI...")
        
        # Log SSO configuration status (non-blocking)
        from auth.services.env_validator import get_missing_vars
        missing = get_missing_vars()
        if missing:
            logger.info(f"SSO environment variables not yet configured: {missing}. Google/Apple sign-in will prompt setup wizard when clicked.")
        
        self._show_splash()

    def stop_backend(self) -> None:
        """Terminate the background FastAPI server process."""
        if hasattr(self, 'backend_process') and self.backend_process:
            logger.info("Stopping background FastAPI server...")
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=2.0)
            except Exception as e:
                logger.error(f"Error stopping backend process: {e}")
                try:
                    self.backend_process.kill()
                except Exception:
                    pass
            self.backend_process = None

    def _show_splash(self) -> None:
        def start_backend():
            import subprocess
            import time
            import requests
            
            import os
            venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "Scripts", "python.exe")
            python_exe = venv_python if os.path.exists(venv_python) else sys.executable
            
            cmd = [python_exe, "-m", "uvicorn", "backend.main:app", "--port", "8000", "--host", "127.0.0.1"]
            logger.info(f"Spawning FastAPI backend server using: {python_exe}")
            self.backend_process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            start_time = time.time()
            while time.time() - start_time < 6.0:
                try:
                    res = requests.get("http://localhost:8000/auth/me", timeout=1)
                    if res.status_code in [200, 401]:
                        logger.info("FastAPI backend server is online.")
                        return
                except Exception:
                    pass
                time.sleep(0.5)
            logger.error("FastAPI backend server failed to start within timeout.")
            raise RuntimeError("FastAPI backend server failed to start. Please verify dependencies are installed and port 8000 is available.")

        def init_db():
            initialize_database()

        def init_ai():
            engine = get_ai_engine()
            engine.initialize_models()

        init_steps = [
            ("Starting Authentication Server...", start_backend),
            ("Initializing Database...", init_db),
            ("Loading AI Models...", init_ai)
        ]
        self.splash = SplashScreen(init_steps)
        self.splash.initialization_complete.connect(self._on_init_result)
        self.splash.show_and_initialize()

    def _on_init_result(self, success: bool, error: str) -> None:
        if success:
            self._on_init_complete()
        else:
            self._on_init_failed(error)
    def _on_init_complete(self) -> None:
        logger.info("System initialization complete. Auto-signing in with developer credentials.")
        if self.splash:
            self.splash.close()
            self.splash = None

        # Automatically query or create developer user in database
        from database.connection import get_db_session
        from database.models.user_model import UserModel
        import uuid
        from datetime import datetime
        
        user_id = uuid.UUID("d3b07384-d113-4e4e-9c29-0d1b918fcf10")
        try:
            with get_db_session() as session:
                user_db = session.query(UserModel).filter_by(email="developer@mediverse.ai").first()
                if not user_db:
                    user_db = UserModel(
                        id=user_id,
                        email="developer@mediverse.ai",
                        username="developer",
                        password_hash="BypassedAuth",
                        full_name="Developer Operator",
                        role="doctor",
                        is_active=True,
                        is_verified=True,
                        is_onboarded=True
                    )
                    session.add(user_db)
                    session.commit()
        except Exception as e:
            logger.error(f"DB user verification failed, proceeding: {e}")
                
        # Construct User domain object
        from core.models.user import User
        from config.constants import UserRole
        
        developer_user = User(
            id=user_id,
            email="developer@mediverse.ai",
            username="developer",
            full_name="Developer Operator",
            role=UserRole.DOCTOR,
            is_active=True,
            is_verified=True,
            avatar_url=None,
            auth_provider="mock",
            is_onboarded=True,
            login_count=1,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        
        # Save session so that any background API calls have a dummy token
        try:
            from auth.services.auth_service import AuthService
            auth_service = AuthService()
            dummy_token = "dummy-jwt-developer-token"
            auth_service._session.save_session(dummy_token, "dummy-refresh-token", str(user_id), "developer@mediverse.ai")
        except Exception as e:
            logger.error(f"Failed to save dummy developer session: {e}")
            
        self._show_main(developer_user)

    def _on_init_failed(self, error: str) -> None:
        logger.critical(f"System initialization failed: {error}")
        # In a real app, show an error dialog. Here we just exit.
        sys.exit(1)

    def _show_setup_wizard(self) -> None:
        from auth.ui.setup_wizard_window import SetupWizardWindow
        self.setup_win = SetupWizardWindow()
        
        def config_done():
            logger.info("Setup Wizard completed configuration successfully. Restarting boot sequence.")
            self.setup_win = None
            self.start()
            
        self.setup_win.configuration_completed.connect(config_done)
        self.setup_win.show()

    def _show_login(self) -> None:
        self.login_win = LoginWindow()
        self.login_win.login_successful.connect(self._on_login_success)
        self.login_win.navigate_to_register.connect(self._show_register)
        
        if self.register_win:
            self.register_win.close()
            self.register_win = None
            
        self.login_win.show()

    def _show_register(self) -> None:
        self.register_win = RegisterWindow()
        self.register_win.register_successful.connect(self._on_login_success)
        self.register_win.navigate_to_login.connect(self._show_login)
        
        if self.login_win:
            self.login_win.close()
            self.login_win = None
            
        self.register_win.show()

    def _on_login_success(self, user, token) -> None:
        logger.info(f"User '{user.username}' logged in successfully.")
        if self.login_win:
            self.login_win.close()
            self.login_win = None
        if self.register_win:
            self.register_win.close()
            self.register_win = None

        if not getattr(user, "is_onboarded", False):
            self._show_onboarding(user, token)
        else:
            self._show_main(user)

    def _show_main(self, user) -> None:
        self.main_win = MainWindow(user)
        self.main_win.logout_requested.connect(self._on_logout)
        self.main_win.show()

    def _show_onboarding(self, user, token) -> None:
        from auth.ui.onboarding_window import OnboardingWindow
        self.onboarding_win = OnboardingWindow(user.id)
        
        def completed(updated_user):
            logger.info(f"User onboarding completed: {updated_user.email} -> {updated_user.role}")
            if self.onboarding_win:
                self.onboarding_win.close()
                self.onboarding_win = None
            self._show_main(updated_user)
            
        self.onboarding_win.onboarding_completed.connect(completed)
        self.onboarding_win.show()

    def _on_logout(self) -> None:
        logger.info("User requested logout. Bypassed in authentication-free mode.")
        from shared.components.notification_toast import NotificationToast
        if self.main_win:
            NotificationToast.show_message(self.main_win, "Authentication is disabled in development mode.", "info")



def main() -> None:
    controller = ApplicationController()
    try:
        controller.start()
        sys.exit(controller.app.exec())
    finally:
        controller.stop_backend()


if __name__ == "__main__":
    main()
