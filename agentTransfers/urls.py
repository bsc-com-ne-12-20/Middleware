from django.urls import path
from .views import TransferAPIView, TransferHistoryAPIView

urlpatterns = [
    path('', TransferAPIView.as_view(), name='transfer-api'),
    path('trsf-hstr/', TransferHistoryAPIView.as_view(), name='transfer-history-api'),
]
