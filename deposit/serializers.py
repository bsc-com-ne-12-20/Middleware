from rest_framework import serializers
from decimal import Decimal
import uuid
import requests
from secmomo.models import Agents
from .models import AgentDepositHistory

class AgentDepositSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    agent_code = serializers.CharField(write_only=True)
    transaction_id = serializers.CharField(read_only=True)

    class Meta:
        model = AgentDepositHistory
        fields = ['agent_code', 'email', 'amount', 'transaction_id', 'timestamp']

    def validate(self, data):
        agent_code = data.get("agent_code")
        amount = data.get("amount")

        try:
            agent = Agents.objects.get(agentCode=agent_code)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Agent with this code does not exist.")

        if agent.current_balance < amount:
            raise serializers.ValidationError("Insufficient balance.")

        data["agent"] = agent
        return data

    def create(self, validated_data):
        agent = validated_data.pop("agent")
        user_email = validated_data["email"]
        amount = validated_data["amount"]
        transaction_id = uuid.uuid4().hex[:12].upper()

        # Create initial record with pending status
        deposit = AgentDepositHistory.objects.create(
            agent=agent,
            user_email=user_email,
            amount=amount,
            transaction_id=transaction_id,
            commission_earned=Decimal('0.00'),
            status='pending'
        )

        # Prepare the payload for the external deposit API
        external_payload = {
            "email": user_email,
            "amount": str(amount),
            "transaction_id": transaction_id
        }

        try:
            # Call external API to process the deposit
            response = requests.post(
                "https://mtima.onrender.com/api/v1/dpst/",
                json=external_payload
            )

            if response.status_code == 201:
                # Update agent's balance and set status to completed
                agent.current_balance -= amount
                agent.save()
                deposit.status = 'completed'
            else:
                # Set status to failed on non-success response
                deposit.status = 'failed'
                
            deposit.save()

        except requests.exceptions.RequestException as e:
            # Handle network or API errors
            deposit.status = 'failed'
            deposit.save()

        # Return response with all required fields
        return {
            "id": transaction_id,
            "type": "deposit",
            "sender": agent.agentCode,
            "receiver": user_email,
            "amount": str(amount),
            "commission_earned": str(deposit.commission_earned),
            "time_stamp": deposit.timestamp.isoformat(),
            "status": deposit.status
        }

class AgentDepositHistorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='transaction_id')
    type = serializers.SerializerMethodField()
    sender = serializers.CharField(source='agent.agentCode')
    receiver = serializers.CharField(source='user_email')
    commission_earned = serializers.DecimalField(max_digits=10, decimal_places=2)
    time_stamp = serializers.DateTimeField(source='timestamp')

    class Meta:
        model = AgentDepositHistory
        fields = ['id', 'type', 'sender', 'receiver', 'amount', 'commission_earned', 'time_stamp', 'status']

    def get_type(self, obj):
        return "deposit"