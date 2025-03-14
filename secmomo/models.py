from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.conf import settings  # Ensure this import is at the top

class Agents(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    number = models.CharField(max_length=20, unique=True)  # No default value
    agent_code = models.CharField(max_length=50, unique=True)  # No default value
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.username} - {self.agent_code}"


class Transaction(models.Model):
    agent = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)  # Use get_user_model() for compatibility
    date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10)  # e.g., 'withdrawal'

    def __str__(self):
        return f"{self.transaction_type.capitalize()} of {self.amount} by {self.agent.username} on {self.date}"
    
#Handle verification identity from esignet
class IdentityVerification(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Verified: {self.is_verified}"