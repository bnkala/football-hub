from django.shortcuts import render
from rest_framework import viewsets
from .models import Competition, Season, CompetitionEntry
from .serializers import CompetitionSerializer, SeasonSerializer, CompetitionEntrySerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from .standings import calculate_standings
# Create your views here.

class CompetitionViewSet(viewsets.ModelViewSet):
    queryset = Competition.objects.all()
    serializer_class = CompetitionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        competition_type = self.request.query_params.get("type")
        country = self.request.query_params.get("country")
        confederation = self.request.query_params.get("confederation")

        if competition_type:
            queryset = queryset.filter(competition_type=competition_type.upper())

        if country:
            queryset = queryset.filter(country__iexact=country)

        if confederation:
            queryset = queryset.filter(confederation__iexact=confederation)

        return queryset

class SeasonViewSet(viewsets.ModelViewSet):
    queryset = Season.objects.all().order_by("-start_date")
    serializer_class = SeasonSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        competition = self.request.query_params.get("competition")
        current = self.request.query_params.get("current")

        if competition:
            queryset = queryset.filter(competition_id=competition)

        if current is not None:
            if current.lower() in ("true", "1"):
                queryset = queryset.filter(is_current=True)
            elif current.lower() in ("false", "0"):
                queryset = queryset.filter(is_current=False)

        return queryset

    @action(detail=True, methods=["get"], url_path="standings")
    def standings(self, request, pk=None):
        season = self.get_object()

        table = calculate_standings(season)

        return Response({
            "competition": season.competition.name,
            "season": season.name,
            "standings": table,
        })


class CompetitionEntryViewSet(viewsets.ModelViewSet):
    queryset = CompetitionEntry.objects.all()
    serializer_class = CompetitionEntrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        serializer_class = CompetitionEntrySerializer

        season = self.request.query_params.get("season")
        club = self.request.query_params.get("club")
        competition = self.request.query_params.get("competition")

        if season:
            queryset = queryset.filter(season_id=season)

        if club:
            queryset = queryset.filter(club_id=club)

        if competition:
            queryset = queryset.filter(season__competition_id=competition)

        return queryset

