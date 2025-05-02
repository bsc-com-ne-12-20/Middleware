from django.shortcuts import render

# Create your views here.
# agents/views.py
# agents/views.py

from django.shortcuts import render  # for Django's templates in the future
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Agent
from .serializers import AgentSerializer

# View to list and create agents
class AgentListView(generics.ListCreateAPIView):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer

# View to handle withdrawals
class WithdrawView(APIView):
    def post(self, request):
        agentCode = request.data.get('agentCode')
        amount = request.data.get('amount')

        try:
            agent = Agent.objects.get(agentCode=agentCode)
        except Agent.DoesNotExist:
            return Response({"error": "Agent not found."}, status=status.HTTP_404_NOT_FOUND)

        if amount <= 0:
            return Response({"error": "Amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        if agent.balance < amount:
            return Response({"error": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

        agent.balance -= amount
        agent.save()

        return Response({"message": "Withdrawal successful.", "new_balance": agent.balance}, status=status.HTTP_200_OK)