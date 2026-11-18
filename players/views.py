from django.shortcuts import render
from rest_framework import viewsets
from .models import Player
from .serializers import PlayerSerializer
# Create your views here.

class PlayerViewSet(viewsets.ModelViewSet):
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        club = self.request.query_params.get("club")
        position = self.request.query_params.get("position")

        if club:
            queryset = queryset.filter(club_id=club)

        if position:
            queryset = queryset.filter(position=position.upper())

        return queryset
    
