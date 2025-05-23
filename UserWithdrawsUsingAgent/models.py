# UserWithdrawsUsingAgent/models.py
from django.db import models
from decimal import Decimal
import uuid
from django.db import transaction
from django.db.models import F
from secmomo.models import Agents

class Revenue(models.Model):
    total_fees = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    last_updated = models.DateTimeField(auto_now=True)

    @classmethod
    def add_fee(cls, fee_amount):
        with transaction.atomic():
            revenue, created = cls.objects.get_or_create(pk=1)
            cls.objects.filter(pk=1).update(total_fees=F("total_fees") + Decimal(str(fee_amount)))
            revenue.refresh_from_db()
            return revenue

    def __str__(self):
        return f"Total Revenue: {self.total_fees}"

class AgentWithdrawalHistory(models.Model):
    agent = models.ForeignKey(Agents, on_delete=models.CASCADE, related_name="withdrawal_history")
    sender_email = models.EmailField(blank=True, null=True)  # Optional for deposits
    receiver_email = models.EmailField(blank=True, null=True)  # Optional for deposits
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    transaction_id = models.CharField(max_length=12, unique=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ),
        default='pending'
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=['agent', 'timestamp']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = uuid.uuid4().hex[:12].upper()

        if self.gross_amount <= 0:
            raise ValueError("Amount must be positive")

        if self.net_amount is None:
            self.net_amount = self.gross_amount  # Net equals gross for deposits

        super().save(*args, **kwargs)

    def process_transaction(self):
        with transaction.atomic():
            Agents.objects.filter(pk=self.agent.pk).update(
                current_balance=F("current_balance") + self.net_amount
            )
            if self.commission_earned > 0:  # Skip Revenue update for deposits
                Revenue.add_fee(self.commission_earned)
            self.agent.refresh_from_db()
            self.save()

    def __str__(self):
        return f"{'Deposit' if not self.sender_email else self.sender_email} -> {self.agent.agentCode}: ${self.gross_amount}"