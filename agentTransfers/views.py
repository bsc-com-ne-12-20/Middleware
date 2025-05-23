from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status
from secmomo.models import Agents
from .serializers import TransferHistorySerializer, TransferSerializer
from .models import Transfer
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Q
from django.core.cache import cache
from django.db import DatabaseError

class TransferAPIView(generics.CreateAPIView):
   # permission_classes = [permissions.IsAuthenticated]
    queryset = Transfer.objects.all()
    serializer_class = TransferSerializer

    def perform_create(self, serializer):
        serializer.save()

class TransferHistoryAPIView(generics.ListAPIView):
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransferHistorySerializer

    def get_queryset(self):
        agentCode = self.request.query_params.get("agentCode")
        timeRange = self.request.query_params.get("timeRange", "day")
        if not agentCode:
            return Transfer.objects.none()

        user = get_object_or_404(Agents, agentCode=agentCode)
        queryset = Transfer.objects.filter(Q(sender=user) | Q(receiver=user), status='completed')

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

        return queryset.filter(time_stamp__gte=start, time_stamp__lte=end)

    def list(self, request, *args, **kwargs):
        agentCode = request.query_params.get("agentCode")
        timeRange = request.query_params.get("timeRange", "day")
        if not agentCode:
            return Response({"detail": "agentCode parameter required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            agent = Agents.objects.get(agentCode=agentCode)
        except Agents.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

        cache_key = f"growth_transfer_{agentCode}_{timeRange}"
        growth = None
        try:
            cached_growth = cache.get(cache_key)
            if cached_growth is not None:
                growth = cached_growth
        except DatabaseError as e:
            print(f"Cache get error in TransferHistoryAPIView: {e}")
            # Proceed without cache

        if not growth:
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

            current_transactions = Transfer.objects.filter(
                Q(sender=agent) | Q(receiver=agent),
                time_stamp__gte=current_start,
                time_stamp__lte=current_end,
                status='completed'
            )
            previous_transactions = Transfer.objects.filter(
                Q(sender=agent) | Q(receiver=agent),
                time_stamp__gte=previous_start,
                time_stamp__lte=previous_end,
                status='completed'
            )

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
                cache.set(cache_key, growth, timeout=5)
            except DatabaseError as e:
                print(f"Cache set error in TransferHistoryAPIView: {e}")
                # Continue without caching

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "transactions": serializer.data,
            "growth": growth
        }, status=status.HTTP_200_OK)