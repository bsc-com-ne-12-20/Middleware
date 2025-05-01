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
        #for authorized use only use 
        #agent = self.context['request'].user(remove agent code)
        agent_code = data.get("agent_code")
        amount = data.get("amount")

        # Fetch agent using the provided agent code
        try:
            agent = Agents.objects.get(agent_code=agent_code)#this line will be removed for authenticated user
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
        user_email = validated_data["email"]  # Get the user email
        amount = validated_data["amount"]
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
                transaction_id=transaction_id
            )

            # Prepare and return the custom response format
            return {
                "agent_code": agent.agent_code,
                "receiver_email": user_email,
                "status": "success",
                "amount": str(amount),
                "transaction_id": transaction_id,
                "timestamp": deposit.timestamp
            }
        else:
            # Handle errors from the external API
            error_details = response.json() if response.headers.get("Content-Type") == "application/json" else response.text
            raise serializers.ValidationError({
                "external_api_error": error_details
            })


class AgentDepositHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentDepositHistory
        fields = ['transaction_id', 'user_email', 'amount', 'timestamp']
