from django.core.exceptions import ValidationError


def _is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def validate_competition_configuration(
    *,
    group_count: int,
    total_team_count: int,
    qualifiers_per_group: int,
    third_place_enabled: bool,
) -> int:
    """Validate initial configuration and return the derived teams per group."""

    errors: dict[str, list[str]] = {}

    def add_error(field: str, message: str) -> None:
        errors.setdefault(field, []).append(message)

    integer_values = {
        "group_count": group_count,
        "total_team_count": total_team_count,
        "qualifiers_per_group": qualifiers_per_group,
    }
    invalid_integer_fields = {
        field
        for field, value in integer_values.items()
        if not isinstance(value, int) or isinstance(value, bool)
    }
    for field in invalid_integer_fields:
        add_error(field, "This value must be an integer.")
    if not isinstance(third_place_enabled, bool):
        add_error("third_place_enabled", "This value must be true or false.")
    if errors:
        raise ValidationError(errors)

    if not _is_power_of_two(group_count):
        add_error("group_count", "The number of groups must be a power of two.")

    if total_team_count < 2:
        add_error("total_team_count", "The competition must contain at least two teams.")

    teams_per_group: int | None = None
    if group_count > 0 and total_team_count > 0:
        if total_team_count % group_count:
            add_error(
                "total_team_count",
                "The total number of teams must divide evenly between the groups.",
            )
        else:
            teams_per_group = total_team_count // group_count
            if teams_per_group < 2:
                add_error(
                    "total_team_count",
                    "Each group must contain at least two teams.",
                )

    if not _is_power_of_two(qualifiers_per_group):
        add_error(
            "qualifiers_per_group",
            "The number of qualifiers per group must be a power of two.",
        )

    if teams_per_group is not None and qualifiers_per_group > teams_per_group:
        add_error(
            "qualifiers_per_group",
            "Qualifiers per group cannot exceed teams per group.",
        )

    knockout_team_count = group_count * qualifiers_per_group
    if knockout_team_count < 2:
        add_error(
            "qualifiers_per_group",
            "At least two teams must qualify for the knockout stage.",
        )

    if third_place_enabled and knockout_team_count < 4:
        add_error(
            "third_place_enabled",
            "A third-place match requires at least four knockout teams.",
        )

    if errors:
        raise ValidationError(errors)

    if teams_per_group is None:
        raise ValidationError(
            {"total_team_count": ["Teams per group could not be calculated."]}
        )

    return teams_per_group
