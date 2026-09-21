import random

import pytest
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError

from competitions.models import Competition, GroupMembership
from competitions.services import (
    assign_team_to_group,
    create_competition,
    create_team,
    delete_team,
    randomize_group_assignments,
)


@pytest.fixture
def competition(db) -> Competition:
    return create_competition(
        name="Draft Cup",
        year=2026,
        group_count=2,
        total_team_count=4,
        qualifiers_per_group=1,
        third_place_enabled=False,
    )


@pytest.mark.django_db
def test_create_team_normalizes_name_and_enforces_configured_total(
    competition: Competition,
):
    names = ["Green", "Blue", "Red", "Yellow"]
    teams = [create_team(competition=competition, name=f"  {name}  ") for name in names]

    assert [team.name for team in teams] == names

    with pytest.raises(ValidationError) as error:
        create_team(competition=competition, name="Purple")

    assert NON_FIELD_ERRORS in error.value.message_dict
    assert competition.teams.count() == competition.total_team_count


@pytest.mark.django_db
def test_create_team_rejects_blank_and_duplicate_names(competition: Competition):
    create_team(competition=competition, name="Green")

    with pytest.raises(ValidationError) as blank_error:
        create_team(competition=competition, name="   ")
    with pytest.raises(ValidationError) as duplicate_error:
        create_team(competition=competition, name="Green")

    assert "name" in blank_error.value.message_dict
    assert "name" in duplicate_error.value.message_dict


@pytest.mark.django_db
def test_team_changes_are_rejected_outside_draft(competition: Competition):
    team = create_team(competition=competition, name="Green")
    competition.status = Competition.Status.GROUP_STAGE
    competition.save(update_fields=["status"])

    with pytest.raises(ValidationError):
        create_team(competition=competition, name="Blue")
    with pytest.raises(ValidationError):
        delete_team(team=team)

    assert competition.teams.filter(id=team.id).exists()


@pytest.mark.django_db
def test_delete_team_removes_its_draft_group_assignment(competition: Competition):
    team = create_team(competition=competition, name="Green")
    group = competition.groups.get(ordinal=1)
    assign_team_to_group(team=team, group=group)

    delete_team(team=team)

    assert not competition.teams.filter(id=team.id).exists()
    assert GroupMembership.objects.count() == 0


@pytest.mark.django_db
def test_manual_assignment_can_move_team_between_groups(competition: Competition):
    team = create_team(competition=competition, name="Green")
    group_a = competition.groups.get(ordinal=1)
    group_b = competition.groups.get(ordinal=2)

    first_membership = assign_team_to_group(team=team, group=group_a)
    moved_membership = assign_team_to_group(team=team, group=group_b)

    assert moved_membership.id == first_membership.id
    assert moved_membership.group == group_b
    assert GroupMembership.objects.filter(team=team).count() == 1


@pytest.mark.django_db
def test_manual_assignment_rejects_full_group(competition: Competition):
    group = competition.groups.get(ordinal=1)
    teams = [
        create_team(competition=competition, name=name)
        for name in ["Green", "Blue", "Red"]
    ]
    assign_team_to_group(team=teams[0], group=group)
    assign_team_to_group(team=teams[1], group=group)

    with pytest.raises(ValidationError) as error:
        assign_team_to_group(team=teams[2], group=group)

    assert "group" in error.value.message_dict


@pytest.mark.django_db
def test_manual_assignment_rejects_group_from_another_competition(
    competition: Competition,
):
    team = create_team(competition=competition, name="Green")
    other_competition = create_competition(
        name="Other Cup",
        year=2027,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )

    with pytest.raises(ValidationError) as error:
        assign_team_to_group(
            team=team,
            group=other_competition.groups.get(ordinal=1),
        )

    assert "group" in error.value.message_dict


@pytest.mark.django_db
def test_randomization_requires_every_configured_team(competition: Competition):
    create_team(competition=competition, name="Green")

    with pytest.raises(ValidationError) as error:
        randomize_group_assignments(competition=competition)

    assert NON_FIELD_ERRORS in error.value.message_dict
    assert GroupMembership.objects.count() == 0


@pytest.mark.django_db
def test_randomization_assigns_every_team_evenly(competition: Competition):
    teams = [
        create_team(competition=competition, name=name)
        for name in ["Green", "Blue", "Red", "Yellow"]
    ]

    memberships = randomize_group_assignments(
        competition=competition,
        rng=random.Random(42),
    )

    assert len(memberships) == competition.total_team_count
    assert {membership.team_id for membership in memberships} == {
        team.id for team in teams
    }
    assert [
        group.memberships.count() for group in competition.groups.order_by("ordinal")
    ] == [competition.teams_per_group, competition.teams_per_group]


@pytest.mark.django_db
def test_randomization_replaces_existing_manual_assignments(
    competition: Competition,
):
    teams = [
        create_team(competition=competition, name=name)
        for name in ["Green", "Blue", "Red", "Yellow"]
    ]
    assign_team_to_group(
        team=teams[0],
        group=competition.groups.get(ordinal=1),
    )

    randomize_group_assignments(
        competition=competition,
        rng=random.Random(7),
    )

    assert GroupMembership.objects.count() == competition.total_team_count
    assert set(
        GroupMembership.objects.values_list("team_id", flat=True)
    ) == {team.id for team in teams}
