
from rest_framework import serializers
from decimal import Decimal
import uuid
import requests
from secmomo.models import Agents
from .models import AgentDepositHistory

class AgentDepositHistorySerializer(serializers.ModelSerializer):
    trans_id = serializers.CharField(source='transaction_id')
    sender = serializers.CharField(source='agent.email')
    receiver = serializers.CharField(source='user_email', allow_null=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=True)
    transaction_fee = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=True)
    time_stamp = serializers.DateTimeField(source='timestamp')
    commission = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=True)
    agentCode = serializers.CharField(source='agent.agentCode')

    class Meta:
        model = AgentDepositHistory
        fields = ['trans_id', 'sender', 'receiver', 'amount', 'transaction_fee', 'time_stamp', 'commission', 'agentCode']

class AgentDepositSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    agentCode = serializers.CharField(write_only=True)
    transaction_id = serializers.CharField(read_only=True)

    class Meta:
        model = AgentDepositHistory
        fields = ['agentCode', 'email', 'amount', 'transaction_id', 'timestamp']

    def validate(self, data):
        # For authorized use only, use:
        # agent = self.context['request'].user
        agentCode = data.get("agentCode")
        amount = data.get("amount")

        # Fetch agent using the provided agent code
        try:
            agent = Agents.objects.get(agentCode=agentCode)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Agent with this code does not exist.")

        # Check if the agent has sufficient balance
        if agent.current_balance < amount:
            raise serializers.ValidationError("Insufficient balance.")

        # Attach the agent instance to validated data for use in create
        data["agent"] = agent
        return data

    def create(self, validated_data):
        agent = validated_data.pop("agent")  # Get the agent instance
        user_email = validated_data.get("email")  # Get the user email
        amount = validated_data["amount"]
        commission = amount * Decimal('0.02')  # Calculate 2% commission
        transaction_id = uuid.uuid4().hex[:12].upper()  # Generate a unique transaction ID

        # Prepare the payload for the external deposit API
        external_payload = {
            "email": user_email,
            "amount": str(amount),
            "transaction_id": transaction_id
        }

        # Call external API to process the deposit
        response = requests.post(
            "https://mtima.onrender.com/api/v1/dpst/",  # Adjust this URL as needed
            json=external_payload
        )

        if response.status_code == 201:  # If the external API responds with HTTP 201 (Created)
            # Update the agent's balance
            agent.current_balance -= amount
            agent.save()

            # Record the deposit in the local history
            deposit = AgentDepositHistory.objects.create(
                agent=agent,
                user_email=user_email,
                amount=amount,
                transaction_id=transaction_id,
                transaction_fee=Decimal('0.00'),
                commission=commission
            )

            # Prepare and return the custom response format
            return {
                "agentCode": agent.agentCode,
                "receiver_email": user_email,
                "status": "success",
                "amount": str(amount),
                "transaction_id": transaction_id,
                "timestamp": deposit.timestamp,
                "transaction_fee": "0.00",
                "commission": str(commission)
            }
        else:
            # Handle errors from the external API
            error_details = response.json() if response.headers.get("Content-Type") == "application/json" else response.text
            raise serializers.ValidationError({
                "external_api_error": error_details
            })