from collections.abc import Mapping

import pytest
from django.core.exceptions import ValidationError

from competitions.models import Match, Team
from competitions.selectors import calculate_group_standings
from competitions.services import (
    TeamResult,
    assign_team_to_group,
    complete_or_correct_match,
    create_competition,
    create_team,
    generate_group_fixtures,
    save_draw_lots_priorities,
)


def create_group_stage(*, team_names: tuple[str, ...], qualifiers: int = 2):
    competition = create_competition(
        name="Standings Cup",
        year=2026,
        group_count=1,
        total_team_count=len(team_names),
        qualifiers_per_group=qualifiers,
        third_place_enabled=False,
    )
    group = competition.groups.get()
    teams = {
        name: create_team(competition=competition, name=name) for name in team_names
    }
    for team in teams.values():
        assign_team_to_group(team=team, group=group)
    generate_group_fixtures(competition=competition)
    return competition, group, teams


def complete_scores(
    *,
    teams: Mapping[str, Team],
    scores: Mapping[frozenset[str], Mapping[str, int]],
) -> None:
    matches = Match.objects.filter(
        round__competition=next(iter(teams.values())).competition
    ).select_related("team_a", "team_b")
    for match in matches:
        key = frozenset((match.team_a.name, match.team_b.name))
        if key not in scores:
            continue
        score_by_name = scores[key]
        complete_or_correct_match(
            match=match,
            team_a_result=TeamResult(
                team_id=match.team_a_id,
                own_goals_received=score_by_name[match.team_a.name],
            ),
            team_b_result=TeamResult(
                team_id=match.team_b_id,
                own_goals_received=score_by_name[match.team_b.name],
            ),
        )


def score(team_a: str, goals_a: int, team_b: str, goals_b: int):
    return frozenset((team_a, team_b)), {team_a: goals_a, team_b: goals_b}


@pytest.mark.django_db
def test_standings_use_only_completed_matches_and_derive_table_totals():
    _, group, teams = create_group_stage(team_names=("A", "B", "C", "D"))
    complete_scores(
        teams=teams,
        scores=dict(
            [
                score("A", 2, "B", 0),
                score("A", 1, "C", 1),
            ]
        ),
    )

    standings = calculate_group_standings(group)
    row_a = next(row for row in standings.rows if row.team_name == "A")
    row_b = next(row for row in standings.rows if row.team_name == "B")

    assert (
        row_a.played,
        row_a.wins,
        row_a.draws,
        row_a.losses,
        row_a.goals_for,
        row_a.goals_against,
        row_a.goal_difference,
        row_a.points,
    ) == (2, 1, 1, 0, 3, 1, 2, 4)
    assert row_b.played == 1
    assert row_b.points == 0


@pytest.mark.django_db
def test_head_to_head_breaks_an_exact_overall_tie():
    _, group, teams = create_group_stage(team_names=("A", "B", "C", "D"))
    complete_scores(
        teams=teams,
        scores=dict(
            [
                score("A", 1, "B", 0),
                score("A", 0, "C", 1),
                score("A", 1, "D", 0),
                score("B", 1, "C", 0),
                score("B", 1, "D", 0),
                score("C", 0, "D", 0),
            ]
        ),
    )

    standings = calculate_group_standings(group)
    rows = {row.team_name: row for row in standings.rows}

    assert rows["A"].points == rows["B"].points == 6
    assert rows["A"].goal_difference == rows["B"].goal_difference == 1
    assert rows["A"].goals_for == rows["B"].goals_for == 2
    assert rows["A"].head_to_head_points == 3
    assert rows["B"].head_to_head_points == 0
    assert rows["A"].position < rows["B"].position
    assert standings.is_resolved


@pytest.mark.django_db
def test_exact_tie_is_flagged_and_draw_lots_priority_resolves_it():
    _, group, teams = create_group_stage(team_names=("A", "B", "C", "D"))
    complete_scores(
        teams=teams,
        scores=dict(
            [
                score("A", 0, "B", 0),
                score("A", 1, "C", 0),
                score("A", 0, "D", 1),
                score("B", 1, "C", 0),
                score("B", 0, "D", 1),
                score("C", 0, "D", 0),
            ]
        ),
    )

    unresolved = calculate_group_standings(group)
    assert [set(cohort.team_ids) for cohort in unresolved.unresolved_ties] == [
        {teams["A"].id, teams["B"].id}
    ]

    save_draw_lots_priorities(
        group=group,
        priorities={teams["A"].id: 1, teams["B"].id: 2},
        confirmed=True,
    )

    resolved = calculate_group_standings(group)
    assert resolved.is_resolved
    assert resolved.rows[1].team_name == "B"
    assert resolved.rows[2].team_name == "A"
    assert resolved.rows[1].qualifies
    assert not resolved.rows[2].qualifies


@pytest.mark.django_db
def test_draw_lots_requires_all_matches_and_exact_confirmed_cohort():
    _, group, teams = create_group_stage(team_names=("A", "B", "C", "D"))

    with pytest.raises(ValidationError):
        save_draw_lots_priorities(
            group=group,
            priorities={team.id: index for index, team in enumerate(teams.values(), 1)},
            confirmed=True,
        )

    complete_scores(
        teams=teams,
        scores=dict(
            score(team_a, 0, team_b, 0)
            for index, team_a in enumerate(teams)
            for team_b in tuple(teams)[index + 1 :]
        ),
    )

    with pytest.raises(ValidationError) as error:
        save_draw_lots_priorities(
            group=group,
            priorities={teams["A"].id: 1, teams["B"].id: 2},
            confirmed=True,
        )
    assert "priorities" in error.value.message_dict

    with pytest.raises(ValidationError) as error:
        save_draw_lots_priorities(
            group=group,
            priorities={team.id: index for index, team in enumerate(teams.values(), 1)},
            confirmed=False,
        )
    assert "confirmed" in error.value.message_dict


@pytest.mark.django_db
def test_draw_lots_priorities_must_be_unique_and_positive():
    _, group, teams = create_group_stage(team_names=("A", "B"), qualifiers=2)
    complete_scores(teams=teams, scores=dict([score("A", 0, "B", 0)]))

    with pytest.raises(ValidationError):
        save_draw_lots_priorities(
            group=group,
            priorities={teams["A"].id: 1, teams["B"].id: 1},
            confirmed=True,
        )
    with pytest.raises(ValidationError):
        save_draw_lots_priorities(
            group=group,
            priorities={teams["A"].id: 0, teams["B"].id: 1},
            confirmed=True,
        )
