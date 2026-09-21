import pytest

from competitions.models import Competition, Match, Round
from competitions.selectors import (
    get_champion,
    get_competition_locks,
    get_knockout_round_name,
    get_player_leaderboards,
    get_third_place_finisher,
)
from competitions.services import (
    PlayerStatLine,
    TeamResult,
    assign_team_to_group,
    complete_or_correct_match,
    create_competition,
    create_player_and_assign,
    create_team,
    generate_group_fixtures,
)


@pytest.mark.django_db
def test_leaderboards_sum_completed_player_stats_and_share_ranks():
    competition = create_competition(
        name="Leaders Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    group = competition.groups.get()
    team_a = create_team(competition=competition, name="Green")
    team_b = create_team(competition=competition, name="Blue")
    assign_team_to_group(team=team_a, group=group)
    assign_team_to_group(team=team_b, group=group)
    alex = create_player_and_assign(name="Alex", team=team_a)
    blair = create_player_and_assign(name="Blair", team=team_a)
    casey = create_player_and_assign(name="Casey", team=team_b)
    generate_group_fixtures(competition=competition)
    match = Match.objects.select_related("team_a", "team_b").get(
        round__competition=competition
    )
    memberships = {row.team_id: row for row in (alex, casey)}
    if match.team_a_id == team_a.id:
        result_a = TeamResult(
            team_id=team_a.id,
            own_goals_received=1,
            player_stats=(
                PlayerStatLine(alex.id, goals=2, assists=1),
                PlayerStatLine(blair.id, assists=1),
            ),
        )
        result_b = TeamResult(
            team_id=team_b.id,
            player_stats=(PlayerStatLine(casey.id, goals=2, assists=2),),
        )
    else:
        result_a = TeamResult(
            team_id=team_b.id,
            player_stats=(PlayerStatLine(casey.id, goals=2, assists=2),),
        )
        result_b = TeamResult(
            team_id=team_a.id,
            own_goals_received=1,
            player_stats=(
                PlayerStatLine(alex.id, goals=2, assists=1),
                PlayerStatLine(blair.id, assists=1),
            ),
        )
    assert memberships
    complete_or_correct_match(
        match=match,
        team_a_result=result_a,
        team_b_result=result_b,
    )

    leaderboards = get_player_leaderboards(competition)

    assert [(row.player_name, row.total, row.rank) for row in leaderboards.scorers] == [
        ("Alex", 2, 1),
        ("Casey", 2, 1),
    ]
    assert [
        (row.player_name, row.total, row.rank) for row in leaderboards.assisters
    ] == [
        ("Casey", 2, 1),
        ("Alex", 1, 2),
        ("Blair", 1, 2),
    ]


@pytest.mark.django_db
def test_champion_and_third_place_are_derived_from_completed_matches():
    competition = create_competition(
        name="Finals Cup",
        year=2026,
        group_count=1,
        total_team_count=4,
        qualifiers_per_group=4,
        third_place_enabled=True,
    )
    teams = [
        create_team(competition=competition, name=name)
        for name in ("A", "B", "C", "D")
    ]
    competition.status = Competition.Status.KNOCKOUT
    competition.save(update_fields=["status"])
    final_round = Round.objects.create(
        competition=competition,
        stage=Round.Stage.KNOCKOUT,
        number=2,
    )
    final = Match.objects.create(
        round=final_round,
        position=1,
        kind=Match.Kind.FINAL,
        team_a=teams[0],
        team_b=teams[1],
    )
    third_place = Match.objects.create(
        round=final_round,
        position=2,
        kind=Match.Kind.THIRD_PLACE,
        team_a=teams[2],
        team_b=teams[3],
    )
    complete_or_correct_match(
        match=final,
        team_a_result=TeamResult(team_id=teams[0].id, own_goals_received=1),
        team_b_result=TeamResult(team_id=teams[1].id),
    )
    assert get_champion(competition) == teams[0]
    assert get_third_place_finisher(competition) is None

    complete_or_correct_match(
        match=third_place,
        team_a_result=TeamResult(team_id=teams[2].id),
        team_b_result=TeamResult(team_id=teams[3].id),
        shootout_winner_id=teams[3].id,
    )
    assert get_third_place_finisher(competition) == teams[3]


@pytest.mark.django_db
def test_knockout_round_names_are_derived_from_round_count():
    competition = Competition.objects.create(
        name="Names Cup",
        year=2026,
        status=Competition.Status.KNOCKOUT,
        group_count=2,
        teams_per_group=8,
        qualifiers_per_group=8,
    )
    rounds = [
        Round.objects.create(
            competition=competition,
            stage=Round.Stage.KNOCKOUT,
            number=number,
        )
        for number in range(1, 5)
    ]

    assert [get_knockout_round_name(round_) for round_ in rounds] == [
        "Round of 16",
        "Quarterfinals",
        "Semifinals",
        "Final",
    ]


@pytest.mark.django_db
def test_competition_lock_state_changes_with_lifecycle():
    competition = create_competition(
        name="Locks Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    draft_locks = get_competition_locks(competition)
    assert not draft_locks.structure_locked
    assert not draft_locks.roster_locked

    group = competition.groups.get()
    teams = [
        create_team(competition=competition, name=name) for name in ("A", "B")
    ]
    for team in teams:
        assign_team_to_group(team=team, group=group)
    generate_group_fixtures(competition=competition)
    group_locks = get_competition_locks(competition)
    assert group_locks.structure_locked
    assert group_locks.can_return_to_setup

    match = Match.objects.get(round__competition=competition)
    complete_or_correct_match(
        match=match,
        team_a_result=TeamResult(team_id=match.team_a_id),
        team_b_result=TeamResult(team_id=match.team_b_id),
    )
    completed_group_locks = get_competition_locks(competition)
    assert completed_group_locks.roster_locked
    assert not completed_group_locks.can_finalize_group_stage
    assert not completed_group_locks.can_return_to_setup

    group.memberships.filter(team=match.team_a).update(draw_lots_priority=2)
    group.memberships.filter(team=match.team_b).update(draw_lots_priority=1)
    assert get_competition_locks(competition).can_finalize_group_stage
