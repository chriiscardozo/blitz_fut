from collections.abc import Mapping

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import transaction

from competitions.models import Competition, Group, Match
from competitions.selectors.group_standings import calculate_group_standings


@transaction.atomic
def save_draw_lots_priorities(
    *,
    group: Group,
    priorities: Mapping[int, int],
    confirmed: bool,
) -> None:
    if group.competition.status != Competition.Status.GROUP_STAGE:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["Drawing of lots is available only during the group stage."]}
        )
    if group.matches.exclude(status=Match.Status.COMPLETED).exists():
        raise ValidationError(
            {NON_FIELD_ERRORS: ["Complete every match in the group before drawing lots."]}
        )
    if not confirmed:
        raise ValidationError(
            {"confirmed": ["Confirm that the entered order reflects the drawing of lots."]}
        )
    if not priorities:
        raise ValidationError({"priorities": ["A tied cohort is required."]})
    if any(
        not isinstance(priority, int)
        or isinstance(priority, bool)
        or priority < 1
        for priority in priorities.values()
    ):
        raise ValidationError(
            {"priorities": ["Every drawing-of-lots priority must be a positive integer."]}
        )
    if len(set(priorities.values())) != len(priorities):
        raise ValidationError(
            {"priorities": ["Priorities must be unique within the tied cohort."]}
        )

    standings = calculate_group_standings(group, apply_draw_lots=False)
    submitted_ids = set(priorities)
    matching_cohort = next(
        (
            cohort
            for cohort in standings.unresolved_ties
            if set(cohort.team_ids) == submitted_ids
        ),
        None,
    )
    if matching_cohort is None:
        raise ValidationError(
            {
                "priorities": [
                    "Submit every team from exactly one currently tied cohort."
                ]
            }
        )

    memberships = group.memberships.filter(team_id__in=submitted_ids)
    if memberships.count() != len(submitted_ids):
        raise ValidationError({"priorities": ["One or more teams are not in this group."]})
    for membership in memberships:
        membership.draw_lots_priority = priorities[membership.team_id]
    group.memberships.model.objects.bulk_update(
        memberships,
        ["draw_lots_priority"],
    )
