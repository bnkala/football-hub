from django.contrib import admin
from .models import Manager
# Register your models here.

@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "club",
        "nationality",
        "appointed_date",
    )

    list_filter = ("club", "nationality")
    search_fields = ("first_name", "last_name", "club__name")