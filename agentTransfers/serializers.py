
# transfer/serializers.py
from rest_framework import serializers
from secmomo.models import Agents
from .models import Transfer
from decimal import Decimal
from UserWithdrawsUsingAgent.models import Revenue

class TransferSerializer(serializers.ModelSerializer):
    sender_agentCode = serializers.CharField(write_only=True)
    receiver_agentCode = serializers.CharField(write_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    id = serializers.CharField(source='trans_id', read_only=True)
    sender = serializers.CharField(source='sender.agentCode', read_only=True)
    receiver = serializers.CharField(source='receiver.agentCode', read_only=True)
    type = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Transfer
        fields = ['id', 'type', 'sender', 'receiver', 'amount', 'commission_earned', 'time_stamp', 'status', 'sender_agentCode', 'receiver_agentCode']

    def get_type(self, obj):
        return "transfer"

    def validate(self, data):
        sender_agentCode = data.get("sender_agentCode")
        receiver_agentCode = data.get("receiver_agentCode")
        amount = data.get("amount")

        if sender_agentCode == receiver_agentCode:
            raise serializers.ValidationError("Sender and receiver cannot be the same.")

        try:
            sender = Agents.objects.get(agentCode=sender_agentCode)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Sender agent does not exist.")

        try:
            receiver = Agents.objects.get(agentCode=receiver_agentCode)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Receiver agent does not exist.")

        total_amount = amount + (amount * Decimal("0.02"))
        if sender.current_balance < total_amount:
            raise serializers.ValidationError("Sender does not have enough balance.")

        return data

    def create(self, validated_data):
        sender_agentCode = validated_data.pop("sender_agentCode")
        receiver_agentCode = validated_data.pop("receiver_agentCode")
        amount = validated_data["amount"]
        commission_earned = amount * Decimal("0.02")

        sender = Agents.objects.get(agentCode=sender_agentCode)
        receiver = Agents.objects.get(agentCode=receiver_agentCode)

        transfer = Transfer(
            sender=sender,
            receiver=receiver,
            sender_email=sender.email,
            receiver_email=receiver.email,
            amount=amount,
            commission_earned=commission_earned,
            status='pending'
        )

        try:
            total_amount = amount + commission_earned
            sender.current_balance -= total_amount
            receiver.current_balance += amount
            sender.save()
            receiver.save()
            Revenue.add_fee(commission_earned)
            transfer.status = 'completed'
            transfer.save()
        except Exception:
            transfer.status = 'failed'
            transfer.save()

        return transfer

class TransferHistorySerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='trans_id')
    type = serializers.SerializerMethodField()
    sender = serializers.CharField(source='sender.agentCode')
    receiver = serializers.CharField(source='receiver.agentCode')
    time_stamp = serializers.DateTimeField()

    class Meta:
        model = Transfer
        fields = ['id', 'type', 'sender', 'receiver', 'amount', 'commission_earned', 'time_stamp', 'status']

    def get_type(self, obj):
        return "transfer"
