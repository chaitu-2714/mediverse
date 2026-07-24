"""
Tests checking successful imports of core classes and main modules.
"""
def test_core_imports():
    from main import ApplicationController
    assert ApplicationController is not None

def test_main_window_imports():
    from modules.main_window import MainWindow
    assert MainWindow is not None

def test_view_imports():
    from modules.dashboard.ui.dashboard_view import DashboardView
    from modules.repository.ui.repository_view import RepositoryView
    from modules.ai_assistant.ui.assistant_view import AssistantView
    from modules.knowledge_graph.ui.graph_view import KnowledgeGraphView
    from modules.profile.ui.profile_view import UserProfileView
    from modules.admin_panel.ui.admin_view import AdminPanelView
    from modules.imaging_analysis.ui.imaging_analysis_view import ClinicalAnalysisWorkspaceView
    
    assert all([
        DashboardView, RepositoryView, AssistantView,
        KnowledgeGraphView, UserProfileView, AdminPanelView,
        ClinicalAnalysisWorkspaceView
    ])


