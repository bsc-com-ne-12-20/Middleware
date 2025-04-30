from rest_framework import serializers
from secmomo.models import Agents
from .models import Revenue, Transfer
from decimal import Decimal


class TransferSerializer(serializers.ModelSerializer):
    sender_agent_code = serializers.CharField(write_only=True)
    receiver_agent_code = serializers.CharField(write_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    trans_id = serializers.CharField(read_only=True)
    transaction_fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Transfer
        fields = [
            "sender_agent_code",
            "receiver_agent_code",
            "amount",
            "transaction_fee",
            "trans_id",
            "time_stamp",
        ]

    def validate(self, data):
        sender_agent_code = data.get("sender_agent_code")
        receiver_agent_code = data.get("receiver_agent_code")
        amount = data.get("amount")

        if sender_agent_code == receiver_agent_code:
            raise serializers.ValidationError("Sender and receiver cannot be the same.")

        try:
            sender = Agents.objects.get(agent_code=sender_agent_code)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Sender agent does not exist.")

        transaction_fee = amount * Decimal("0.03")
        total_amount = amount + transaction_fee

        if sender.current_balance < 500:
            raise serializers.ValidationError(
                "Sender does not have enough balance. Please despodit to your account"
            )

        if sender.current_balance < total_amount:
            raise serializers.ValidationError(
                "Sender does not have enough balance to cover the transaction and fee."
            )

        try:
            Agents.objects.get(agent_code=receiver_agent_code)
        except Agents.DoesNotExist:
            raise serializers.ValidationError("Receiver agent does not exist.")

        return data

    def create(self, validated_data):
        sender_agent_code = validated_data.pop("sender_agent_code")
        receiver_agent_code = validated_data.pop("receiver_agent_code")
        amount = validated_data["amount"]
        transaction_fee = amount * Decimal("0.03")

        sender = Agents.objects.get(agent_code=sender_agent_code)
        receiver = Agents.objects.get(agent_code=receiver_agent_code)

        sender.current_balance -= amount + transaction_fee
        receiver.current_balance += amount

        sender.save()
        receiver.save()

        Revenue.add_fee(transaction_fee)

        transfer = Transfer.objects.create(
            sender=sender,
            receiver=receiver,
            amount=amount,
            transaction_fee=transaction_fee,
        )

        return transfer


class TransferHistorySerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_email = serializers.EmailField(source="sender.email")
    receiver_name = serializers.SerializerMethodField()
    receiver_email = serializers.EmailField(source="receiver.email")

    class Meta:
        model = Transfer
        fields = [
            "trans_id",
            "sender_name",
            "sender_email",
            "receiver_name",
            "receiver_email",
            "amount",
            "transaction_fee",
            "time_stamp",
        ]

    def get_sender_name(self, obj):
        return f"{obj.sender.username}"

    def get_receiver_name(self, obj):
        return f"{obj.receiver.username}"
