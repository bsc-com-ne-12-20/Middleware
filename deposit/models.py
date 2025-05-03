from django.db import models
from secmomo.models import Agents

class Deposit(models.Model):
    agent = models.ForeignKey(Agents, on_delete=models.CASCADE, related_name='deposits')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ), default='pending')
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.agent.username} - {self.amount} - {self.status}"

    class Meta:
        ordering = ['-timestamp']

class AgentDepositHistory(models.Model):
    agent = models.ForeignKey(Agents, on_delete=models.CASCADE, related_name='deposit_history')
    user_email = models.EmailField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=12, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    commission_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ), default='completed')

    def __str__(self):
        return f"{self.agent.email} sent {self.amount} to {self.user_email}"

    class Meta:
        ordering = ['-timestamp']