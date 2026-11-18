from django.db import models
from clubs.models import Club
# Create your models here.

class Stadium(models.Model):
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField()

    club = models.OneToOneField(Club, on_delete=models.CASCADE, related_name="stadium")

    opened = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name