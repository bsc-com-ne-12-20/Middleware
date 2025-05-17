from django.urls import path
from .views import AgentDepositAPIView, AgentDepositHistoryAPIView, AgentBalanceAPIView, AnalyticsAPIView

urlpatterns = [
    path('', AgentDepositAPIView.as_view(), name='deposit'),
    path('dpst-hstr/', AgentDepositHistoryAPIView.as_view(), name='deposit-history'),
    path('get-balance/', AgentBalanceAPIView.as_view(), name='balance'),
    path('analytics/', AnalyticsAPIView.as_view(), name='analytics'),
]
