# withdrawal/views.py
from django.forms import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.conf import settings
from decimal import Decimal
import requests
from secmomo.models import Agents
from .models import AgentWithdrawalHistory, Revenue
from .serializers import (
    UserWithdrawalToAgentSerializer,
    TransactionResponseSerializer,
    AgentWithdrawalHistorySerializer,
    AgentDepositSerializer,
)
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from django.core.cache import cache
from django.db import DatabaseError
import logging

logger = logging.getLogger(__name__)

class UserWithdrawToAgentAPIView(APIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = UserWithdrawalToAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        sender_email = data["sender_email"]
        amount = data["amount"]
        agent_code = data["agentCode"]

        commission_rate = Decimal("0.03")
        commission_earned = amount * commission_rate
        net_amount = amount + commission_earned

        try:
            agent = Agents.objects.select_for_update().get(agentCode=agent_code)
        except Agents.DoesNotExist:
            logger.error(f"Agent not found: {agent_code}")
            return Response(
                {"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            withdrawal = AgentWithdrawalHistory(
                agent=agent,
                sender_email=sender_email,
                receiver_email=agent.email,
                gross_amount=amount,
                commission_earned=commission_earned,
                net_amount=net_amount,
                status="pending",
            )
            withdrawal.save()
            logger.info(f"Created withdrawal {withdrawal.transaction_id} for {sender_email}")
        except Exception as e:
            logger.error(f"Failed to create withdrawal for {sender_email}: {str(e)}")
            return Response(
                {"detail": "Failed to create withdrawal record"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            response = requests.post(
                settings.USER_WALLET_WITHDRAW_URL,
                json={
                    "email": sender_email,
                    "amount": str(amount),
                    "reference": withdrawal.transaction_id,
                },
                timeout=10,
            )
            response_data = response.json()
            logger.info(f"Wallet service response: {response_data}")

            if (
                response.status_code == 200
                and ("success" in response_data and response_data["success"])
                or ("trans_id" in response_data)
            ):
                try:
                    agent.add_to_balance(net_amount)
                    withdrawal.status = "completed"
                    withdrawal.process_transaction()
                    logger.info(
                        f"Success: Withdrawal {withdrawal.transaction_id} processed. "
                        f"Amount: {amount}, Agent: {agent_code}"
                    )
                except ValidationError as e:
                    withdrawal.status = "failed"
                    logger.error(f"Balance limit exceeded for agent {agent.agentCode}: {str(e)}")
                    return Response(
                        {"detail": str(e)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                withdrawal.status = "failed"
                logger.error(
                    f"Failed: Withdrawal {withdrawal.transaction_id}. "
                    f"Response: {response_data}"
                )
                return Response(
                    {
                        "detail": "Withdrawal failed",
                        "error": response_data.get("error", "Unknown error"),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except requests.exceptions.RequestException as e:
            withdrawal.status = "failed"
            logger.error(
                f"Request failed for withdrawal {withdrawal.transaction_id}. Error: {str(e)}"
            )
            return Response(
                {"detail": "Failed to connect to wallet service"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ValueError as e:
            withdrawal.status = "failed"
            logger.error(f"Invalid response from wallet service: {str(e)}")
            return Response(
                {"detail": "Invalid response from wallet service"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        finally:
            withdrawal.save()

        response_serializer = TransactionResponseSerializer(
            {
                "id": withdrawal.transaction_id,
                "type": "withdrawal",
                "sender": sender_email,
                "receiver": agent.agentCode,
                "amount": withdrawal.gross_amount,
                "commission_earned": withdrawal.commission_earned,
                "time_stamp": withdrawal.timestamp,
                "status": withdrawal.status,
            }
        )

        return Response(response_serializer.data, status=status.HTTP_200_OK)

class AgentWithdrawalDepositAPIView(APIView):
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = AgentDepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        agent_code = data["agentCode"]
        amount = data["amount"]

        commission_earned = Decimal("0.00")  # Always 0 for deposits
        net_amount = amount

        try:
            agent = Agents.objects.select_for_update().get(agentCode=agent_code)
        except Agents.DoesNotExist:
            logger.error(f"Agent not found: {agent_code}")
            return Response(
                {"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            deposit = AgentWithdrawalHistory(
                agent=agent,
                sender_email=None,  # No email for deposits
                receiver_email=None,  # No email for deposits
                gross_amount=amount,
                commission_earned=commission_earned,
                net_amount=net_amount,
                status="pending",
            )
            deposit.save()
            logger.info(f"Created deposit {deposit.transaction_id} for agent {agent_code}")
        except Exception as e:
            logger.error(f"Failed to create deposit for {agent_code}: {str(e)}")
            return Response(
                {"detail": "Failed to create deposit record"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            agent.add_to_balance(net_amount)
            deposit.status = "completed"
            deposit.process_transaction()
            logger.info(
                f"Success: Deposit {deposit.transaction_id} processed. "
                f"Amount: {amount}, Agent: {agent_code}"
            )
        except ValidationError as e:
            deposit.status = "failed"
            logger.error(f"Balance limit exceeded for agent {agent.agentCode}: {str(e)}")
            deposit.save()
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            deposit.status = "failed"
            logger.error(f"Failed to process deposit {deposit.transaction_id}: {str(e)}")
            deposit.save()
            return Response(
                {"detail": "Failed to process deposit"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_serializer = TransactionResponseSerializer(
            {
                "id": deposit.transaction_id,
                "type": "withdrawal",
                "sender": None,
                "receiver": agent.agentCode,
                "amount": deposit.gross_amount,
                "commission_earned": deposit.commission_earned,
                "time_stamp": deposit.timestamp,
                "status": deposit.status,
            }
        )

        return Response(response_serializer.data, status=status.HTTP_200_OK)

class AgentWithdrawalHistoryAPIView(APIView):
    def get(self, request):
        agentCode = request.query_params.get("agentCode")
        timeRange = request.query_params.get("timeRange", "day")
        if not agentCode:
            return Response(
                {"detail": "agentCode parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            agent = Agents.objects.get(agentCode=agentCode)
            queryset = AgentWithdrawalHistory.objects.filter(
                agent=agent, status="completed"
            )

            now = timezone.now()
            if timeRange == "day":
                start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=1) - timedelta(seconds=1)
            elif timeRange == "week":
                start = now - timedelta(days=7)
                end = now
            elif timeRange == "month":
                start = now - timedelta(days=30)
                end = now
            else:
                return Response(
                    {"error": "Invalid timeRange"}, status=status.HTTP_400_BAD_REQUEST
                )

            queryset = queryset.filter(
                timestamp__gte=start, timestamp__lte=end
            ).order_by("-timestamp")

            cache_key = f"growth_withdrawal_{agentCode}_{timeRange}"
            growth = None
            try:
                cached_growth = cache.get(cache_key)
                if cached_growth is not None:
                    growth = cached_growth
            except DatabaseError as e:
                print(f"Cache get error in AgentWithdrawalHistoryAPIView: {e}")

            if not growth:
                current_start = start
                current_end = end
                if timeRange == "day":
                    previous_start = start - timedelta(days=1)
                    previous_end = (
                        previous_start + timedelta(days=1) - timedelta(seconds=1)
                    )
                elif timeRange == "week":
                    previous_start = now - timedelta(days=14)
                    previous_end = now - timedelta(days=7)
                elif timeRange == "month":
                    previous_start = now - timedelta(days=60)
                    previous_end = now - timedelta(days=30)

                current_transactions = AgentWithdrawalHistory.objects.filter(
                    agent=agent,
                    timestamp__gte=current_start,
                    timestamp__lte=current_end,
                    status="completed",
                )
                previous_transactions = AgentWithdrawalHistory.objects.filter(
                    agent=agent,
                    timestamp__gte=previous_start,
                    timestamp__lte=previous_end,
                    status="completed",
                )

                current_metrics = current_transactions.aggregate(
                    total_transactions=Count("id"),
                    total_commission=Sum("commission_earned"),
                    total_volume=Sum("gross_amount"),
                )
                previous_metrics = previous_transactions.aggregate(
                    total_transactions=Count("id"),
                    total_commission=Sum("commission_earned"),
                    total_volume=Sum("gross_amount"),
                )

                def calculate_growth(current, previous):
                    current = current or 0
                    previous = previous or 0
                    if previous == 0:
                        return "↑ 100%" if current > 0 else "0%"
                    growth_value = ((current - previous) / previous) * 100
                    return (
                        f"{'↑' if growth_value >= 0 else '↓'} {abs(growth_value):.1f}%"
                    )

                growth = {
                    "transactions": calculate_growth(
                        current_metrics["total_transactions"],
                        previous_metrics["total_transactions"],
                    ),
                    "commission": calculate_growth(
                        current_metrics["total_commission"],
                        previous_metrics["total_commission"],
                    ),
                    "volume": calculate_growth(
                        current_metrics["total_volume"],
                        previous_metrics["total_volume"],
                    ),
                }
                try:
                    cache.set(cache_key, growth, timeout=300)
                except DatabaseError as e:
                    print(f"Cache set error in AgentWithdrawalHistoryAPIView: {e}")

            serializer = AgentWithdrawalHistorySerializer(queryset, many=True)
            return Response(
                {"transactions": serializer.data, "growth": growth},
                status=status.HTTP_200_OK,
            )
        except Agents.DoesNotExist:
            return Response(
                {"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND
            )