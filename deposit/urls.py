# urls.py

from django.urls import path
from .views import AgentDepositAPIView, AgentDepositHistoryAPIView

urlpatterns = [
    path('dpst/', AgentDepositAPIView.as_view(), name='agent-deposit'),
<<<<<<< HEAD
    path('dpst-hstr/', AgentDepositHistoryAPIView.as_view(), name='agent-deposit-history')
=======
    path('dpst-hstr/', AgentDepositHistoryAPIView.as_view(), name='agent-deposit-history'),
>>>>>>> 53f607d (Remove external deposit api in deposit agent)
]