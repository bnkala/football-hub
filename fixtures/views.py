from django.shortcuts import render
from rest_framework import viewsets
from .models import Match
from .serializers import MatchSerializer
from django.db import transaction
from rest_framework.exceptions import ValidationError
from competitions.knockout import complete_knockout_tie
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
            queryset = queryset.filter(season__competition_id=competition)

        return queryset


    def perform_create(self, serializer):
        with transaction.atomic():
            match = serializer.save()

            if match.knockout_tie_id:
                complete_knockout_tie(match.knockout_tie)

    def perform_update(self, serializer):
        with transaction.atomic():
            match = serializer.instance

            if (
                match.knockout_tie_id
                and match.knockout_tie.is_completed
            ):
                raise ValidationError({
                    "knockout_tie": (
                        "This knockout tie is already completed. "
                        "Its fixtures cannot be modified."
                    )
                })

            updated_match = serializer.save()

            if updated_match.knockout_tie_id:
                complete_knockout_tie(
                    updated_match.knockout_tie
                )

    def perform_destroy(self, instance):
        if (
            instance.knockout_tie_id
            and instance.knockout_tie.is_completed
        ):
            raise ValidationError({
                "knockout_tie": (
                    "Cannot delete a fixture belonging "
                    "to a completed knockout tie."
                )
            })

        instance.delete()
