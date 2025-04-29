from rest_framework import serializers
from .models import AgentBalanceUpdate, Revenue
from decimal import Decimal

class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = ['total_fees', 'last_updated']
        read_only_fields = fields

class AgentBalanceUpdateSerializer(serializers.ModelSerializer):
    agent_code = serializers.CharField(source='agent.agent_code', read_only=True)
    agent_name = serializers.CharField(source='agent.username', read_only=True)
    
    class Meta:
        model = AgentBalanceUpdate
        fields = [
            'transaction_id',
            'agent_code',
            'agent_name',
            'user_email',
            'gross_amount',
            'transaction_fee',
            'net_amount',
            'timestamp'
        ]
        read_only_fields = [
            'transaction_id',
            'net_amount',
            'timestamp',
            'agent_code',
            'agent_name'
        ]
    
    def validate(self, data):
        if 'gross_amount' in data and 'transaction_fee' in data:
            if data['transaction_fee'] >= data['gross_amount']:
                raise serializers.ValidationError(
                    "Fee must be less than gross amount"
                )
            data['net_amount'] = data['gross_amount'] - data['transaction_fee']
        return data

class UserWithdrawalToAgentSerializer(serializers.Serializer):
    user_email = serializers.EmailField()
    amount = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        min_value=Decimal('0.01')
    )
    agent_code = serializers.CharField(max_length=10)

class TransactionResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    transaction_id = serializers.CharField()
    agent_new_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    transaction_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    timestamp = serializers.DateTimeField()