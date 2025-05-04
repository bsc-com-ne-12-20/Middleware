
# withdrawal/serializers.py
from rest_framework import serializers
from .models import AgentWithdrawalHistory, Revenue
from decimal import Decimal

class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = ['total_fees', 'last_updated']
        read_only_fields = fields

class AgentWithdrawalHistorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='transaction_id')
    type = serializers.SerializerMethodField()
    sender = serializers.CharField(source='sender_email')
    receiver = serializers.CharField(source='receiver_email')
    amount = serializers.DecimalField(source='gross_amount', max_digits=10, decimal_places=2)
    time_stamp = serializers.DateTimeField(source='timestamp')

    class Meta:
        model = AgentWithdrawalHistory
        fields = ['id', 'type', 'sender', 'receiver', 'amount', 'commission_earned', 'time_stamp', 'status']
        read_only_fields = ['id', 'type', 'sender', 'receiver', 'amount', 'commission_earned', 'time_stamp', 'status']

    def get_type(self, obj):
        return "withdrawal"

class UserWithdrawalToAgentSerializer(serializers.Serializer):
    sender_email = serializers.EmailField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    agentCode = serializers.CharField(max_length=10)

class TransactionResponseSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    sender = serializers.CharField()
    receiver = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    commission_earned = serializers.DecimalField(max_digits=10, decimal_places=2)
    time_stamp = serializers.DateTimeField()
    status = serializers.CharField()
