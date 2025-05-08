from django.db import models
import uuid
from decimal import Decimal
from secmomo.models import Agents

class Transfer(models.Model):
    sender = models.ForeignKey(Agents, on_delete=models.CASCADE, related_name="sent_transfers")
    receiver = models.ForeignKey(Agents, on_delete=models.CASCADE, related_name="received_transfers")
    sender_email = models.EmailField(null=True, blank=True, default="unknown@example.com")
    receiver_email = models.EmailField(null=True, blank=True, default="unknown@example.com")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    time_stamp = models.DateTimeField(auto_now_add=True)
    trans_id = models.CharField(max_length=12, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ), default='pending')

    def save(self, *args, **kwargs):
        if not self.trans_id:
            self.trans_id = uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Transfer {self.trans_id} from {self.sender_email} to {self.receiver_email}"

    class Meta:
        indexes = [
            models.Index(fields=['sender', 'time_stamp']),
            models.Index(fields=['receiver', 'time_stamp']),
            models.Index(fields=['status']),
        ]