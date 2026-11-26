from django.shortcuts import render
from rest_framework import viewsets
from .models import Match
from .serializers import MatchSerializer
from django.db import transaction, IntegrityError
from competitions.models import KnockoutTie
from rest_framework.exceptions import ValidationError, NotFound
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


    def _lock_knockout_tie(self, tie_id):
        if not tie_id:
            return None

        tie = KnockoutTie.objects.select_for_update().get(
            pk=tie_id
        )

        if tie.is_completed:
            raise ValidationError({
                "knockout_tie": (
                    "This knockout tie is already completed. "
                    "Its fixtures cannot be created, "
                    "modified or deleted."
                )
            })

        return tie


    def _lock_fixture(self, fixture_id):
        try:
            return Match.objects.select_for_update().get(pk=fixture_id)

        except Match.DoesNotExist as exc:
            raise NotFound("This fixture no longer exists") from exc

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                tie = serializer.validated_data.get(
                    "knockout_tie"
                )

                locked_tie = self._lock_knockout_tie(
                    tie.pk if tie else None
                )

                if locked_tie:
                    match = serializer.save(
                        knockout_tie=locked_tie
                    )

                    complete_knockout_tie(locked_tie)
                else:
                    serializer.save()

        except IntegrityError as exc:
            self._handle_integrity_error(exc)

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                original = serializer.instance

                requested_tie = serializer.validated_data.get(
                    "knockout_tie",
                    original.knockout_tie,
                )

                tie_id = (
                    original.knockout_tie_id
                    or (
                        requested_tie.pk
                        if requested_tie else None
                    )
                )

                locked_tie = self._lock_knockout_tie(tie_id)

                match = self._lock_fixture(original.pk)
                if match.knockout_tie_id != original.knockout_tie_id:
                    raise ValidationError({
                        "knockout_tie": (
                            "The fixture has changed. "
                            "Please retry your request."
                        )
                    })

                serializer.instance = match

                # Revalidate against the locked, current fixture.
                serializer.validate(
                    serializer.validated_data
                )

                if locked_tie:
                    serializer.save(
                        knockout_tie=locked_tie
                    )

                    complete_knockout_tie(locked_tie)
                else:
                    serializer.save()

        except IntegrityError as exc:
            self._handle_integrity_error(exc)

    def perform_destroy(self, instance):
        with transaction.atomic():
            self._lock_knockout_tie(
                instance.knockout_tie_id
            )

            match = self._lock_fixture(instance.pk)

            if match.knockout_tie_id != instance.knockout_tie_id:
                raise ValidationError({
                    "knockout_tie": (
                        "The fixture has changed. "
                        "Please retry your request."
                    )
                })

            match.delete()

    def _handle_integrity_error(self, exc):
        cause = exc.__cause__
        diagnostic = getattr(cause, "diag", None)
        constraint = getattr(
            diagnostic,
            "constraint_name",
            None,
        )

        if constraint == "unique_knockout_tie_leg":
            raise ValidationError({
                "leg": (
                    "A fixture already exists for "
                    "this knockout tie and leg."
                )
            }) from exc

        if constraint == "valid_knockout_fixture_leg":
            raise ValidationError({
                "leg": "Invalid knockout fixture leg."
            }) from exc

        raise exc