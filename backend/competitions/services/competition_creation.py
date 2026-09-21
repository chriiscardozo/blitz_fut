from django.core.exceptions import ValidationError
from django.db import transaction

from competitions.models import Competition, Group
from competitions.services.competition_configuration import (
    validate_competition_configuration,
)
from competitions.services.common import (
    MAX_POSITIVE_SMALL_INTEGER,
    normalize_required_name,
)


@transaction.atomic
def create_competition(
    *,
    name: str,
    year: int,
    group_count: int,
    total_team_count: int,
    qualifiers_per_group: int,
    third_place_enabled: bool,
) -> Competition:
    """Create a configured draft competition and its empty groups atomically."""

    normalized_name = normalize_required_name(name, label="Competition")
    if not isinstance(year, int) or isinstance(year, bool):
        raise ValidationError({"year": ["Year must be an integer."]})
    if year < 1 or year > MAX_POSITIVE_SMALL_INTEGER:
        raise ValidationError(
            {"year": [f"Year must be between 1 and {MAX_POSITIVE_SMALL_INTEGER}."]}
        )

    teams_per_group = validate_competition_configuration(
        group_count=group_count,
        total_team_count=total_team_count,
        qualifiers_per_group=qualifiers_per_group,
        third_place_enabled=third_place_enabled,
    )

    competition = Competition.objects.create(
        name=normalized_name,
        year=year,
        status=Competition.Status.DRAFT,
        group_count=group_count,
        teams_per_group=teams_per_group,
        qualifiers_per_group=qualifiers_per_group,
        third_place_enabled=third_place_enabled,
    )
    Group.objects.bulk_create(
        Group(competition=competition, ordinal=ordinal)
        for ordinal in range(1, group_count + 1)
    )
    return competition
