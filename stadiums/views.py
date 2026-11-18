from django.shortcuts import render
from rest_framework import viewsets
from .models import Stadium
from .serializers import StadiumSerializer
# Create your views here.

class StadiumViewSet(viewsets.ModelViewSet):
    queryset = Stadium.objects.all()
    serializer_class = StadiumSerializer
