
from rest_framework import serializers # type: ignore
from .models import Agents

class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agents
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'number', 'agent_code', 'balance']
        extra_kwargs = {
            'password': {'write_only': True},
            'balance': {'read_only': True}  # Optional: Prevent balance from being set during registration
        }

    def create(self, validated_data):
        # Remove balance from validated_data if it's present
        validated_data.pop('balance', None)

        user = Agents(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            number=validated_data['number'],
            agent_code=validated_data['agent_code'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

#reset password selializer
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

class ResetPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)