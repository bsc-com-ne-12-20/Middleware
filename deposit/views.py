from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from .models import AgentDepositHistory
from secmomo.models import Agents
from .serializers import AgentDepositHistorySerializer, AgentDepositSerializer
from UserWithdrawsUsingAgent.models import AgentWithdrawalHistory
from agentTransfers.models import Transfer
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Q
from django.core.cache import cache
from django.db import DatabaseError

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
        timeRange = self.request.query_params.get("timeRange", "day")
        if not agentCode:
            return AgentDepositHistory.objects.none()
        agent = get_object_or_404(Agents, agentCode=agentCode)
        queryset = AgentDepositHistory.objects.filter(agent=agent, status='completed')
        
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
            raise ValueError("Invalid timeRange")
        
        return queryset.filter(timestamp__gte=start, timestamp__lte=end).order_by('-timestamp')

    def list(self, request, *args, **kwargs):
        agentCode = request.query_params.get("agentCode")
        timeRange = request.query_params.get("timeRange", "day")
        if not agentCode:
            return Response({"error": "Agent code is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = Agents.objects.get(agentCode=agentCode)
        except Agents.DoesNotExist:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

        # Cache key for growth data
        cache_key = f"growth_deposit_{agentCode}_{timeRange}"
        growth = None
        try:
            cached_growth = cache.get(cache_key)
            if cached_growth is not None:
                growth = cached_growth
        except DatabaseError as e:
            print(f"Cache get error in AgentDepositHistoryAPIView: {e}")
            # Proceed without cache

        if not growth:
            # Define time ranges
            now = timezone.now()
            if timeRange == "day":
                current_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                current_end = current_start + timedelta(days=1) - timedelta(seconds=1)
                previous_start = current_start - timedelta(days=1)
                previous_end = previous_start + timedelta(days=1) - timedelta(seconds=1)
            elif timeRange == "week":
                current_start = now - timedelta(days=7)
                current_end = now
                previous_start = now - timedelta(days=14)
                previous_end = now - timedelta(days=7)
            elif timeRange == "month":
                current_start = now - timedelta(days=30)
                current_end = now
                previous_start = now - timedelta(days=60)
                previous_end = now - timedelta(days=30)
            else:
                return Response({"error": "Invalid timeRange"}, status=status.HTTP_400_BAD_REQUEST)

            # Query current and previous periods
            current_transactions = AgentDepositHistory.objects.filter(
                agent__agentCode=agentCode,
                timestamp__gte=current_start,
                timestamp__lte=current_end,
                status='completed'
            )
            previous_transactions = AgentDepositHistory.objects.filter(
                agent__agentCode=agentCode,
                timestamp__gte=previous_start,
                timestamp__lte=previous_end,
                status='completed'
            )

            # Calculate metrics
            current_metrics = current_transactions.aggregate(
                total_transactions=Count('id'),
                total_commission=Sum('commission_earned'),
                total_volume=Sum('amount')
            )
            previous_metrics = previous_transactions.aggregate(
                total_transactions=Count('id'),
                total_commission=Sum('commission_earned'),
                total_volume=Sum('amount')
            )

            # Helper function to calculate growth
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
                cache.set(cache_key, growth, timeout=300)  # Cache for 5 minutes
            except DatabaseError as e:
                print(f"Cache set error in AgentDepositHistoryAPIView: {e}")
                # Continue without caching

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "transactions": serializer.data,
            "growth": growth
        }, status=status.HTTP_200_OK)

class AgentBalanceAPIView(generics.RetrieveAPIView):
  #  permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        agentCode = request.query_params.get("agentCode")
        if not agentCode:
            return Response({"error": "Agent code is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = Agents.objects.get(agentCode=agentCode)
            return Response({
                "agentCode": agent.agentCode,
                "current_balance": str(agent.current_balance)
            }, status=status.HTTP_200_OK)
        except Agents.DoesNotExist:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

class AnalyticsAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request):
        agentCode = request.query_params.get("agentCode")
        timeRange = request.query_params.get("timeRange", "day")
        if not agentCode:
            return Response({"error": "Agent code is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = Agents.objects.get(agentCode=agentCode)
        except Agents.DoesNotExist:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

        cache_key = f"analytics_{agentCode}_{timeRange}"
        cached_data = None
        try:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data, status=status.HTTP_200_OK)
        except DatabaseError as e:
            print(f"Cache get error in AnalyticsAPIView: {e}")
            # Proceed without cache

        now = timezone.now()
        if timeRange == "day":
            current_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            current_end = current_start + timedelta(days=1) - timedelta(seconds=1)
            previous_start = current_start - timedelta(days=1)
            previous_end = previous_start + timedelta(days=1) - timedelta(seconds=1)
        elif timeRange == "week":
            current_start = now - timedelta(days=7)
            current_end = now
            previous_start = now - timedelta(days=14)
            previous_end = now - timedelta(days=7)
        elif timeRange == "month":
            current_start = now - timedelta(days=30)
            current_end = now
            previous_start = now - timedelta(days=60)
            previous_end = now - timedelta(days=30)
        else:
            return Response({"error": "Invalid timeRange"}, status=status.HTTP_400_BAD_REQUEST)

        # Query transactions
        deposit_current = AgentDepositHistory.objects.filter(
            agent=agent, timestamp__gte=current_start, timestamp__lte=current_end, status='completed'
        )
        deposit_previous = AgentDepositHistory.objects.filter(
            agent=agent, timestamp__gte=previous_start, timestamp__lte=previous_end, status='completed'
        )
        withdrawal_current = AgentWithdrawalHistory.objects.filter(
            agent=agent, timestamp__gte=current_start, timestamp__lte=current_end, status='completed'
        )
        withdrawal_previous = AgentWithdrawalHistory.objects.filter(
            agent=agent, timestamp__gte=previous_start, timestamp__lte=previous_end, status='completed'
        )
        transfer_current = Transfer.objects.filter(
            Q(sender=agent) | Q(receiver=agent), time_stamp__gte=current_start, time_stamp__lte=current_end, status='completed'
        )
        transfer_previous = Transfer.objects.filter(
            Q(sender=agent) | Q(receiver=agent), time_stamp__gte=previous_start, time_stamp__lte=previous_end, status='completed'
        )

        # Aggregate metrics
        def aggregate_metrics(deposits, withdrawals, transfers):
            deposit_metrics = deposits.aggregate(
                total_transactions=Count('id'),
                total_commission=Sum('commission_earned'),
                total_volume=Sum('amount')
            )
            withdrawal_metrics = withdrawals.aggregate(
                total_transactions=Count('id'),
                total_commission=Sum('commission_earned'),
                total_volume=Sum('gross_amount')
            )
            transfer_metrics = transfers.aggregate(
                total_transactions=Count('id'),
                total_commission=Sum('commission_earned'),
                total_volume=Sum('amount')
            )

            return {
                'total_transactions': (
                    (deposit_metrics['total_transactions'] or 0) +
                    (withdrawal_metrics['total_transactions'] or 0) +
                    (transfer_metrics['total_transactions'] or 0)
                ),
                'total_commission': (
                    (deposit_metrics['total_commission'] or 0) +
                    (withdrawal_metrics['total_commission'] or 0) +
                    (transfer_metrics['total_commission'] or 0)
                ),
                'total_volume': (
                    (deposit_metrics['total_volume'] or 0) +
                    (withdrawal_metrics['total_volume'] or 0) +
                    (transfer_metrics['total_volume'] or 0)
                ),
                'deposit_count': deposit_metrics['total_transactions'] or 0,
                'withdrawal_count': withdrawal_metrics['total_transactions'] or 0,
                'transfer_count': transfer_metrics['total_transactions'] or 0
            }

        current_metrics = aggregate_metrics(deposit_current, withdrawal_current, transfer_current)
        previous_metrics = aggregate_metrics(deposit_previous, withdrawal_previous, transfer_previous)

        def calculate_growth(current, previous):
            current = current or 0
            previous = previous or 0
            if previous == 0:
                return "↑ 100%" if current > 0 else "0%"
            growth_value = ((current - previous) / previous) * 100
            return f"{'↑' if growth_value >= 0 else '↓'} {abs(growth_value):.1f}%"

        response = {
            "summary": {
                "total_transactions": current_metrics['total_transactions'],
                "total_commission": str(current_metrics['total_commission']),
                "total_volume": str(current_metrics['total_volume']),
                "deposit_count": current_metrics['deposit_count'],
                "withdrawal_count": current_metrics['withdrawal_count'],
                "transfer_count": current_metrics['transfer_count']
            },
            "growth": {
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
        }
        try:
            cache.set(cache_key, response, timeout=300)
        except DatabaseError as e:
            print(f"Cache set error in AnalyticsAPIView: {e}")
            # Continue without caching

        return Response(response, status=status.HTTP_200_OK)