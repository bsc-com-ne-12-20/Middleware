from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from deposit.models import AgentDepositHistory
from secmomo.models import Agents
from .serializers import AgentDepositHistorySerializer, AgentDepositSerializer

class AgentDepositAPIView(generics.CreateAPIView):
    serializer_class = AgentDepositSerializer
    #permission_classes = [IsAuthenticated]


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()  # ✅ Get the return value from create()
        return Response(result, status=status.HTTP_201_CREATED)

class AgentDepositHistoryAPIView(generics.ListAPIView):
    serializer_class = AgentDepositHistorySerializer
    #permission_classes = [IsAuthenticated]  # Allow anonymous access (can be restricted to authenticated users)

    def get_queryset(self):
        agent_code = self.request.query_params.get("agent_code")  # Get agent code from the URL query parameter

        if not agent_code:
            return AgentDepositHistory.objects.none()  # If no agent code is provided, return no data

        # Fetch the agent based on the provided agent code
        agent = get_object_or_404(Agents, agent_code=agent_code)

        # Return the deposit history for that agent, ordered by timestamp
        return AgentDepositHistory.objects.filter(agent=agent).order_by('-timestamp')
