import pytest
from django.core.exceptions import ValidationError

from competitions.models import Competition
from competitions.services import create_competition


@pytest.mark.django_db
def test_initial_configuration_creates_draft_and_groups():
    competition = create_competition(
        name="Blitz Fut 2026",
        year=2026,
        group_count=2,
        total_team_count=8,
        qualifiers_per_group=2,
        third_place_enabled=True,
    )

    assert competition.status == Competition.Status.DRAFT
    assert competition.teams_per_group == 4
    assert competition.total_team_count == 8
    assert list(competition.groups.values_list("ordinal", flat=True)) == [1, 2]
    assert competition.teams.count() == 0


@pytest.mark.django_db
def test_invalid_initial_configuration_persists_nothing():
    with pytest.raises(ValidationError):
        create_competition(
            name="Invalid Cup",
            year=2026,
            group_count=4,
            total_team_count=10,
            qualifiers_per_group=2,
            third_place_enabled=False,
        )

    assert Competition.objects.count() == 0
