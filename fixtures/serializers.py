
from rest_framework import serializers
from .models import Match
from competitions.models import CompetitionEntry


class MatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = "__all__"

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

        return attrs
