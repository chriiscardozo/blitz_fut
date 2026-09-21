from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import transaction

from competitions.models import Competition, Match, Player, RosterMembership, Team
from competitions.services.common import normalize_required_name


def _require_roster_editable(competition: Competition) -> None:
    if competition.status == Competition.Status.DRAFT:
        return

    has_completed_result = Match.objects.filter(
        round__competition=competition,
        status=Match.Status.COMPLETED,
    ).exists()
    if competition.status == Competition.Status.GROUP_STAGE and not has_completed_result:
        return

    raise ValidationError(
        {
            NON_FIELD_ERRORS: [
                "Rosters cannot be changed after the first match result is completed."
            ]
        }
    )


def _normalize_player_name(name: str) -> str:
    return normalize_required_name(name, label="Player")


@transaction.atomic
def create_player(*, name: str) -> Player:
    return Player.objects.create(name=_normalize_player_name(name))


@transaction.atomic
def assign_player_to_team(*, player: Player, team: Team) -> RosterMembership:
    competition = team.competition
    _require_roster_editable(competition)

    membership, _ = RosterMembership.objects.update_or_create(
        competition=competition,
        player=player,
        defaults={"team": team},
    )
    return membership


@transaction.atomic
def create_player_and_assign(*, name: str, team: Team) -> RosterMembership:
    _require_roster_editable(team.competition)
    player = create_player(name=name)
    return assign_player_to_team(player=player, team=team)


@transaction.atomic
def remove_player_from_roster(*, membership: RosterMembership) -> None:
    _require_roster_editable(membership.competition)
    membership.delete()


@transaction.atomic
def rename_player(*, player: Player, name: str) -> Player:
    player.name = _normalize_player_name(name)
    player.save(update_fields=["name"])
    return player
