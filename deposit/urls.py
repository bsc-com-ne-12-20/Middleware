# urls.py

from django.urls import path
from .views import AgentDepositAPIView, AgentDepositHistoryAPIView

urlpatterns = [
    path('dpst/', AgentDepositAPIView.as_view(), name='agent-deposit'),
    path('dpst-hstr/', AgentDepositHistoryAPIView.as_view(), name='agent-deposit-history')
]