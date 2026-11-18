from django.db import models
from clubs.models import Club
# Create your models here.

class Player(models.Model):
    class Position(models.TextChoices):
        GOALKEEPER = "GK", "Goalkeeper"
        DEFENDER = "DEF", "Defender"
        MIDFIELDER = "MID", "Midfielder"
        FORWARD = "FWD", "Forward"

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    nationality = models.CharField(max_length=50)

    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name="players",
    )

    position = models.CharField(
        max_length=3,
        choices=Position.choices,
    )

    shirt_number = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"