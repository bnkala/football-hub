from django.db import models

# Create your models here.
class Competition(models.Model):

    class CompetitionType(models.TextChoices):
        LEAGUE = "LEAGUE", "Domestic League"
        DOMESTIC_CUP = "DOMESTIC_CUP", "Domestic Cup"
        CONTINENTAL_CUP = "CONTINENTAL_CUP", "Continental Cup"
        INTERNATIONAL = "INTERNATIONAL", "International"
        OTHER = "OTHER", "Other"

    name = models.CharField(max_length=150)

    country = models.CharField(max_length=100, null=True, blank=True)

    confederation = models.CharField(max_length=20, blank=True)

    competition_type = models.CharField(
        max_length=30,
        choices=CompetitionType.choices,
    )

    founded = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Season(models.Model):
    competition = models.ForeignKey(
        "Competition",
        on_delete=models.CASCADE,
        related_name="seasons",
    )

    name = models.CharField(max_length=20)

    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["competition", "name"],
                name="unique_competition_season",
            )
        ]

    def __str__(self):
        return f"{self.competition.name} - {self.name}"

class CompetitionEntry(models.Model):
    season = models.ForeignKey(
        "Season",
        on_delete=models.CASCADE,
        related_name="entries",
    )

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="competition_entries",
    )

    joined_at = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["club__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["season", "club"],
                name="unique_club_per_competition_season",
            )
        ]
        verbose_name = "Competition Entry"

    def __str__(self):
        return (f"{self.club.name} - {self.season.competition.name} ({self.season.name})")

class KnockoutRound(models.Model):
    class TieFormat(models.TextChoices):
        SINGLE_LEG = "SINGLE_LEG", "Single Leg"
        TWO_LEGGED = "TWO_LEGGED", "Two Legs"

    tie_format = models.CharField(
        max_length=20,
        choices=TieFormat.choices,
        default=TieFormat.SINGLE_LEG,
    )

    class RoundType(models.TextChoices):
        PRELIMINARY = "PRELIMINARY", "Preliminary Round"
        ROUND_OF_64 = "ROUND_OF_64", "Round of 64"
        ROUND_OF_32 = "ROUND_OF_32", "Round of 32"
        ROUND_OF_16 = "ROUND_OF_16", "Round of 16"
        QUATER_FINAL = "QUARTER_FINAL", "Quarter-finals"
        SEMI_FINAL = "SEMI_FINAL", "Semi-finals"
        FINAL = "FINAL", "Final"

    season = models.ForeignKey(
        "Season",
        on_delete=models.CASCADE,
        related_name="knockout_rounds"
    )

    name = models.CharField(
        max_length=30,
        choices=RoundType.choices
    )

    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["season", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["season", "order"],
                name="unique_knockout_round_order"
            ),
            models.UniqueConstraint(
                fields=["season", "name"],
                name="unique_knockout_round_name"
            ),
        ]

    def __str__(self):
        return f"{self.season.competition.name} - {self.season.name} - {self.get_name_display()}"


class KnockoutTie(models.Model):
    knockout_round = models.ForeignKey(
        "KnockoutRound",
        on_delete=models.CASCADE,
        related_name="ties"
    )

    home_club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.PROTECT,
        related_name="home_knockout_ties"
    )

    away_club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.PROTECT,
        related_name="away_knockout_ties"
    )

    winner = models.ForeignKey(
        "clubs.Club",
        on_delete=models.PROTECT,
        related_name="won_knockout_ties",
        null=True,
        blank=True
    )

    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["knockout_round__order", "id"]

    def __str__(self):
        return f"{self.home_club.name} vs {self.away_club.name} - {self.knockout_round}"