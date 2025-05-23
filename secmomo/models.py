from django.db import models
from django.contrib.auth.models import AbstractUser
import random
import string
from django.core.exceptions import ValidationError

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

# ✅ Final Agents model version (used as AUTH_USER_MODEL)
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
    phone_number = models.CharField(max_length=15, blank=True, null=False)
    
    MAX_BALANCE = 1_000_000.00  # Define the max balance

    def add_to_balance(self, amount):
        """Safely add amount to balance with validation."""
        if self.current_balance + amount > self.MAX_BALANCE:
            raise ValidationError("Agent balance cannot exceed 1,000,000.00.")
        self.current_balance += amount
        self.save()

    #def save(self, *args, **kwargs):
    #    if not self.agentCode:
    #        self.agentCode = self._generate_agentCode()
    #
    #    # Ensure unique username, if it's not provided, auto-generate one
    #    if not self.username:
    #        self.username = self._generate_unique_username()
    #
    #    super().save(*args, **kwargs)
    
    #def _generate_agentCode(self):
    #    """Genesrate unique 6-digit numerical code"""
    #    while True:
    #        code = str(random.randint(123000, 123999))  # 6-digit number
    #        if not Agents.objects.filter(agentCode=code).exists():
    #            return code
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
