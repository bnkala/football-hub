from django.contrib import admin
from .models import Player
# Register your models here.

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "club",
        "position",
        "shirt_number",
        "nationality",
    )

    list_filter = ("club", "position", "nationality")
    search_fields = ("first_name", "last_name")