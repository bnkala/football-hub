from django.shortcuts import render
from rest_framework import viewsets
from .models import Manager
from .serializers import ManagerSerializer
# Create your views here.

class ManagerViewSet(viewsets.ModelViewSet):
    queryset = Manager.objects.all()
    serializer_class = ManagerSerializer
