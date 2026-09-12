from django.contrib import admin

from .models import League
# Register your models here.

@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "code",
        "founded",
    )

    search_fields = (
        "name",
        "country",
        "code",
    )
