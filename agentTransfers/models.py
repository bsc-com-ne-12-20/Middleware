from django.db import models
import uuid
from decimal import Decimal

# Create your models here.


class Transfer(models.Model):
    sender = models.ForeignKey(
        "secmomo.Agents", on_delete=models.CASCADE, related_name="sent_transfers"
    )
    receiver = models.ForeignKey(
        "secmomo.Agents", on_delete=models.CASCADE, related_name="received_transfers"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    time_stamp = models.DateTimeField(auto_now_add=True)
    trans_id = models.CharField(max_length=12, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.trans_id:
            self.trans_id = uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transfer {self.trans_id} from {self.sender.email} to {self.receiver.email}"  # Display sender and receiver emails


class Revenue(models.Model):
    total_fees_collected = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal(0.00)
    )

    @classmethod
    def add_fee(cls, fee):
        revenue, created = cls.objects.get_or_create(pk=1)  # Singleton revenue record
        revenue.total_fees_collected += Decimal(str(fee))  # Convert fee to Decimal
        revenue.save()

    def __str__(self):
        return f"Revenue: {self.total_fees_collected}"
