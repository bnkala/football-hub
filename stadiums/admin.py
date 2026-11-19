from django.contrib import admin
from .models import Stadium
# Register your models here.

@admin.register(Stadium)
class StadiumAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "city",
        "capacity",
        "opened",
        "club",
    )

    list_filter = ("city", "club")
    search_fields = ("name", "city", "club__name")
