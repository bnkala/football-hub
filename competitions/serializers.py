
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