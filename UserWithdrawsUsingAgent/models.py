from django.db import models
from decimal import Decimal
import uuid
from django.db import transaction
from django.db.models import F
from secmomo.models import Agents


class Revenue(models.Model):
    """
    Tracks all transaction fees collected
    """

    total_fees = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    last_updated = models.DateTimeField(auto_now=True)

    @classmethod
    def add_fee(cls, fee_amount):
        """Thread-safe fee accumulation"""
        with transaction.atomic():
            revenue, created = cls.objects.get_or_create(pk=1)
            cls.objects.filter(pk=1).update(
                total_fees=F("total_fees") + Decimal(str(fee_amount))
            )
            revenue.refresh_from_db()
            return revenue

    def __str__(self):
        return f"Total Revenue: {self.total_fees}"


class AgentBalanceUpdate(models.Model):
    agent = models.ForeignKey(
        "secmomo.Agents", on_delete=models.CASCADE, related_name="balance_updates"
    )
    user_email = models.EmailField()
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=12, unique=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = uuid.uuid4().hex[:12].upper()

        if self.gross_amount <= 0:
            raise ValueError("Amount must be positive")

        if not hasattr(self, "net_amount"):
            self.net_amount = self.gross_amount - self.transaction_fee

        super().save(*args, **kwargs)

    def process_transaction(self):
        """Atomically update both agent balance and revenue"""
        with transaction.atomic():
            # Update agent balance
            Agents.objects.filter(pk=self.agent.pk).update(
                current_balance=F("current_balance") + self.net_amount
            )

            # Add fee to revenue
            Revenue.add_fee(self.transaction_fee)

            # Refresh instances
            self.agent.refresh_from_db()
            self.save()

    def __str__(self):
        return f"User {self.user_email} -> Agent {self.agent.agentCode}: ${self.gross_amount}"
