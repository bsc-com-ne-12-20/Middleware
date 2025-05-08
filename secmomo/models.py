from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.conf import settings
import random
import string

"""
class Agents(AbstractUser):
    AGENT_STATUS = (
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    )
      
    agentCode = models.CharField(max_length=10, unique=True, null=True, blank=True)
    status = models.CharField(max_length=10, choices=AGENT_STATUS, default='pending')
    mobile_money_user_id = models.PositiveIntegerField(null=True, blank=True)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
"""


class Agents(AbstractUser):
    AGENT_STATUS = (
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    )
      
    agentCode = models.CharField(max_length=10, unique=True, null=True, blank=True)
    status = models.CharField(max_length=10, choices=AGENT_STATUS, default='active')  # Changed from 'pending' to 'active'
    mobile_money_user_id = models.PositiveIntegerField(null=True, blank=True)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    phone_number = models.CharField(max_length=15, blank=True)
    


    def save(self, *args, **kwargs):
        if not self.agentCode:
            self.agentCode = self._generate_agentCode()
        super().save(*args, **kwargs)
    
    def _generate_agentCode(self):
        """Generate unique 6-digit numerical code"""
        while True:
            code = str(random.randint(100000, 999999))  # 6-digit number
            if not Agents.objects.filter(agentCode=code).exists():
                return code
class AgentApplication(models.Model):
    APPLICANT_TYPES = (
        ('individual', 'Individual'),
        ('business', 'Business'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    user = models.ForeignKey(Agents, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=50, null=True, blank=True)
    applicant_type = models.CharField(max_length=10, choices=APPLICANT_TYPES)
    email = models.EmailField()
    phone_number = models.CharField(max_length=15)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    business_name = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    application_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    verification_notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(Agents, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Application from {self.email}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['username'], name='unique_application_username')
        ]
        ordering = ['-application_date']
        verbose_name = "Agent Application"
        verbose_name_plural = "Agent Applications"