from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import transaction

from competitions.models import Competition, Match, Player, RosterMembership, Team
from competitions.services.common import normalize_required_name


@transaction.atomic
def rename_competition(*, competition: Competition, name: str) -> Competition:
    competition.name = normalize_required_name(name, label="Competition")
    competition.save(update_fields=["name"])
    return competition


@transaction.atomic
def rename_team(*, team: Team, name: str) -> Team:
    normalized_name = normalize_required_name(name, label="Team")
    if team.competition.teams.exclude(id=team.id).filter(name=normalized_name).exists():
        raise ValidationError(
            {"name": ["A team with this name already exists in the competition."]}
        )
    team.name = normalized_name
    team.save(update_fields=["name"])
    return team


@transaction.atomic
def delete_competition(*, competition: Competition, confirmed_name: str) -> None:
    if confirmed_name != competition.name:
        raise ValidationError(
            {
                NON_FIELD_ERRORS: [
                    "Type the exact competition name to confirm deletion."
                ]
            }
        )

    # Delete dependents before their protected team and roster references.
    # Match deletion also removes player/team statistics and all bracket links.
    Match.objects.filter(round__competition=competition).delete()
    RosterMembership.objects.filter(competition=competition).delete()
    Team.objects.filter(competition=competition).delete()
    competition.delete()


@transaction.atomic
def delete_unreferenced_player(*, player: Player) -> None:
    if player.roster_memberships.exists():
        raise ValidationError(
            {
                NON_FIELD_ERRORS: [
                    "This player cannot be deleted because competition history references them."
                ]
            }
        )
    player.delete()
