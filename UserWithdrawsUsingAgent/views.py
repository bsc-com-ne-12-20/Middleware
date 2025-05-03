from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.conf import settings
from decimal import Decimal
import requests
from secmomo.models import Agents
from .models import AgentBalanceUpdate, Revenue
from .serializers import (
    UserWithdrawalToAgentSerializer,
    TransactionResponseSerializer,
    AgentBalanceUpdateSerializer,
)

class UserWithdrawToAgentAPIView(APIView):
    """
    Processes user withdrawals to agent accounts
    """
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = UserWithdrawalToAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        user_email = data["user_email"]
        amount = data["amount"]
        agentCode = data["agentCode"]

        commission_earned = amount * Decimal("0.03")
        net_amount = amount + commission_earned

        try:
            agent = Agents.objects.select_for_update().get(agentCode=agentCode)
        except Agents.DoesNotExist:
            return Response(
                {"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Create transaction record with pending status
        transaction = AgentBalanceUpdate(
            agent=agent,
            user_email=user_email,
            gross_amount=amount,
            commission_earned=commission_earned,
            net_amount=net_amount,
            status='pending'
        )
        transaction.save()

        try:
            # Deduct from user wallet
            response = requests.post(
                settings.USER_WALLET_WITHDRAW_URL,
                json={"email": user_email, "amount": str(amount)},
                timeout=5,
            )
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("success", True):
                # Process transaction on success
                transaction.status = 'completed'
                transaction.process_transaction()
            else:
                # Set failed status on non-success response
                transaction.status = 'failed'
                
            transaction.save()

        except requests.exceptions.RequestException as e:
            # Handle network or API errors
            transaction.status = 'failed'
            transaction.save()

        return Response(
            TransactionResponseSerializer(
                {
                    "id": transaction.transaction_id,
                    "type": "withdrawal",
                    "sender": user_email,
                    "receiver": agent.agentCode,
                    "amount": transaction.gross_amount,
                    "commission_earned": transaction.commission_earned,
                    "time_stamp": transaction.timestamp,
                    "status": transaction.status
                }
            ).data,
            status=status.HTTP_200_OK if transaction.status == 'completed' else status.HTTP_400_BAD_REQUEST
        )

class AgentTransactionHistoryAPIView(APIView):
    def get(self, request):
        agentCode = request.query_params.get("agentCode")
        if not agentCode:
            return Response(
                {"detail": "agentCode parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            agent = Agents.objects.get(agentCode=agentCode)
            transactions = AgentBalanceUpdate.objects.filter(agent=agent).order_by(
                "-timestamp"
            )
            return Response(AgentBalanceUpdateSerializer(transactions, many=True).data)
        except Agents.DoesNotExist:
            return Response(
                {"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND
            )

class RevenueReportAPIView(APIView):
    def get(self, request):
        revenue = Revenue.objects.first()
        return Response(
            {
                "total_fees": str(revenue.total_fees if revenue else 0),
                "last_updated": revenue.last_updated if revenue else None,
            }
        )