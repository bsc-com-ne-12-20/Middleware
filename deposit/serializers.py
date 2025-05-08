
# transactions/serializers.py
from rest_framework import serializers
from decimal import Decimal
import uuid
import requests
from secmomo.models import Agents
from .models import AgentDepositHistory

class AgentDepositSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    agentCode = serializers.CharField(write_only=True)
    transaction_id = serializers.CharField(read_only=True)

    class Meta:
        model = AgentDepositHistory
        fields = ['agentCode', 'email', 'amount', 'transaction_id', 'timestamp']

    def validate(self, data):
        agentCode = data.get("agentCode")
        amount = data.get("amount")

        try:
            agent = Agents.objects.get(agentCode=agentCode)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Agent with this code does not exist.")

        if agent.current_balance < amount:
            raise serializers.ValidationError("Insufficient balance.")

        data["agent"] = agent
        return data

    def create(self, validated_data):
        agent = validated_data.pop("agent")
        receiver_email = validated_data["email"]
        amount = validated_data["amount"]
        transaction_id = uuid.uuid4().hex[:12].upper()
        commission = amount * Decimal('0.02')  # 2% commission

        deposit = AgentDepositHistory.objects.create(
            agent=agent,
            sender_email=agent.email,
            receiver_email=receiver_email,
            amount=amount,
            transaction_id=transaction_id,
            commission_earned=commission,
            status='pending'
        )

        external_payload = {
            "email": receiver_email,
            "amount": str(amount),
            "transaction_id": transaction_id
        }

        try:
            response = requests.post(
                "https://mtima.onrender.com/api/v1/dpst/",
                json=external_payload
            )

            if response.status_code == 201:
                agent.current_balance -= amount
                agent.current_balance += commission
                agent.save()
                deposit.status = 'completed'
            else:
                deposit.status = 'failed'
                
            deposit.save()

        except requests.exceptions.RequestException:
            deposit.status = 'failed'
            deposit.save()

        return {
            "id": transaction_id,
            "type": "deposit",
            "sender": agent.agentCode,
            "receiver": receiver_email,
            "amount": str(amount),
            "commission_earned": str(deposit.commission_earned),
            "time_stamp": deposit.timestamp.isoformat(),
            "status": deposit.status
        }

class AgentDepositHistorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='transaction_id')
    type = serializers.SerializerMethodField()
    sender = serializers.CharField(source='agent.agentCode')
    receiver = serializers.CharField(source='receiver_email')
    commission_earned = serializers.DecimalField(max_digits=10, decimal_places=2)
    time_stamp = serializers.DateTimeField(source='timestamp')

    class Meta:
        model = AgentDepositHistory
        fields = ['id', 'type', 'sender', 'receiver', 'amount', 'commission_earned', 'time_stamp', 'status']

    def get_type(self, obj):
        return "deposit"