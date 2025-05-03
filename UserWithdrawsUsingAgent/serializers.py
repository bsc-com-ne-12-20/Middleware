from rest_framework import serializers
from .models import AgentBalanceUpdate, Revenue
from decimal import Decimal

class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = ['total_fees', 'last_updated']
        read_only_fields = fields

class AgentBalanceUpdateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='transaction_id')
    type = serializers.SerializerMethodField()
    sender = serializers.CharField(source='user_email')
    receiver = serializers.CharField(source='agent.agentCode')
    amount = serializers.DecimalField(source='gross_amount', max_digits=10, decimal_places=2)
    time_stamp = serializers.DateTimeField(source='timestamp')

    class Meta:
        model = AgentBalanceUpdate
        fields = ['id', 'type', 'sender', 'receiver', 'amount', 'commission_earned', 'time_stamp', 'status']
        read_only_fields = ['id', 'type', 'sender', 'receiver', 'amount', 'commission_earned', 'time_stamp', 'status']

    def get_type(self, obj):
        return "withdrawal"

    def validate(self, data):
        if 'gross_amount' in data and 'commission_earned' in data:
            if data['commission_earned'] >= data['gross_amount']:
                raise serializers.ValidationError(
                    "Commission must be less than gross amount"
                )
        return data

class UserWithdrawalToAgentSerializer(serializers.Serializer):
    user_email = serializers.EmailField()
    amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        min_value=Decimal('0.01')
    )
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