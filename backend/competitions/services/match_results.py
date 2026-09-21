from collections.abc import Sequence
from dataclasses import dataclass, field

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import transaction
from django.db.models import Q

from competitions.models import (
    Competition,
    Match,
    PlayerMatchStat,
    RosterMembership,
    Round,
    Team,
    TeamMatchStat,
)
from competitions.selectors import MatchScore


MAX_COUNTER_VALUE = 32_767


@dataclass(frozen=True)
class PlayerStatLine:
    roster_membership_id: int
    goals: int = 0
    assists: int = 0


@dataclass(frozen=True)
class TeamResult:
    team_id: int
    own_goals_received: int = 0
    player_stats: Sequence[PlayerStatLine] = field(default_factory=tuple)


def _validate_counter(*, field_name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidationError({field_name: ["This value must be an integer."]})
    if value < 0 or value > MAX_COUNTER_VALUE:
        raise ValidationError(
            {field_name: [f"This value must be between 0 and {MAX_COUNTER_VALUE}."]}
        )


def _prepare_team_result(
    *,
    match: Match,
    team: Team,
    result: TeamResult,
) -> tuple[int, list[PlayerMatchStat]]:
    if result.team_id != team.id:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["Submitted result teams do not match the fixture."]}
        )

    _validate_counter(
        field_name="own_goals_received",
        value=result.own_goals_received,
    )

    membership_ids = [line.roster_membership_id for line in result.player_stats]
    if len(membership_ids) != len(set(membership_ids)):
        raise ValidationError(
            {"player_stats": ["A roster member may appear only once per team result."]}
        )

    memberships = RosterMembership.objects.filter(id__in=membership_ids).in_bulk()
    if len(memberships) != len(membership_ids):
        raise ValidationError(
            {"player_stats": ["One or more roster memberships do not exist."]}
        )

    player_goal_total = 0
    assist_total = 0
    rows: list[PlayerMatchStat] = []
    for line in result.player_stats:
        membership = memberships[line.roster_membership_id]
        if membership.competition_id != match.round.competition_id:
            raise ValidationError(
                {"player_stats": ["A roster member belongs to another competition."]}
            )
        if membership.team_id != team.id:
            raise ValidationError(
                {"player_stats": ["A roster member belongs to the other team."]}
            )

        _validate_counter(field_name="goals", value=line.goals)
        _validate_counter(field_name="assists", value=line.assists)
        player_goal_total += line.goals
        assist_total += line.assists
        if line.goals or line.assists:
            rows.append(
                PlayerMatchStat(
                    match=match,
                    roster_membership=membership,
                    goals=line.goals,
                    assists=line.assists,
                )
            )

    if assist_total > player_goal_total:
        raise ValidationError(
            {
                "player_stats": [
                    "A team's total assists cannot exceed its player-attributed goals."
                ]
            }
        )

    return player_goal_total + result.own_goals_received, rows


def _validate_match_phase(match: Match) -> Competition:
    competition = match.round.competition
    if match.round.stage == Round.Stage.GROUP:
        if competition.status != Competition.Status.GROUP_STAGE:
            raise ValidationError(
                {NON_FIELD_ERRORS: ["Group results are not editable in this phase."]}
            )
        if match.group_id is None or match.kind != Match.Kind.REGULAR:
            raise ValidationError(
                {NON_FIELD_ERRORS: ["The group-stage fixture is invalid."]}
            )
    elif match.round.stage == Round.Stage.KNOCKOUT:
        if competition.status != Competition.Status.KNOCKOUT:
            raise ValidationError(
                {NON_FIELD_ERRORS: ["Knockout results are not editable in this phase."]}
            )
        if match.group_id is not None:
            raise ValidationError(
                {NON_FIELD_ERRORS: ["The knockout fixture is invalid."]}
            )
    else:
        raise ValidationError({NON_FIELD_ERRORS: ["The match stage is invalid."]})
    return competition


def _validate_shootout_winner(
    *,
    match: Match,
    score: MatchScore,
    shootout_winner_id: int | None,
) -> None:
    if match.round.stage == Round.Stage.GROUP:
        if shootout_winner_id is not None:
            raise ValidationError(
                {"shootout_winner": ["Group-stage matches cannot have a shootout winner."]}
            )
        return

    if score.team_a == score.team_b:
        if shootout_winner_id not in {match.team_a_id, match.team_b_id}:
            raise ValidationError(
                {
                    "shootout_winner": [
                        "A tied knockout match requires one participant as its winner."
                    ]
                }
            )
    elif shootout_winner_id is not None:
        raise ValidationError(
            {
                "shootout_winner": [
                    "A shootout winner is allowed only when the normal score is tied."
                ]
            }
        )


def _winner_and_loser(match: Match, score: MatchScore) -> tuple[Team, Team]:
    if score.team_a > score.team_b:
        return match.team_a, match.team_b
    if score.team_b > score.team_a:
        return match.team_b, match.team_a
    if match.shootout_winner_id == match.team_a_id:
        return match.team_a, match.team_b
    return match.team_b, match.team_a


def _update_knockout_dependents(match: Match, score: MatchScore) -> None:
    winner, loser = _winner_and_loser(match, score)
    dependents = Match.objects.filter(
        Q(source_match_a=match) | Q(source_match_b=match)
    )
    for dependent in dependents:
        changed_fields: list[str] = []
        if dependent.source_match_a_id == match.id:
            dependent.team_a = (
                winner
                if dependent.source_outcome_a == Match.SourceOutcome.WINNER
                else loser
            )
            changed_fields.append("team_a")
        if dependent.source_match_b_id == match.id:
            dependent.team_b = (
                winner
                if dependent.source_outcome_b == Match.SourceOutcome.WINNER
                else loser
            )
            changed_fields.append("team_b")
        dependent.save(update_fields=changed_fields)


def _update_competition_completion(competition: Competition) -> None:
    final = Match.objects.filter(
        round__competition=competition,
        kind=Match.Kind.FINAL,
    ).first()
    if final is None or final.status != Match.Status.COMPLETED:
        return

    if competition.third_place_enabled:
        third_place = Match.objects.filter(
            round__competition=competition,
            kind=Match.Kind.THIRD_PLACE,
        ).first()
        if third_place is None or third_place.status != Match.Status.COMPLETED:
            return

    competition.status = Competition.Status.COMPLETED
    competition.save(update_fields=["status"])


@transaction.atomic
def complete_or_correct_match(
    *,
    match: Match,
    team_a_result: TeamResult,
    team_b_result: TeamResult,
    shootout_winner_id: int | None = None,
) -> MatchScore:
    competition = _validate_match_phase(match)
    if match.team_a_id is None or match.team_b_id is None:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["Both participants are required to complete a match."]}
        )

    was_completed = match.status == Match.Status.COMPLETED
    completed_dependents_exist = Match.objects.filter(
        Q(source_match_a=match) | Q(source_match_b=match),
        status=Match.Status.COMPLETED,
    ).exists()
    if was_completed and completed_dependents_exist:
        raise ValidationError(
            {
                NON_FIELD_ERRORS: [
                    "This result cannot be corrected after a dependent match is completed."
                ]
            }
        )

    score_a, team_a_rows = _prepare_team_result(
        match=match,
        team=match.team_a,
        result=team_a_result,
    )
    score_b, team_b_rows = _prepare_team_result(
        match=match,
        team=match.team_b,
        result=team_b_result,
    )
    score = MatchScore(team_a=score_a, team_b=score_b)
    _validate_shootout_winner(
        match=match,
        score=score,
        shootout_winner_id=shootout_winner_id,
    )

    PlayerMatchStat.objects.filter(match=match).delete()
    TeamMatchStat.objects.filter(match=match).delete()
    PlayerMatchStat.objects.bulk_create([*team_a_rows, *team_b_rows])
    TeamMatchStat.objects.bulk_create(
        [
            TeamMatchStat(
                match=match,
                team=match.team_a,
                own_goals_received=team_a_result.own_goals_received,
            ),
            TeamMatchStat(
                match=match,
                team=match.team_b,
                own_goals_received=team_b_result.own_goals_received,
            ),
        ]
    )
    match.status = Match.Status.COMPLETED
    match.shootout_winner_id = shootout_winner_id
    match.save(update_fields=["status", "shootout_winner"])

    if match.round.stage == Round.Stage.GROUP:
        if was_completed and match.group_id is not None:
            match.group.memberships.update(draw_lots_priority=None)
    else:
        _update_knockout_dependents(match, score)
        _update_competition_completion(competition)

    return score
