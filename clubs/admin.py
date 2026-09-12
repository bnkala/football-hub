from django.contrib import admin

from .models import Club
# Register your models here.

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "short_name",
        "league",
        "city",
        "stadium_name",
    )

    search_fields = (
        "name",
        "short_name",
        "city",
    )

    list_filter = (
        "league",
    )

    
