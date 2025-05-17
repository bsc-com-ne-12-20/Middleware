from django.urls import path
from .views import UserWithdrawToAgentAPIView, AgentWithdrawalHistoryAPIView

urlpatterns = [
    path('', UserWithdrawToAgentAPIView.as_view(), name='withdrawal'),
    path('wdr-to-agent-hstr/', AgentWithdrawalHistoryAPIView.as_view(), name='withdrawal-history'),
]