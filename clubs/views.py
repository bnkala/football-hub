from django.shortcuts import render

from rest_framework.viewsets import ModelViewSet

from .models import Club
from .serializers import ClubSerializer

# Create your views here.

class ClubViewSet(ModelViewSet):
    queryset = Club.objects.select_related("league").all()
    serializer_class = ClubSerializer