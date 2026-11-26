
from rest_framework import serializers
from .models import Match
from leagues.models import League
from competitions.models import CompetitionEntry


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = "__all__"

    league = serializers.PrimaryKeyRelatedField(
        queryset=League.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        instance = self.instance

        home_club = attrs.get(
            "home_club",
            getattr(instance, "home_club", None)
        )
        away_club = attrs.get(
            "away_club",
            getattr(instance, "away_club", None)
        )
        season = attrs.get(
            "season",
            getattr(instance, "season", None)
        )
        status = attrs.get(
            "status",
            getattr(instance, "status", "SCHEDULED")
        )
        home_score = attrs.get(
            "home_score",
            getattr(instance, "home_score", None)
        )
        away_score = attrs.get(
            "away_score",
            getattr(instance, "away_score", None)
        )

        knockout_tie = attrs.get("knockout_tie", getattr(instance, "knockout_tie", None))

        leg = attrs.get("leg", getattr(instance, "leg", None))

        # Prevent a club from playing itself.
        if home_club and away_club and home_club == away_club:
            raise serializers.ValidationError({
                "away_club": "A club cannot play against itself."
            })

        # Check participation in the selected season.
        if season:
            for field, club in (
                ("home_club", home_club),
                ("away_club", away_club),
            ):
                if club and not CompetitionEntry.objects.filter(
                    season=season,
                    club=club
                ).exists():
                    raise serializers.ValidationError({
                        field: (
                            "This club is not registered "
                            "for the selected season."
                        )
                    })

        # Finished matches must have a complete score.
        if status == "FINISHED":
            if home_score is None or away_score is None:
                raise serializers.ValidationError({
                    "status": (
                        "A finished match must have "
                        "both home and away scores."
                    )
                })

        if instance and instance.knockout_tie_id:
            if knockout_tie != instance.knockout_tie:
                raise serializers.ValidationError({
                    "knockout_tie": "An existing knockout fixture cannot be reassigned or detached from its tie."
                })

        # Validate knockout fixtures.
        if knockout_tie:
            if knockout_tie.is_completed:
                raise serializers.ValidationError({
                    "knockout_tie": "This knockout tie is already completed. Its fixtures cannot be created or modified."
                })
            knockout_round = knockout_tie.knockout_round

            if season != knockout_round.season:
                raise serializers.ValidationError({
                    "season": (
                        "The fixture season must match "
                        "the knockout tie season."
                    )
                })

            if leg not in (1, 2):
                raise serializers.ValidationError({
                    "leg": (
                        "A knockout fixture must have "
                        "a valid leg number."
                    )
                })

            if (
                knockout_round.tie_format == "SINGLE_LEG"
                and leg != 1
            ):
                raise serializers.ValidationError({
                    "leg": (
                        "A single-leg knockout tie "
                        "cannot have a second leg."
                    )
                })

            if leg == 1:
                expected_home = knockout_tie.home_club
                expected_away = knockout_tie.away_club
            else:
                expected_home = knockout_tie.away_club
                expected_away = knockout_tie.home_club

            if (
                home_club != expected_home
                or away_club != expected_away
            ):
                raise serializers.ValidationError({
                    "knockout_tie": (
                        "Fixture clubs must match the "
                        "knockout tie and leg."
                    )
                })

            existing_fixtures = Match.objects.filter(
                knockout_tie=knockout_tie,
                leg=leg,
            )

            if instance:
                existing_fixtures = existing_fixtures.exclude(
                    pk=instance.pk
                )

            if existing_fixtures.exists():
                raise serializers.ValidationError({
                    "leg": (
                        "A fixture already exists for "
                        "this knockout tie and leg."
                    )
                })

        elif leg is not None:
            raise serializers.ValidationError({
                "leg": (
                    "A leg number requires a knockout tie."
                )
            })

        return attrs
