# agents/urls.py
from django.urls import path
from .views import WithdrawView, AgentListView  # Import AgentListView

urlpatterns = [
    path('', AgentListView.as_view(), name='agent-list'),  # List and create agents
    path('withdraw/', WithdrawView.as_view(), name='agent-withdraw'),  # Handle withdrawals
]