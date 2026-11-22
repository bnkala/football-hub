from django.contrib import admin
from .models import Competition, Season, CompetitionEntry, KnockoutRound, KnockoutTie
# Register your models here.

@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "competition_type",
        "country",
        "confederation",
        "founded",
    )

    list_filter = ("competition_type", "country", "confederation")
    search_fields = ("name", "country", "confederation")
    ordering = ("name",)

@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "competition",
        "start_date",
        "end_date",
        "is_current",
    )

    list_filter = ("competition", "is_current")
    search_fields = ("name", "competition__name")
    ordering = ("-start_date",)

@admin.register(CompetitionEntry)
class CompetitionEntryAdmin(admin.ModelAdmin):
    list_display = (
        "club",
        "get_competition",
        "season",
        "joined_at",
    )

    list_filter = ("season__competition", "season")
    search_fields = ("club__name", "season__name", "season__competition__name")

    def get_competition(self, obj):
        return obj.season.competition.name

    get_competition.short_description = "Competition"

@admin.register(KnockoutRound)
class KnockoutRoundAdmin(admin.ModelAdmin):
    list_display = ("season", "name", "tie_format", "order")

    list_filter = ("season__competition", "season", "name", "tie_format")

    search_fields = ("season__competition__name", "season__name")

    ordering = ("season", "order")


@admin.register(KnockoutTie)
class KnockoutTieAdmin(admin.ModelAdmin):
    list_display = ("knockout_round", "home_club", "away_club", "winner", "is_completed")

    list_filter = ("knockout_round__season__competition", "knockout_round__season", "knockout_round", "is_completed")

    search_fields = ("home_club__name", "away_club__name", "knockout_round__season__competition__name")

    autocomplete_fields = ("home_club", "away_club", "winner")