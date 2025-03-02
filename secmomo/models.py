from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class Agents(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    # Add custom fields here, if needed
    

    def __str__(self):
        return self.username
