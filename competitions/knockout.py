from fixtures.models import Match

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

    if result["matches_played"] != expected_legs:
        return None

    if result["home_aggregate"] > result["away_aggregate"]:
        return knockout_tie.home_club

    if result["away_aggregate"] > result["home_aggregate"]:
        return knockout_tie.away_club

    # Equal scores require extra time, penalties,
    # or another competition-specific tie-breaker.
    return None
