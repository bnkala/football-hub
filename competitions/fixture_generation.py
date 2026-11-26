from datetime import timedelta, datetime

from django.db import transaction
from django.utils import timezone

from fixtures.models import Match
from competitions.models import KnockoutTie

@transaction.atomic
def generate_knockout_fixtures(tie, first_kickoff, days_between_legs=7):
    """
    Generate scheduled fixtures for a knockout tie.

    SINGLE_LEG: one match.
    TWO_LEGGED: two matches with reversed home/away clubs.
    """

    tie = KnockoutTie.objects.select_for_update().get(pk=tie.pk)

    if Match.objects.filter(knockout_tie=tie).exists():
        raise ValueError("Fixtures already exist for this knockout tie.")

    if tie.is_completed:
        raise ValueError("Cannot generate fixtures for a completed tie.")

    if first_kickoff is None:
        raise ValueError("A kickoff date is required.")

    if not isinstance(first_kickoff, datetime):
        raise ValueError("Kickoff must be a valid datetime.")

    if timezone.is_naive(first_kickoff):
        raise ValueError("Kickoff must include timezone information.")

    if days_between_legs < 1:
        raise ValueError("Days between legs must be at least 1.")

    round_format = tie.knockout_round.tie_format

    if round_format not in ("SINGLE_LEG", "TWO_LEGGED"):
        raise ValueError("Unsupported knockout tie format.")

    fixtures = [
        Match(
            season=tie.knockout_round.season,
            knockout_tie=tie,
            home_club=tie.home_club,
            away_club=tie.away_club,
            kickoff=first_kickoff,
            leg=1,
            status=Match.MatchStatus.SCHEDULED,
        )
    ]

    if round_format == "TWO_LEGGED":
        fixtures.append(
            Match(
                season=tie.knockout_round.season,
                knockout_tie=tie,
                home_club=tie.away_club,
                away_club=tie.home_club,
                kickoff=first_kickoff + timedelta(days=days_between_legs),
                leg=2,
                status=Match.MatchStatus.SCHEDULED,
            )
        )

    return Match.objects.bulk_create(fixtures)