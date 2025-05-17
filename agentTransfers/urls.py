from django.urls import path
from .views import TransferAPIView, TransferHistoryAPIView

urlpatterns = [
    path('agent-trsf', TransferAPIView.as_view(), name='transfer'),
    path('trsf-hstr/', TransferHistoryAPIView.as_view(), name='transfer-history'),
]