from collections.abc import Sequence

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import transaction

from competitions.models import Competition, Group, Match, Round, Team


def build_round_robin(team_ids: Sequence[int]) -> list[list[tuple[int, int]]]:
    """Build deterministic single round-robin pairings with an implicit bye."""

    if len(team_ids) < 2:
        raise ValueError("A round-robin schedule requires at least two teams.")
    if len(set(team_ids)) != len(team_ids):
        raise ValueError("A round-robin schedule cannot contain duplicate teams.")

    rotation: list[int | None] = list(team_ids)
    if len(rotation) % 2:
        rotation.append(None)

    rounds: list[list[tuple[int, int]]] = []
    for _ in range(len(rotation) - 1):
        pairings: list[tuple[int, int]] = []
        for index in range(len(rotation) // 2):
            team_a = rotation[index]
            team_b = rotation[-index - 1]
            if team_a is not None and team_b is not None:
                pairings.append((team_a, team_b))
        rounds.append(pairings)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]

    return rounds


def _validated_group_teams(competition: Competition) -> list[tuple[Group, list[Team]]]:
    errors: list[str] = []
    groups = list(competition.groups.order_by("ordinal"))
    if len(groups) != competition.group_count:
        errors.append("The configured competition groups are incomplete.")

    competition_teams = list(competition.teams.order_by("id"))
    if len(competition_teams) != competition.total_team_count:
        errors.append("The competition does not contain the configured number of teams.")

    grouped_teams: list[tuple[Group, list[Team]]] = []
    assigned_team_ids: set[int] = set()
    for group in groups:
        memberships = list(
            group.memberships.select_related("team").order_by("team_id")
        )
        teams = [membership.team for membership in memberships]
        if len(teams) != competition.teams_per_group:
            errors.append(
                f"Group {group.label} must contain exactly "
                f"{competition.teams_per_group} teams."
            )
        if any(team.competition_id != competition.id for team in teams):
            errors.append(f"Group {group.label} contains a team from another competition.")
        assigned_team_ids.update(team.id for team in teams)
        grouped_teams.append((group, teams))

    expected_team_ids = {team.id for team in competition_teams}
    if assigned_team_ids != expected_team_ids:
        errors.append("Every competition team must belong to exactly one configured group.")

    if errors:
        raise ValidationError({NON_FIELD_ERRORS: errors})
    return grouped_teams


@transaction.atomic
def generate_group_fixtures(*, competition: Competition) -> list[Round]:
    if competition.status != Competition.Status.DRAFT:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["Group fixtures can be generated only from draft setup."]}
        )
    if competition.rounds.exists():
        raise ValidationError(
            {NON_FIELD_ERRORS: ["This competition already contains generated rounds."]}
        )

    grouped_teams = _validated_group_teams(competition)
    schedules = [
        (group, build_round_robin([team.id for team in teams]))
        for group, teams in grouped_teams
    ]
    round_count = len(schedules[0][1])
    rounds = [
        Round.objects.create(
            competition=competition,
            stage=Round.Stage.GROUP,
            number=round_number,
        )
        for round_number in range(1, round_count + 1)
    ]

    matches: list[Match] = []
    for round_index, round_ in enumerate(rounds):
        position = 1
        for group, schedule in schedules:
            for team_a_id, team_b_id in schedule[round_index]:
                matches.append(
                    Match(
                        round=round_,
                        group=group,
                        position=position,
                        kind=Match.Kind.REGULAR,
                        team_a_id=team_a_id,
                        team_b_id=team_b_id,
                    )
                )
                position += 1
    Match.objects.bulk_create(matches)

    competition.status = Competition.Status.GROUP_STAGE
    competition.save(update_fields=["status"])
    return rounds


@transaction.atomic
def return_to_setup(*, competition: Competition) -> None:
    if competition.status != Competition.Status.GROUP_STAGE:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["Only a group-stage competition can return to setup."]}
        )

    group_rounds = competition.rounds.filter(stage=Round.Stage.GROUP)
    if Match.objects.filter(
        round__in=group_rounds,
        status=Match.Status.COMPLETED,
    ).exists():
        raise ValidationError(
            {
                NON_FIELD_ERRORS: [
                    "The competition cannot return to setup after a result is completed."
                ]
            }
        )

    group_rounds.delete()
    competition.status = Competition.Status.DRAFT
    competition.save(update_fields=["status"])
