from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from secmomo.models import Agents
from .serializers import TransferHistorySerializer, TransferSerializer
from .models import Transfer

class TransferAPIView(generics.CreateAPIView):
    # permission_classes = (permissions.IsAuthenticated,)
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer

    def perform_create(self, serializer):
        serializer.save()

class TransferHistoryAPIView(generics.ListAPIView):
    # permission_classes = (permissions.IsAuthenticated,)
    serializer_class = TransferHistorySerializer

    def get_queryset(self):
        agentCode = self.request.query_params.get("agentCode")
        if not agentCode:
            return Transfer.objects.none()

        user = get_object_or_404(Agents, agentCode=agentCode)
        return Transfer.objects.filter(sender=user) | Transfer.objects.filter(receiver=user)