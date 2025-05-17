
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

    # Set a maximum deposit limit
    MAX_DEPOSIT_LIMIT = Decimal('10000.00')  # Set the limit as per your requirements

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

        # Check if deposit exceeds the maximum limit
        if amount > self.MAX_DEPOSIT_LIMIT:
            raise serializers.ValidationError(f"Deposit amount exceeds the maximum limit of {self.MAX_DEPOSIT_LIMIT}.")

        # Ensure the agent has enough balance (if it's a withdrawal deposit or transfer)
        if agent.current_balance < amount:
            raise serializers.ValidationError("Insufficient balance to process this deposit.")

        data["agent"] = agent
        return data

    def create(self, validated_data):
        agent = validated_data.pop("agent")
        receiver_email = validated_data["email"]
        amount = validated_data["amount"]
        transaction_id = uuid.uuid4().hex[:12].upper()
        commission = amount * Decimal('0.02')  # 2% commission

        # Create the deposit history record
        deposit = AgentDepositHistory.objects.create(
            agent=agent,
            sender_email=agent.email,
            receiver_email=receiver_email,
            amount=amount,
            transaction_id=transaction_id,
            commission_earned=commission,
            status='pending'
        )

        # Define the payload to send to the external API
        external_payload = {
            "email": receiver_email,
            "amount": str(amount),
            "transaction_id": transaction_id
        }

        try:
            # Make the API call to the external payment system
            response = requests.post(
                "https://mtima.onrender.com/api/v1/dpst/",
                json=external_payload
            )

            if response.status_code == 201:
                # Successful external deposit; update agent's balance
                agent.current_balance -= amount  # Deduct deposit amount
                agent.current_balance += commission  # Add commission
                agent.save()
                deposit.status = 'completed'
            else:
                deposit.status = 'failed'

            deposit.save()

        except requests.exceptions.RequestException:
            deposit.status = 'failed'
            deposit.save()

        # Return transaction details
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