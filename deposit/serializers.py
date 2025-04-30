from rest_framework import serializers
from .models import Deposit, AgentDepositHistory

class AgentDepositHistorySerializer(serializers.ModelSerializer):
    agent_code = serializers.CharField(source='agent.agent_code', read_only=True)

    class Meta:
        model = AgentDepositHistory
        fields = ['agent_code', 'user_email', 'amount', 'transaction_id', 'timestamp']

class DepositSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deposit
        fields = '__all__'
