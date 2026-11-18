from django.db import models
from clubs.models import Club
# Create your models here.

class Manager(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nationality = models.CharField(max_length=100)
    date_of_birth = models.CharField(null=True, blank=True)

    club = models.OneToOneField(Club, on_delete=models.CASCADE, related_name="manager")

    appointed_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
