from collections import defaultdict
from dataclasses import dataclass

from django.db.models import Sum

from competitions.models import Group, Match, PlayerMatchStat, TeamMatchStat


@dataclass(frozen=True)
class StandingRow:
    position: int
    team_id: int
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    head_to_head_points: int
    head_to_head_goal_difference: int
    head_to_head_goals_for: int
    draw_lots_priority: int | None
    unresolved_tie: bool
    qualifies: bool


@dataclass(frozen=True)
class TieCohort:
    team_ids: tuple[int, ...]


@dataclass(frozen=True)
class GroupStandings:
    group_id: int
    rows: tuple[StandingRow, ...]
    unresolved_ties: tuple[TieCohort, ...]

    @property
    def is_resolved(self) -> bool:
        return not self.unresolved_ties


@dataclass
class _TeamStats:
    team_id: int
    team_name: str
    draw_lots_priority: int | None
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    head_to_head_points: int = 0
    head_to_head_goals_for: int = 0
    head_to_head_goals_against: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def head_to_head_goal_difference(self) -> int:
        return self.head_to_head_goals_for - self.head_to_head_goals_against

    @property
    def overall_key(self) -> tuple[int, int, int]:
        return self.points, self.goal_difference, self.goals_for

    @property
    def head_to_head_key(self) -> tuple[int, int, int]:
        return (
            self.head_to_head_points,
            self.head_to_head_goal_difference,
            self.head_to_head_goals_for,
        )


def _completed_matches_and_scores(
    group: Group,
) -> tuple[list[Match], dict[tuple[int, int], int]]:
    matches = list(
        Match.objects.filter(group=group, status=Match.Status.COMPLETED)
        .select_related("team_a", "team_b")
        .order_by("round__number", "position")
    )
    match_ids = [match.id for match in matches]
    scores: defaultdict[tuple[int, int], int] = defaultdict(int)

    for row in (
        PlayerMatchStat.objects.filter(match_id__in=match_ids)
        .values("match_id", "roster_membership__team_id")
        .annotate(total=Sum("goals"))
    ):
        scores[(row["match_id"], row["roster_membership__team_id"])] += (
            row["total"] or 0
        )

    for row in TeamMatchStat.objects.filter(match_id__in=match_ids).values(
        "match_id", "team_id", "own_goals_received"
    ):
        scores[(row["match_id"], row["team_id"])] += row["own_goals_received"]

    return matches, dict(scores)


def _record_result(stats: _TeamStats, *, goals_for: int, goals_against: int) -> None:
    stats.played += 1
    stats.goals_for += goals_for
    stats.goals_against += goals_against
    if goals_for > goals_against:
        stats.wins += 1
        stats.points += 3
    elif goals_for < goals_against:
        stats.losses += 1
    else:
        stats.draws += 1
        stats.points += 1


def _record_head_to_head(
    stats: _TeamStats,
    *,
    goals_for: int,
    goals_against: int,
) -> None:
    stats.head_to_head_goals_for += goals_for
    stats.head_to_head_goals_against += goals_against
    if goals_for > goals_against:
        stats.head_to_head_points += 3
    elif goals_for == goals_against:
        stats.head_to_head_points += 1


def calculate_group_standings(
    group: Group,
    *,
    apply_draw_lots: bool = True,
) -> GroupStandings:
    """Calculate a group table solely from completed match source data."""

    memberships = list(
        group.memberships.select_related("team").order_by("team__name", "team_id")
    )
    stats_by_team = {
        membership.team_id: _TeamStats(
            team_id=membership.team_id,
            team_name=membership.team.name,
            draw_lots_priority=membership.draw_lots_priority,
        )
        for membership in memberships
    }
    matches, scores = _completed_matches_and_scores(group)

    for match in matches:
        if match.team_a_id not in stats_by_team or match.team_b_id not in stats_by_team:
            continue
        score_a = scores.get((match.id, match.team_a_id), 0)
        score_b = scores.get((match.id, match.team_b_id), 0)
        _record_result(
            stats_by_team[match.team_a_id],
            goals_for=score_a,
            goals_against=score_b,
        )
        _record_result(
            stats_by_team[match.team_b_id],
            goals_for=score_b,
            goals_against=score_a,
        )

    overall_cohorts: defaultdict[tuple[int, int, int], list[_TeamStats]] = defaultdict(
        list
    )
    for stats in stats_by_team.values():
        overall_cohorts[stats.overall_key].append(stats)

    ordered: list[_TeamStats] = []
    unresolved: list[TieCohort] = []
    for overall_key in sorted(overall_cohorts, reverse=True):
        cohort = overall_cohorts[overall_key]
        cohort_ids = {stats.team_id for stats in cohort}
        if len(cohort) > 1:
            for match in matches:
                if match.team_a_id not in cohort_ids or match.team_b_id not in cohort_ids:
                    continue
                score_a = scores.get((match.id, match.team_a_id), 0)
                score_b = scores.get((match.id, match.team_b_id), 0)
                _record_head_to_head(
                    stats_by_team[match.team_a_id],
                    goals_for=score_a,
                    goals_against=score_b,
                )
                _record_head_to_head(
                    stats_by_team[match.team_b_id],
                    goals_for=score_b,
                    goals_against=score_a,
                )

        head_to_head_cohorts: defaultdict[
            tuple[int, int, int], list[_TeamStats]
        ] = defaultdict(list)
        for stats in cohort:
            head_to_head_cohorts[stats.head_to_head_key].append(stats)

        for head_to_head_key in sorted(head_to_head_cohorts, reverse=True):
            exact_tie = head_to_head_cohorts[head_to_head_key]
            priorities = [stats.draw_lots_priority for stats in exact_tie]
            priorities_resolve_tie = (
                apply_draw_lots
                and len(exact_tie) > 1
                and all(priority is not None for priority in priorities)
                and len(set(priorities)) == len(priorities)
            )
            if priorities_resolve_tie:
                exact_tie.sort(
                    key=lambda stats: stats.draw_lots_priority or 0,
                    reverse=True,
                )
            else:
                exact_tie.sort(key=lambda stats: (stats.team_name.casefold(), stats.team_id))
                if len(exact_tie) > 1:
                    unresolved.append(
                        TieCohort(team_ids=tuple(stats.team_id for stats in exact_tie))
                    )
            ordered.extend(exact_tie)

    unresolved_team_ids = {
        team_id for cohort in unresolved for team_id in cohort.team_ids
    }
    qualifier_count = group.competition.qualifiers_per_group
    rows = tuple(
        StandingRow(
            position=position,
            team_id=stats.team_id,
            team_name=stats.team_name,
            played=stats.played,
            wins=stats.wins,
            draws=stats.draws,
            losses=stats.losses,
            goals_for=stats.goals_for,
            goals_against=stats.goals_against,
            goal_difference=stats.goal_difference,
            points=stats.points,
            head_to_head_points=stats.head_to_head_points,
            head_to_head_goal_difference=stats.head_to_head_goal_difference,
            head_to_head_goals_for=stats.head_to_head_goals_for,
            draw_lots_priority=stats.draw_lots_priority,
            unresolved_tie=stats.team_id in unresolved_team_ids,
            qualifies=position <= qualifier_count,
        )
        for position, stats in enumerate(ordered, start=1)
    )
    return GroupStandings(
        group_id=group.id,
        rows=rows,
        unresolved_ties=tuple(unresolved),
    )
