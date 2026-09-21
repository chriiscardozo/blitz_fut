from itertools import combinations

import pytest
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

from competitions.models import Competition, Match, Round
from competitions.services import (
    assign_team_to_group,
    build_round_robin,
    create_competition,
    create_team,
    generate_group_fixtures,
    return_to_setup,
)


@pytest.mark.parametrize("team_count", [2, 3, 4, 5, 6])
def test_round_robin_contains_every_pair_once(team_count: int):
    team_ids = list(range(1, team_count + 1))

    rounds = build_round_robin(team_ids)
    actual_pairs = {
        frozenset(pair)
        for round_pairings in rounds
        for pair in round_pairings
    }
    expected_pairs = {frozenset(pair) for pair in combinations(team_ids, 2)}
    expected_round_count = team_count - 1 if team_count % 2 == 0 else team_count

    assert len(rounds) == expected_round_count
    assert actual_pairs == expected_pairs
    assert sum(len(round_pairings) for round_pairings in rounds) == (
        team_count * (team_count - 1) // 2
    )


@pytest.mark.parametrize("team_count", [2, 3, 4, 5, 6])
def test_team_appears_at_most_once_per_round(team_count: int):
    for pairings in build_round_robin(list(range(1, team_count + 1))):
        playing_team_ids = [team_id for pairing in pairings for team_id in pairing]
        assert len(playing_team_ids) == len(set(playing_team_ids))


def test_round_robin_rejects_invalid_team_lists():
    with pytest.raises(ValueError):
        build_round_robin([1])
    with pytest.raises(ValueError):
        build_round_robin([1, 1])


def configured_competition(*, team_count: int = 8) -> Competition:
    competition = create_competition(
        name="Fixture Cup",
        year=2026,
        group_count=2,
        total_team_count=team_count,
        qualifiers_per_group=2,
        third_place_enabled=True,
    )
    groups = list(competition.groups.order_by("ordinal"))
    for index in range(team_count):
        team = create_team(competition=competition, name=f"Team {index + 1}")
        assign_team_to_group(team=team, group=groups[index % len(groups)])
    return competition


@pytest.mark.django_db
def test_generate_group_fixtures_creates_shared_rounds_and_matches():
    competition = configured_competition()

    rounds = generate_group_fixtures(competition=competition)

    competition.refresh_from_db()
    assert competition.status == Competition.Status.GROUP_STAGE
    assert len(rounds) == competition.teams_per_group - 1
    assert Match.objects.filter(round__competition=competition).count() == 12
    assert all(
        round_.matches.count() == 4
        for round_ in competition.rounds.order_by("number")
    )

    for group in competition.groups.all():
        group_team_ids = set(group.memberships.values_list("team_id", flat=True))
        group_matches = Match.objects.filter(group=group)
        actual_pairs = {
            frozenset((match.team_a_id, match.team_b_id)) for match in group_matches
        }
        assert actual_pairs == {
            frozenset(pair) for pair in combinations(group_team_ids, 2)
        }


@pytest.mark.django_db
def test_generate_group_fixtures_supports_odd_group_size():
    competition = create_competition(
        name="Odd Cup",
        year=2026,
        group_count=1,
        total_team_count=5,
        qualifiers_per_group=4,
        third_place_enabled=True,
    )
    group = competition.groups.get()
    for index in range(5):
        team = create_team(competition=competition, name=f"Team {index + 1}")
        assign_team_to_group(team=team, group=group)

    generate_group_fixtures(competition=competition)

    assert competition.rounds.count() == 5
    assert Match.objects.filter(round__competition=competition).count() == 10
    assert all(round_.matches.count() == 2 for round_ in competition.rounds.all())


@pytest.mark.django_db
def test_generation_rejects_incomplete_group_assignments():
    competition = create_competition(
        name="Incomplete Cup",
        year=2026,
        group_count=2,
        total_team_count=4,
        qualifiers_per_group=2,
        third_place_enabled=True,
    )
    teams = [
        create_team(competition=competition, name=f"Team {index + 1}")
        for index in range(4)
    ]
    group = competition.groups.get(ordinal=1)
    assign_team_to_group(team=teams[0], group=group)
    assign_team_to_group(team=teams[1], group=group)

    with pytest.raises(ValidationError) as error:
        generate_group_fixtures(competition=competition)

    competition.refresh_from_db()
    assert NON_FIELD_ERRORS in error.value.message_dict
    assert competition.status == Competition.Status.DRAFT
    assert competition.rounds.count() == 0


@pytest.mark.django_db
def test_return_to_setup_deletes_pending_fixtures():
    competition = configured_competition()
    generate_group_fixtures(competition=competition)

    return_to_setup(competition=competition)

    competition.refresh_from_db()
    assert competition.status == Competition.Status.DRAFT
    assert competition.rounds.count() == 0
    assert Match.objects.filter(round__competition=competition).count() == 0
    assert competition.teams.count() == competition.total_team_count


@pytest.mark.django_db
def test_return_to_setup_is_blocked_after_completed_result():
    competition = configured_competition()
    generate_group_fixtures(competition=competition)
    match = Match.objects.filter(round__competition=competition).first()
    assert match is not None
    match.status = Match.Status.COMPLETED
    match.save(update_fields=["status"])

    with pytest.raises(ValidationError):
        return_to_setup(competition=competition)

    competition.refresh_from_db()
    assert competition.status == Competition.Status.GROUP_STAGE
    assert competition.rounds.filter(stage=Round.Stage.GROUP).exists()
