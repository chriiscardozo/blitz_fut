import random

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import transaction

from competitions.models import Competition, Group, GroupMembership, Team
from competitions.services.common import normalize_required_name


def _require_draft(competition: Competition) -> None:
    if competition.status != Competition.Status.DRAFT:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["This operation is available only during draft setup."]}
        )


@transaction.atomic
def create_team(*, competition: Competition, name: str) -> Team:
    _require_draft(competition)

    normalized_name = normalize_required_name(name, label="Team")

    if competition.teams.count() >= competition.total_team_count:
        raise ValidationError(
            {
                NON_FIELD_ERRORS: [
                    "The configured total number of teams has already been reached."
                ]
            }
        )

    if competition.teams.filter(name=normalized_name).exists():
        raise ValidationError(
            {"name": ["A team with this name already exists in the competition."]}
        )

    return Team.objects.create(competition=competition, name=normalized_name)


@transaction.atomic
def delete_team(*, team: Team) -> None:
    _require_draft(team.competition)
    team.delete()


@transaction.atomic
def assign_team_to_group(*, team: Team, group: Group) -> GroupMembership:
    competition = team.competition
    _require_draft(competition)

    if group.competition_id != competition.id:
        raise ValidationError(
            {"group": ["The team and group must belong to the same competition."]}
        )

    existing_membership = GroupMembership.objects.filter(team=team).first()
    if existing_membership and existing_membership.group_id == group.id:
        return existing_membership

    if group.memberships.count() >= competition.teams_per_group:
        raise ValidationError({"group": ["This group is already full."]})

    membership, _ = GroupMembership.objects.update_or_create(
        team=team,
        defaults={"group": group, "draw_lots_priority": None},
    )
    return membership


@transaction.atomic
def randomize_group_assignments(
    *,
    competition: Competition,
    rng: random.Random | None = None,
) -> list[GroupMembership]:
    _require_draft(competition)

    groups = list(competition.groups.order_by("ordinal"))
    if len(groups) != competition.group_count:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["The configured competition groups are incomplete."]}
        )

    teams = list(competition.teams.order_by("id"))
    if len(teams) != competition.total_team_count:
        raise ValidationError(
            {
                NON_FIELD_ERRORS: [
                    "Create every configured team before randomizing the groups."
                ]
            }
        )

    (rng or random.SystemRandom()).shuffle(teams)
    GroupMembership.objects.filter(group__competition=competition).delete()

    memberships = [
        GroupMembership(
            group=groups[index % competition.group_count],
            team=team,
        )
        for index, team in enumerate(teams)
    ]
    return GroupMembership.objects.bulk_create(memberships)
