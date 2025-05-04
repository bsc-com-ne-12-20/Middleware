from django.db import models
from secmomo.models import Agents

class AgentDepositHistory(models.Model):
    agent = models.ForeignKey(Agents, on_delete=models.CASCADE, related_name='deposit_history')
    sender_email = models.EmailField(null=True, blank=True)  # Agent's email
    receiver_email = models.EmailField(null=True, blank=True, default="unknown@example.com")  # User's email
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=12, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    commission_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ), default='pending')

    def __str__(self):
        return f"{self.sender_email} sent {self.amount} to {self.receiver_email}"

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['agent', 'timestamp']),
            models.Index(fields=['status']),
        ]