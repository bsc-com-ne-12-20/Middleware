from django.shortcuts import render

# Create your views here.

from rest_framework import generics
from secmomo.models import Agents
from .serializers import UserSerializer


class UserAPIView(generics.ListCreateAPIView):
    queryset = Agents.objects.all()
    serializer_class = UserSerializer
