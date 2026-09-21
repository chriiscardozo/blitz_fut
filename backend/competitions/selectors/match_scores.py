from dataclasses import dataclass

from django.db.models import Sum

from competitions.models import Match, PlayerMatchStat, TeamMatchStat


@dataclass(frozen=True)
class MatchScore:
    team_a: int
    team_b: int


def get_match_score(match: Match) -> MatchScore:
    player_goals = {
        row["roster_membership__team_id"]: row["total"] or 0
        for row in PlayerMatchStat.objects.filter(match=match)
        .values("roster_membership__team_id")
        .annotate(total=Sum("goals"))
    }
    own_goals = {
        row["team_id"]: row["own_goals_received"]
        for row in TeamMatchStat.objects.filter(match=match).values(
            "team_id", "own_goals_received"
        )
    }
    return MatchScore(
        team_a=player_goals.get(match.team_a_id, 0)
        + own_goals.get(match.team_a_id, 0),
        team_b=player_goals.get(match.team_b_id, 0)
        + own_goals.get(match.team_b_id, 0),
    )
