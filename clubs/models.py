from django.db import models

from leagues.models import League

# Create your models here.

class Club(models.Model):
    name = models.CharField(max_length=120)
    short_name = models.CharField(max_length=50)

    league = models.ForeignKey(
        League,
        on_delete=models.CASCADE,
        related_name="clubs",
    )

    city = models.CharField(max_length=100)
    founded = models.PositiveIntegerField(null=True, blank=True)
    stadium_name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name