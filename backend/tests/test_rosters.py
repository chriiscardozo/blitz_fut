import pytest
from django.core.exceptions import ValidationError

from competitions.models import Competition, Match, Player, RosterMembership, Round
from competitions.services import (
    assign_player_to_team,
    create_competition,
    create_player,
    create_player_and_assign,
    create_team,
    remove_player_from_roster,
    rename_player,
)


@pytest.fixture
def competition(db) -> Competition:
    return create_competition(
        name="Roster Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )


@pytest.fixture
def teams(competition: Competition):
    return (
        create_team(competition=competition, name="Green"),
        create_team(competition=competition, name="Blue"),
    )


@pytest.mark.django_db
def test_create_player_and_assign_normalizes_name(teams):
    membership = create_player_and_assign(name="  Alex  ", team=teams[0])

    assert membership.competition == teams[0].competition
    assert membership.team == teams[0]
    assert membership.player.name == "Alex"


@pytest.mark.django_db
def test_duplicate_player_names_are_allowed(teams):
    first = create_player_and_assign(name="Alex", team=teams[0])
    second = create_player_and_assign(name="Alex", team=teams[1])

    assert first.player_id != second.player_id
    assert Player.objects.filter(name="Alex").count() == 2


@pytest.mark.django_db
def test_assigning_existing_player_moves_membership_within_competition(teams):
    player = create_player(name="Alex")
    first = assign_player_to_team(player=player, team=teams[0])
    moved = assign_player_to_team(player=player, team=teams[1])

    assert moved.id == first.id
    assert moved.team == teams[1]
    assert RosterMembership.objects.filter(player=player).count() == 1


@pytest.mark.django_db
def test_player_can_represent_team_in_another_competition(teams):
    player = create_player(name="Alex")
    first_membership = assign_player_to_team(player=player, team=teams[0])
    other_competition = create_competition(
        name="Next Cup",
        year=2027,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    other_team = create_team(competition=other_competition, name="Red")

    second_membership = assign_player_to_team(player=player, team=other_team)

    assert first_membership.id != second_membership.id
    assert RosterMembership.objects.filter(player=player).count() == 2


@pytest.mark.django_db
def test_remove_roster_membership_keeps_global_player(teams):
    membership = create_player_and_assign(name="Alex", team=teams[0])
    player_id = membership.player_id

    remove_player_from_roster(membership=membership)

    assert not RosterMembership.objects.filter(id=membership.id).exists()
    assert Player.objects.filter(id=player_id).exists()


@pytest.mark.django_db
def test_roster_changes_remain_open_before_first_completed_result(
    competition: Competition,
    teams,
):
    competition.status = Competition.Status.GROUP_STAGE
    competition.save(update_fields=["status"])

    membership = create_player_and_assign(name="Alex", team=teams[0])

    assert membership.team == teams[0]


@pytest.mark.django_db
def test_first_completed_result_locks_all_rosters(
    competition: Competition,
    teams,
):
    membership = create_player_and_assign(name="Alex", team=teams[0])
    competition.status = Competition.Status.GROUP_STAGE
    competition.save(update_fields=["status"])
    round_ = Round.objects.create(
        competition=competition,
        stage=Round.Stage.GROUP,
        number=1,
    )
    Match.objects.create(
        round=round_,
        position=1,
        team_a=teams[0],
        team_b=teams[1],
        status=Match.Status.COMPLETED,
    )

    with pytest.raises(ValidationError):
        create_player_and_assign(name="Blair", team=teams[1])
    with pytest.raises(ValidationError):
        assign_player_to_team(player=membership.player, team=teams[1])
    with pytest.raises(ValidationError):
        remove_player_from_roster(membership=membership)

    assert membership.player.roster_memberships.get(competition=competition).team == teams[0]


@pytest.mark.django_db
def test_player_name_can_be_corrected_after_roster_lock(
    competition: Competition,
    teams,
):
    membership = create_player_and_assign(name="Alxe", team=teams[0])
    competition.status = Competition.Status.COMPLETED
    competition.save(update_fields=["status"])

    player = rename_player(player=membership.player, name="  Alex  ")

    assert player.name == "Alex"


@pytest.mark.django_db
def test_player_name_is_required(teams):
    with pytest.raises(ValidationError) as create_error:
        create_player_and_assign(name="   ", team=teams[0])

    player = create_player(name="Alex")
    with pytest.raises(ValidationError) as rename_error:
        rename_player(player=player, name="")

    assert "name" in create_error.value.message_dict
    assert "name" in rename_error.value.message_dict
