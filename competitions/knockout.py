from fixtures.models import Match
from django.db import transaction
from competitions.models import KnockoutRound, KnockoutTie
from competitions.fixture_generation import generate_knockout_fixtures

def calculate_aggregate(knockout_tie):
    matches = Match.objects.filter(
        knockout_tie=knockout_tie,
        status="FINISHED",
        home_score__isnull=False,
        away_score__isnull=False,
    )

    club_a = knockout_tie.home_club
    club_b = knockout_tie.away_club

    aggregate = {
        club_a.id: 0,
        club_b.id: 0,
    }

    for match in matches:
        if {match.home_club_id, match.away_club_id} != {club_a.id, club_b.id}:
            raise ValueError("Fixture clubs do not match the knockout tie.")

        aggregate[match.home_club_id] += match.home_score
        aggregate[match.away_club_id] += match.away_score

    return {
        "home_club": club_a.name,
        "away_club": club_b.name,
        "home_aggregate": aggregate[club_a.id],
        "away_aggregate": aggregate[club_b.id],
        "matches_played": matches.count(),
    }



def determine_winner(knockout_tie):
    result = calculate_aggregate(knockout_tie)

    tie_format = knockout_tie.knockout_round.tie_format

    if tie_format == "SINGLE_LEG":
        expected_legs = 1
    elif tie_format == "TWO_LEGGED":
        expected_legs = 2
    else:
        raise ValueError("Unsupported knockout tie format.")

    matches = list(
        Match.objects.filter(
            knockout_tie=knockout_tie
        ).order_by("leg", "id")
    )

    # Only determine a winner when the expected
    # number of fixtures has been completed.
    if len(matches) != expected_legs:
        return None

    if any(
        match.status != "FINISHED"
        or match.home_score is None
        or match.away_score is None
        for match in matches
    ):
        return None

    if expected_legs == 2:
        if {match.leg for match in matches} != {1, 2}:
            return None

    if result["home_aggregate"] > result["away_aggregate"]:
        return knockout_tie.home_club

    if result["away_aggregate"] > result["home_aggregate"]:
        return knockout_tie.away_club

    # Aggregate scores are equal.
    # Check penalties in the deciding fixture.
    deciding_match = matches[-1]

    home_penalties = deciding_match.home_penalties
    away_penalties = deciding_match.away_penalties

    if home_penalties is None or away_penalties is None:
        return None

    if home_penalties == away_penalties:
        return None

    if home_penalties > away_penalties:
        return deciding_match.home_club

    return deciding_match.away_club

@transaction.atomic
def complete_knockout_tie(knockout_tie):
    """
    Complete a knockout tie once a winner can be determined.
    Save the winner and completion status.
    """

    tie = type(knockout_tie).objects.select_for_update().get(
        pk=knockout_tie.pk
    )

    winner = determine_winner(tie)

    if winner is None:
        return None

    if tie.is_completed:
        if tie.winner_id != winner.id:
            raise ValueError(
                "Completed tie has a different recorded winner."
            )
        return winner

    tie.winner = winner
    tie.is_completed = True

    tie.save(update_fields=["winner", "is_completed"])

    return winner


@transaction.atomic
def progress_knockout_round(knockout_round, first_kickoff=None, days_between_legs=7):
    """
    Advance winners from a completed knockout round
    into the next round of the same season.

    Clubs are paired in the order of their existing ties.

    If first_kickoff is supplied, automatically generate
    fixtures for each newly created knockout tie.

    Round progression and fixture generation are performed
    within the same database transaction.
    """

    current_round = KnockoutRound.objects.select_for_update().get(
        pk=knockout_round.pk
    )

    ties = list(
        KnockoutTie.objects.filter(
            knockout_round=current_round
        )
        .select_related("winner", "home_club", "away_club")
        .order_by("id")
    )

    if not ties:
        raise ValueError(
            "Cannot progress a round without knockout ties."
        )

    for tie in ties:
        if not tie.is_completed or tie.winner_id is None:
            raise ValueError(
                "All knockout ties must be completed before progression."
            )

        if tie.winner_id not in (
            tie.home_club_id,
            tie.away_club_id,
        ):
            raise ValueError(
                "A knockout tie has an invalid winner."
            )

    winners = [tie.winner for tie in ties]

    if len({club.id for club in winners}) != len(winners):
        raise ValueError(
            "A club cannot qualify more than once from the same round."
        )

    if len(winners) % 2 != 0:
        raise ValueError(
            "An even number of winners is required."
        )

    next_round = (
        KnockoutRound.objects.filter(
            season=current_round.season,
            order__gt=current_round.order,
        )
        .order_by("order")
        .first()
    )

    if next_round is None:
        raise ValueError(
            "No next knockout round exists for this season."
        )

    existing_ties = KnockoutTie.objects.filter(
        knockout_round=next_round
    )

    if existing_ties.exists():
        raise ValueError(
            "The next round already contains knockout ties."
        )

    new_ties = []

    for index in range(0, len(winners), 2):
        new_ties.append(
            KnockoutTie(
                knockout_round=next_round,
                home_club=winners[index],
                away_club=winners[index + 1],
            )
        )

    KnockoutTie.objects.bulk_create(new_ties)

    created_ties = list(
        KnockoutTie.objects.filter(
            knockout_round=next_round
        ).order_by("id")
    )

    if first_kickoff is not None:
        for tie in created_ties:
            generate_knockout_fixtures(
                tie=tie,
                first_kickoff=first_kickoff,
                days_between_legs=days_between_legs,
            )

    return created_ties