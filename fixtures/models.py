from django.db import models

# Create your models here.
class Match(models.Model):

    class MatchStatus(models.TextChoices):
        SCHEDULED= "SCHEDULED", "Scheduled"
        LIVE = "LIVE", "Live"
        FINISHED = "FINISHED", "Finished"
        POSTPONED = "POSTPONED", "Postponed"
        CANCELLED = "CANCELLED", "Cancelled"

    league = models.ForeignKey(
        "leagues.League",
        on_delete=models.CASCADE,
        related_name="matches",
    )

    home_club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="home_matches",
    )

    away_club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="away_matches",
    )

    kickoff = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=MatchStatus.choices,
        default=MatchStatus.SCHEDULED,
    )

    home_score = models.PositiveIntegerField(null=True, blank=True)

    away_score = models.PositiveIntegerField(null=True, blank=True)

    matchweek = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.home_club} vs {self.away_club}"