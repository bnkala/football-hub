from django.shortcuts import render

from rest_framework.viewsets import ModelViewSet

from .models import League
from .serializers import LeagueSerializer
# Create your views here.


class LeagueViewSet(ModelViewSet):
    queryset = League.objects.all()
    serializer_class = LeagueSerializer

    