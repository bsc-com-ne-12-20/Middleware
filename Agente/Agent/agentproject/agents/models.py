from django.db import models

# Create your models here.
# agents/models.py
import random
import string
from django.db import models

def generate_unique_agent_code():
    """Generate a unique agent code."""
    length = 8
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not Agent.objects.filter(agent_code=code).exists():
            return code

class Agent(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    number = models.CharField(max_length=15)
    agent_code = models.CharField(max_length=8, unique=True, default=generate_unique_agent_code)
    balance = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name
