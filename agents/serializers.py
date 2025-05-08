from rest_framework import serializers
from secmomo.models import Agents, AgentApplication


class AgentApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentApplication
        fields = (
            "username",
            "application_date",
        )


class UserSerializer(serializers.ModelSerializer):
    agent = AgentApplicationSerializer(read_only=True)

    class Meta:
        model = Agents
        fields = (
            "agentCode",
            "email",
            "current_balance",
            "phone_number",
            "agent",
        )
