from dataclasses import dataclass

from django.db.models import Sum

from competitions.models import Competition, Match, PlayerMatchStat


@dataclass(frozen=True)
class LeaderboardRow:
    rank: int
    player_id: int
    player_name: str
    team_id: int
    team_name: str
    total: int


@dataclass(frozen=True)
class PlayerLeaderboards:
    scorers: tuple[LeaderboardRow, ...]
    assisters: tuple[LeaderboardRow, ...]


def _leaderboard(
    competition: Competition,
    *,
    field_name: str,
) -> tuple[LeaderboardRow, ...]:
    values = list(
        PlayerMatchStat.objects.filter(
            match__round__competition=competition,
            match__status=Match.Status.COMPLETED,
        )
        .values(
            "roster_membership__player_id",
            "roster_membership__player__name",
            "roster_membership__team_id",
            "roster_membership__team__name",
        )
        .annotate(total=Sum(field_name))
        .filter(total__gt=0)
        .order_by(
            "-total",
            "roster_membership__player__name",
            "roster_membership__player_id",
        )
    )

    rows: list[LeaderboardRow] = []
    previous_total: int | None = None
    current_rank = 0
    for index, value in enumerate(values, start=1):
        total = value["total"] or 0
        if total != previous_total:
            current_rank = index
            previous_total = total
        rows.append(
            LeaderboardRow(
                rank=current_rank,
                player_id=value["roster_membership__player_id"],
                player_name=value["roster_membership__player__name"],
                team_id=value["roster_membership__team_id"],
                team_name=value["roster_membership__team__name"],
                total=total,
            )
        )
    return tuple(rows)


def get_player_leaderboards(competition: Competition) -> PlayerLeaderboards:
    return PlayerLeaderboards(
        scorers=_leaderboard(competition, field_name="goals"),
        assisters=_leaderboard(competition, field_name="assists"),
    )
