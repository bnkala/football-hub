from fixtures.models import Match
from django.db import transaction

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