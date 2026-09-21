from dataclasses import dataclass

from competitions.models import Competition, Match, Round, Team
from competitions.selectors.group_standings import calculate_group_standings
from competitions.selectors.match_scores import get_match_score


@dataclass(frozen=True)
class CompetitionLocks:
    structure_locked: bool
    roster_locked: bool
    can_return_to_setup: bool
    can_finalize_group_stage: bool
    can_reopen_group_stage: bool


def get_match_winner(match: Match) -> Team | None:
    if (
        match.status != Match.Status.COMPLETED
        or match.team_a_id is None
        or match.team_b_id is None
    ):
        return None
    score = get_match_score(match)
    if score.team_a > score.team_b:
        return match.team_a
    if score.team_b > score.team_a:
        return match.team_b
    if match.round.stage == Round.Stage.KNOCKOUT:
        return match.shootout_winner
    return None


def get_champion(competition: Competition) -> Team | None:
    final = (
        Match.objects.filter(
            round__competition=competition,
            kind=Match.Kind.FINAL,
        )
        .select_related("team_a", "team_b", "shootout_winner", "round")
        .first()
    )
    return get_match_winner(final) if final is not None else None


def get_third_place_finisher(competition: Competition) -> Team | None:
    match = (
        Match.objects.filter(
            round__competition=competition,
            kind=Match.Kind.THIRD_PLACE,
        )
        .select_related("team_a", "team_b", "shootout_winner", "round")
        .first()
    )
    return get_match_winner(match) if match is not None else None


def get_knockout_round_name(round_: Round) -> str:
    if round_.stage != Round.Stage.KNOCKOUT:
        raise ValueError("Only knockout rounds have knockout display names.")
    total_rounds = Round.objects.filter(
        competition=round_.competition,
        stage=Round.Stage.KNOCKOUT,
    ).count()
    teams_at_round_start = 2 ** (total_rounds - round_.number + 1)
    names = {
        2: "Final",
        4: "Semifinals",
        8: "Quarterfinals",
    }
    return names.get(teams_at_round_start, f"Round of {teams_at_round_start}")


def get_competition_locks(competition: Competition) -> CompetitionLocks:
    any_result = Match.objects.filter(
        round__competition=competition,
        status=Match.Status.COMPLETED,
    ).exists()
    knockout_result = Match.objects.filter(
        round__competition=competition,
        round__stage=Round.Stage.KNOCKOUT,
        status=Match.Status.COMPLETED,
    ).exists()
    pending_group_result = Match.objects.filter(
        round__competition=competition,
        round__stage=Round.Stage.GROUP,
        status=Match.Status.PENDING,
    ).exists()
    has_group_matches = Match.objects.filter(
        round__competition=competition,
        round__stage=Round.Stage.GROUP,
    ).exists()
    group_stage_resolved = False
    if (
        competition.status == Competition.Status.GROUP_STAGE
        and has_group_matches
        and not pending_group_result
    ):
        groups = list(competition.groups.order_by("ordinal"))
        group_stage_resolved = len(groups) == competition.group_count and all(
            calculate_group_standings(group).is_resolved for group in groups
        )
    return CompetitionLocks(
        structure_locked=competition.status != Competition.Status.DRAFT,
        roster_locked=any_result
        or competition.status in {Competition.Status.KNOCKOUT, Competition.Status.COMPLETED},
        can_return_to_setup=(
            competition.status == Competition.Status.GROUP_STAGE and not any_result
        ),
        can_finalize_group_stage=(
            competition.status == Competition.Status.GROUP_STAGE
            and has_group_matches
            and not pending_group_result
            and group_stage_resolved
        ),
        can_reopen_group_stage=(
            competition.status == Competition.Status.KNOCKOUT and not knockout_result
        ),
    )
