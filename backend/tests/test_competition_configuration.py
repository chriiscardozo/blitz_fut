import pytest
from django.core.exceptions import ValidationError

from competitions.services import validate_competition_configuration


@pytest.mark.parametrize(
    (
        "group_count",
        "total_team_count",
        "qualifiers_per_group",
        "third_place_enabled",
    ),
    [
        (1, 4, 2, False),
        (1, 5, 4, True),
        (2, 8, 1, False),
        (2, 8, 2, True),
        (2, 8, 4, True),
        (4, 12, 2, True),
    ],
)
def test_accepts_valid_competition_configurations(
    group_count: int,
    total_team_count: int,
    qualifiers_per_group: int,
    third_place_enabled: bool,
):
    derived_teams_per_group = validate_competition_configuration(
        group_count=group_count,
        total_team_count=total_team_count,
        qualifiers_per_group=qualifiers_per_group,
        third_place_enabled=third_place_enabled,
    )

    assert derived_teams_per_group == total_team_count // group_count


@pytest.mark.parametrize("group_count", [0, 3, 6])
def test_rejects_group_count_that_is_not_a_power_of_two(group_count: int):
    with pytest.raises(ValidationError) as error:
        validate_competition_configuration(
            group_count=group_count,
            total_team_count=8,
            qualifiers_per_group=2,
            third_place_enabled=False,
        )

    assert "group_count" in error.value.message_dict


def test_rejects_group_with_fewer_than_two_teams():
    with pytest.raises(ValidationError) as error:
        validate_competition_configuration(
            group_count=2,
            total_team_count=2,
            qualifiers_per_group=1,
            third_place_enabled=False,
        )

    assert "total_team_count" in error.value.message_dict


def test_rejects_team_count_that_cannot_be_divided_evenly():
    with pytest.raises(ValidationError) as error:
        validate_competition_configuration(
            group_count=4,
            total_team_count=10,
            qualifiers_per_group=2,
            third_place_enabled=False,
        )

    assert "total_team_count" in error.value.message_dict


@pytest.mark.parametrize("qualifiers_per_group", [0, 3, 6])
def test_rejects_qualifier_count_that_is_not_a_power_of_two(
    qualifiers_per_group: int,
):
    with pytest.raises(ValidationError) as error:
        validate_competition_configuration(
            group_count=2,
            total_team_count=12,
            qualifiers_per_group=qualifiers_per_group,
            third_place_enabled=False,
        )

    assert "qualifiers_per_group" in error.value.message_dict


def test_rejects_more_qualifiers_than_teams():
    with pytest.raises(ValidationError) as error:
        validate_competition_configuration(
            group_count=1,
            total_team_count=3,
            qualifiers_per_group=4,
            third_place_enabled=False,
        )

    assert "qualifiers_per_group" in error.value.message_dict


def test_rejects_knockout_stage_with_only_one_team():
    with pytest.raises(ValidationError) as error:
        validate_competition_configuration(
            group_count=1,
            total_team_count=4,
            qualifiers_per_group=1,
            third_place_enabled=False,
        )

    assert "qualifiers_per_group" in error.value.message_dict


def test_rejects_third_place_match_without_semifinals():
    with pytest.raises(ValidationError) as error:
        validate_competition_configuration(
            group_count=1,
            total_team_count=4,
            qualifiers_per_group=2,
            third_place_enabled=True,
        )

    assert "third_place_enabled" in error.value.message_dict
