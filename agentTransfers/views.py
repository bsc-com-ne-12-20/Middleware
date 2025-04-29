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
        agent_code = self.request.query_params.get("agent_code")
        if not agent_code:
            return Transfer.objects.none()  # Return empty queryset if no code provided

        user = get_object_or_404(
            Agents, agent_code=agent_code
        )  # 👈 Get agent by agent_code
        return Transfer.objects.filter(sender=user) | Transfer.objects.filter(
            receiver=user
        )
