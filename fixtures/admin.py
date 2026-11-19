from django.contrib import admin
from .models import Match

# Register your models here.
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        "home_club",
        "away_club",
        "kickoff",
        "status",
        "home_score",
        "away_score",
        "matchweek",
    )

    list_fileter = (
        "league",
        "status",
        "matchweek",
    )

    search_fields = (
        "home_club__name",
        "away_club__name",
    )

    ordering = ("-kickoff",)