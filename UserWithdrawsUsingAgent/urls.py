# UserWithdrawsUsingAgent/urls.py
from django.urls import path
from .views import UserWithdrawToAgentAPIView, AgentWithdrawalHistoryAPIView, AgentWithdrawalDepositAPIView

urlpatterns = [
    path('', UserWithdrawToAgentAPIView.as_view(), name='withdrawal'),
    path('wdr-to-agent-hstr/', AgentWithdrawalHistoryAPIView.as_view(), name='withdrawal-history'),
    path('dpst/', AgentWithdrawalDepositAPIView.as_view(), name='withdraw-deposit'),
]