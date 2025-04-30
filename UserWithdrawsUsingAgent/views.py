from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.conf import settings
from decimal import Decimal
import requests
from secmomo.models import Agents
from .models import Agents, AgentBalanceUpdate, Revenue
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
        agent_code = data["agent_code"]

        # Calculate fees (2% example)
        fee = amount * Decimal("0.02")
        net_amount = amount - fee

        try:
            agent = Agents.objects.select_for_update().get(agent_code=agent_code)
        except Agents.DoesNotExist:
            return Response(
                {"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Deduct from user wallet
        try:
            response = requests.post(
                settings.USER_WALLET_WITHDRAW_URL,
                json={"email": user_email, "amount": str(amount)},
                timeout=5,
            )
            if not response.json().get("success", True):
                raise requests.exceptions.RequestException("Deduction failed")
        except requests.exceptions.RequestException as e:
            return Response(
                {"detail": "User wallet deduction failed", "error": str(e)},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        # Process transaction
        try:
            transaction = AgentBalanceUpdate(
                agent=agent,
                user_email=user_email,
                gross_amount=amount,
                transaction_fee=fee,
                net_amount=net_amount,
            )
            transaction.save()
            transaction.process_transaction()

            return Response(
                TransactionResponseSerializer(
                    {
                        "success": True,
                        "transaction_id": transaction.transaction_id,
                        "agent_new_balance": agent.current_balance,
                        "net_amount": transaction.net_amount,
                        "transaction_fee": transaction.transaction_fee,
                        "timestamp": transaction.timestamp,
                    }
                ).data,
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"detail": "Transaction processing failed", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AgentTransactionHistoryAPIView(APIView):
    def get(self, request):
        agent_code = request.query_params.get("agent_code")
        if not agent_code:
            return Response(
                {"detail": "agent_code parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            agent = Agents.objects.get(agent_code=agent_code)
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
