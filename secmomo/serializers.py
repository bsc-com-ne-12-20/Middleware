from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Agents, AgentApplication
from django.utils import timezone
import re

# ----------------------------
# Phone Number Helper Methods
# ----------------------------

def normalize_phone(value):
    """Normalize phone number (remove spaces and dashes)."""
    return value.strip().replace(" ", "").replace("-", "")

def normalize_phone(value):
    """Normalize phone number by removing spaces, dashes, and parentheses."""
    return ''.join(filter(str.isdigit, str(value))) if value else ''

def validate_phone_number(value):
    """Ensure phone number format is valid and normalize it."""
    value = normalize_phone(value)
    
    # Ensure the phone number starts with +265 followed by a digit 1-9
    if not re.match(r'^\+265[1-9][0-9]{6,11}$', value):
        raise serializers.ValidationError("Phone number must start with +265 followed by a digit 1-9 and be 10 to 15 digits long.")
    
    return value

# ----------------------------
# AgentSerializer (Registration)
# ----------------------------

class AgentSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(validators=[validate_phone_number])

    class Meta:
        model = Agents
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 
                  'mobile_money_user_id', 'status', 'agentCode', 'phone_number']
        extra_kwargs = {
            'password': {'write_only': True},
            'status': {'read_only': True},
            'agentCode': {'read_only': True}
        }

    def validate_phone_number(self, value):
        value = validate_phone_number(value)
        if Agents.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already in use.")
        return value

    def create(self, validated_data):
        validated_data['phone_number'] = normalize_phone(validated_data['phone_number'])

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

# ----------------------------
# Login
# ----------------------------

class AgentLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    agentCode = serializers.CharField(required=False)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        agentCode = data.get('agentCode', None)

        if not email or not password:
            raise serializers.ValidationError("Both email and password are required")

        try:
            user = Agents.objects.get(email=email)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")

        user = authenticate(username=user.username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")
        if user.status != 'active':
            raise serializers.ValidationError("Agent account is not active")
        if agentCode and user.agentCode != agentCode:
            raise serializers.ValidationError("Invalid agent code")

        return {
            'user': user,
            'email': user.email,
            'agentCode': user.agentCode
        }

# ----------------------------
# Password Management
# ----------------------------

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
class ResetPasswordEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

# ----------------------------
# Agent Profile
# ----------------------------

class AgentProfileSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(validators=[validate_phone_number])

    class Meta:
        model = Agents
        fields = ['username', 'email', 'first_name', 'last_name', 
                  'agentCode', 'status', 'current_balance', 'phone_number']
        read_only_fields = ['username', 'email', 'agentCode', 
                            'status', 'current_balance']

# ----------------------------
# Agent Application
# ----------------------------

class AgentApplicationSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(validators=[validate_phone_number])

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
    balance = serializers.FloatField(write_only=True, required=False)
    phone_number = serializers.CharField(validators=[validate_phone_number])

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

# ----------------------------
# Email Utility Serializers
# ----------------------------

class EmailToUsernameSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            agent = Agents.objects.get(email=value)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Agent with this email does not exist.")
        return value

    def get_username(self):
        email = self.validated_data['email']
        agent = Agents.objects.get(email=email)
        return agent.username

class EmailToBalanceSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            agent = Agents.objects.get(email=value)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Agent with this email does not exist.")
        return value

    def get_balance(self):
        email = self.validated_data['email']
        agent = Agents.objects.get(email=email)
        return agent.current_balance
