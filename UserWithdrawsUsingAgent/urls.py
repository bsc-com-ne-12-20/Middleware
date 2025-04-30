from django.urls import path
from .views import (
    UserWithdrawToAgentAPIView,
    AgentTransactionHistoryAPIView,
    RevenueReportAPIView,
)

urlpatterns = [
    # User withdrawal endpoint
    path(
        "withdraw-to-agent/",
        UserWithdrawToAgentAPIView.as_view(),
        name="user-withdraw-to-agent",
    ),
    # Agent transaction history
    path(
        "Widraw-to-agent-history/",
        AgentTransactionHistoryAPIView.as_view(),
        name="agent-transactions",
    ),
    # Revenue reporting
    path("revenue/", RevenueReportAPIView.as_view(), name="revenue-report"),
]
