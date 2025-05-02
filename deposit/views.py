
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import AgentDepositHistory
from secmomo.models import Agents
from .serializers import AgentDepositHistorySerializer, AgentDepositSerializer

class AgentDepositAPIView(generics.CreateAPIView):
    serializer_class = AgentDepositSerializer
    # permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)

class AgentDepositHistoryAPIView(generics.ListAPIView):
    serializer_class = AgentDepositHistorySerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        agentCode = self.request.query_params.get("agentCode")
        if not agentCode:
            return AgentDepositHistory.objects.none()
        agent = get_object_or_404(Agents, agentCode=agentCode)
        return AgentDepositHistory.objects.filter(agent=agent).order_by('-timestamp')

class TransactionHistoryAPIView(generics.ListAPIView):
    serializer_class = AgentDepositHistorySerializer
    # permission_classes = [IsAuthenticated]

    def get_queryset(self):
        agentCode = self.request.query_params.get("agentCode")
        if not agentCode:
            return AgentDepositHistory.objects.none()
        agent = get_object_or_404(Agents, agentCode=agentCode)
        return AgentDepositHistory.objects.filter(agent=agent).order_by('-timestamp')
