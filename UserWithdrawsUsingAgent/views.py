from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.conf import settings
from decimal import Decimal
import requests
from secmomo.models import Agents
from .models import AgentWithdrawalHistory, Revenue
from .serializers import UserWithdrawalToAgentSerializer, TransactionResponseSerializer, AgentWithdrawalHistorySerializer
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from django.core.cache import cache
from django.db import DatabaseError

class UserWithdrawToAgentAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = UserWithdrawalToAgentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        sender_email = data["sender_email"]
        amount = data["amount"]
        agentCode = data["agentCode"]

        commission_earned = amount * Decimal("0.03")
        net_amount = amount  # Agent receives full amount

        try:
            agent = Agents.objects.select_for_update().get(agentCode=agentCode)
        except Agents.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

        transaction = AgentWithdrawalHistory(
            agent=agent,
            sender_email=sender_email,
            receiver_email=agent.email,
            receiver=agent.agentCode,
            gross_amount=amount,
            commission_earned=commission_earned,
            net_amount=net_amount,
            status='pending'
        )
        transaction.save()

        try:
            response = requests.post(
                settings.USER_WALLET_WITHDRAW_URL,  # Use configurable setting
                json={"email": sender_email, "amount": str(amount)},
                timeout=5,
            )
            response_data = response.json()

            if response.status_code == 200 and response_data.get("success", True):
                transaction.status = 'completed'
                transaction.process_transaction()
            else:
                transaction.status = 'failed'
                
            transaction.save()

        except requests.exceptions.RequestException:
            transaction.status = 'failed'
            transaction.save()

        return Response(
            TransactionResponseSerializer(
                {
                    "id": transaction.transaction_id,
                    "type": "withdrawal",
                    "sender": sender_email,
                    "receiver": agent.agentCode,
                    "amount": transaction.gross_amount,
                    "commission_earned": transaction.commission_earned,
                    "time_stamp": transaction.timestamp,
                    "status": transaction.status
                }
            ).data,
            status=status.HTTP_200_OK if transaction.status == 'completed' else status.HTTP_400_BAD_REQUEST
        )

class AgentWithdrawalHistoryAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        agentCode = request.query_params.get("agentCode")
        timeRange = request.query_params.get("timeRange", "day")
        if not agentCode:
            return Response({"detail": "agentCode parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = Agents.objects.get(agentCode=agentCode)
            queryset = AgentWithdrawalHistory.objects.filter(agent=agent, status='completed')

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
                return Response({"error": "Invalid timeRange"}, status=status.HTTP_400_BAD_REQUEST)

            queryset = queryset.filter(timestamp__gte=start, timestamp__lte=end).order_by('-timestamp')

            # Cache key for growth data
            cache_key = f"growth_withdrawal_{agentCode}_{timeRange}"
            growth = None
            try:
                cached_growth = cache.get(cache_key)
                if cached_growth is not None:
                    growth = cached_growth
            except DatabaseError as e:
                print(f"Cache get error in AgentWithdrawalHistoryAPIView: {e}")
                # Proceed without cache

            if not growth:
                current_start = start
                current_end = end
                if timeRange == "day":
                    previous_start = start - timedelta(days=1)
                    previous_end = previous_start + timedelta(days=1) - timedelta(seconds=1)
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
                    status='completed'
                )
                previous_transactions = AgentWithdrawalHistory.objects.filter(
                    agent=agent,
                    timestamp__gte=previous_start,
                    timestamp__lte=previous_end,
                    status='completed'
                )

                current_metrics = current_transactions.aggregate(
                    total_transactions=Count('id'),
                    total_commission=Sum('commission_earned'),
                    total_volume=Sum('gross_amount')
                )
                previous_metrics = previous_transactions.aggregate(
                    total_transactions=Count('id'),
                    total_commission=Sum('commission_earned'),
                    total_volume=Sum('gross_amount')
                )

                def calculate_growth(current, previous):
                    current = current or 0
                    previous = previous or 0
                    if previous == 0:
                        return "↑ 100%" if current > 0 else "0%"
                    growth_value = ((current - previous) / previous) * 100
                    return f"{'↑' if growth_value >= 0 else '↓'} {abs(growth_value):.1f}%"

                growth = {
                    "transactions": calculate_growth(
                        current_metrics['total_transactions'],
                        previous_metrics['total_transactions']
                    ),
                    "commission": calculate_growth(
                        current_metrics['total_commission'],
                        previous_metrics['total_commission']
                    ),
                    "volume": calculate_growth(
                        current_metrics['total_volume'],
                        previous_metrics['total_volume']
                    )
                }
                try:
                    cache.set(cache_key, growth, timeout=300)
                except DatabaseError as e:
                    print(f"Cache set error in AgentWithdrawalHistoryAPIView: {e}")
                    # Continue without caching

            serializer = AgentWithdrawalHistorySerializer(queryset, many=True)
            return Response({
                "transactions": serializer.data,
                "growth": growth
            }, status=status.HTTP_200_OK)
        except Agents.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)