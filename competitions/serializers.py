
from rest_framework import serializers
from .models import Competition, Season, CompetitionEntry



class CompetitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competition
        fields = "__all__"


class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = "__all__"


class CompetitionEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompetitionEntry
        fields = "__all__"

class KnockoutProgressionSerializer(serializers.Serializer):
    first_kickoff = serializers.DateTimeField(
        required=False,
    )

    days_between_legs = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=365,
        default=7,
    )

    def validate(self, attrs):
        if (
            "days_between_legs" in self.initial_data
            and "first_kickoff" not in attrs
        ):
            raise serializers.ValidationError({
                "first_kickoff": (
                    "A kickoff date is required when "
                    "specifying days between legs."
                )
            })

        return attrs
