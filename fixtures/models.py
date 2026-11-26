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
        on_delete=models.SET_NULL,
        related_name="matches",
        null=True,
        blank=True,
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

    home_penalties = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    away_penalties = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
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

    season = models.ForeignKey(
        "competitions.Season",
        on_delete=models.PROTECT,
        related_name="matches",
        null=True,
        blank=True,
    )

    knockout_tie = models.ForeignKey(
        "competitions.KnockoutTie",
        on_delete=models.SET_NULL,
        related_name="matches",
        null=True,
        blank=True,
    )

    leg = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(1, "First Leg"), (2, "Second Leg")],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["knockout_tie", "leg"],
                condition=models.Q(
                    knockout_tie__isnull=False
                ),
                name="unique_knockout_tie_leg",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(knockout_tie__isnull=True)
                    | (
                        models.Q(leg__isnull=False)
                        & models.Q(leg__in=[1, 2])
                    )
                ),
                name="valid_knockout_fixture_leg",
            ),
        ]

    def __str__(self):
        return f"{self.home_club} vs {self.away_club}"