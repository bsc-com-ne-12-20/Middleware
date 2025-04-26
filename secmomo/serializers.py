from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Agents, AgentApplication
from django.utils import timezone
import random
import string

class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agents
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 
                 'mobile_money_user_id', 'status', 'agent_code', 'phone_number']
        extra_kwargs = {
            'password': {'write_only': True},
            'status': {'read_only': True},
            'agent_code': {'read_only': True}
        }

    def create(self, validated_data):
        user = Agents(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            mobile_money_user_id=validated_data.get('mobile_money_user_id'),
            phone_number=validated_data.get('phone_number'),
            status='pending'
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class AgentLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    agent_code = serializers.CharField(required=False)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        agent_code = data.get('agent_code', None)

        if not username or not password:
            raise serializers.ValidationError("Both username and password are required")

        if '@' in username:
            try:
                user = Agents.objects.get(email=username)
                username = user.username
            except Agents.DoesNotExist:
                raise serializers.ValidationError("Invalid credentials")

        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")
        if user.status != 'active':
            raise serializers.ValidationError("Agent account is not active")
        if agent_code and user.agent_code != agent_code:
            raise serializers.ValidationError("Invalid agent code")

        return {
            'user': user,
            'username': user.username,
            'email': user.email,
            'agent_code': user.agent_code
        }

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

class ResetPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class AgentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agents
        fields = ['username', 'email', 'first_name', 'last_name', 
                 'agent_code', 'status', 'current_balance', 'phone_number']
        read_only_fields = ['username', 'email', 'agent_code', 
                          'status', 'current_balance']

class AgentApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentApplication
        fields = [
            'applicant_type', 'email', 'phone_number', 
            'business_name', 'tax_id', 'id_document', 
            'proof_of_address'
        ]
        extra_kwargs = {
            'business_name': {'required': False},
            'tax_id': {'required': False},
            'id_document': {'required': True},
            'proof_of_address': {'required': True},
        }

    def validate(self, data):
        if data['applicant_type'] == 'business' and not data.get('business_name'):
            raise serializers.ValidationError("Business name is required for business applications")
        return data

class AgentApplicationListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentApplication
        fields = '__all__'
        read_only_fields = ['user', 'status', 'application_date', 
                          'reviewed_by', 'reviewed_at']
class SimpleAgentApplicationSerializer(serializers.ModelSerializer):
    balance = serializers.FloatField(write_only=True, required=False)  # Add this field
    
    class Meta:
        model = AgentApplication
        fields = ['username', 'email', 'phone_number', 'applicant_type', 'business_name', 'balance']
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
            'phone_number': {'required': True},
            'applicant_type': {'required': True},
            'business_name': {'required': False}
        }