from competitions.models import CompetitionEntry
from fixtures.models import Match

def calculate_standings(season):
    entries = (CompetitionEntry.objects.filter(season=season).select_related("club"))

    standings = {}

    for entry in entries:
        club = entry.club

        standings[club.id] = {
            "club_id": club.id,
            "club_name": club.name,
            "played": 0,
            "won": 0,
            "drawn": 0,
            "lost": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 0,
        }

    matches = Match.objects.filter(
        season=season,
        status="FINISHED",
        home_score__isnull=False,
        away_score__isnull=False,
    )

    for match in matches:
        home = standings.get(match.home_club_id)
        away = standings.get(match.away_club_id)

        if home is None or away is None:
            continue

        home["played"] += 1
        away["played"] += 1

        home["goals_for"] += match.home_score
        home["goals_against"] += match.away_score

        away["goals_for"] += match.away_score
        away["goals_against"] += match.home_score

        if match.home_score > match.away_score:
            home["won"] += 1
            away["lost"] += 1
            home["points"] += 3

        elif match.home_score < match.away_score:
            away["won"] += 1
            home["lost"] += 1
            away["points"] += 3

        else:
            home["drawn"] += 1
            away["drawn"] += 1
            home["points"] += 1
            away["points"] += 1

    for club in standings.values():
        club["goal_difference"] = (
            club["goals_for"] - club["goals_against"]
        )

    table = sorted(
        standings.values(),
        key=lambda club: (
            -club["points"],
            -club["goal_difference"],
            -club["goals_for"],
            club["club_name"],
        ),
    )

    for position, club in enumerate(table, start=1):
        club["position"] = position

    return table