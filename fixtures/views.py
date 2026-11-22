from django.shortcuts import render
from rest_framework import viewsets
from .models import Match
from .serializers import MatchSerializer
# Create your views here.

class MatchViewSet(viewsets.ModelViewSet):
    queryset = Match.objects.all().order_by("-kickoff")
    serializer_class = MatchSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        league = self.request.query_params.get("league")
        club = self.request.query_params.get("club")
        status = self.request.query_params.get("status")
        matchweek = self.request.query_params.get("matchweek")
        season = self.request.query_params.get("season")
        competition = self.request.query_params.get("competition")

        if league:
            queryset = queryset.filter(league_id=league)

        if club:
            from django.db.models import Q
            queryset = queryset.filter(Q(home_club_id=club) | Q(away_club_id=club))

        if status:
            queryset = queryset.filter(status=status.upper())

        if matchweek:
            queryset = queryset.filter(matchweek=matchweek)

        if season:
            queryset = queryset.filter(season_id=season)

        if competition:
            queryset = queryset.filter(season__compeition_id=competition)

        return queryset
