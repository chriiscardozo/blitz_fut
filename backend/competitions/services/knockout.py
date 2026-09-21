from collections.abc import Sequence
from math import log2

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import transaction

from competitions.models import Competition, Match, Round
from competitions.selectors import calculate_group_standings


def seed_slots(size: int) -> list[int]:
    """Return the standard one-based seed order for bracket leaf slots."""

    if size < 2 or size & (size - 1):
        raise ValueError("Bracket size must be a power of two of at least two.")
    slots = [1, 2]
    current_size = 2
    while current_size < size:
        next_size = current_size * 2
        slots = [value for seed in slots for value in (seed, next_size + 1 - seed)]
        current_size = next_size
    return slots


def build_knockout_team_order(
    group_qualifiers: Sequence[Sequence[int]],
) -> list[int]:
    """Place qualifiers in deterministic first-round bracket leaf order."""

    if not group_qualifiers:
        raise ValueError("At least one group of qualifiers is required.")
    group_count = len(group_qualifiers)
    qualifier_count = len(group_qualifiers[0])
    if group_count & (group_count - 1):
        raise ValueError("The number of groups must be a power of two.")
    if qualifier_count < 1 or qualifier_count & (qualifier_count - 1):
        raise ValueError("Qualifiers per group must be a power of two.")
    if any(len(qualifiers) != qualifier_count for qualifiers in group_qualifiers):
        raise ValueError("Every group must provide the same number of qualifiers.")
    flat_ids = [team_id for qualifiers in group_qualifiers for team_id in qualifiers]
    if len(set(flat_ids)) != len(flat_ids):
        raise ValueError("A qualifier may appear only once in the bracket.")
    if len(flat_ids) < 2:
        raise ValueError("At least two knockout qualifiers are required.")

    if group_count == 1:
        return [group_qualifiers[0][seed - 1] for seed in seed_slots(qualifier_count)]

    ordered: list[int] = []
    for group_index in range(0, group_count, 2):
        left = group_qualifiers[group_index]
        right = group_qualifiers[group_index + 1]
        local_seeds = [
            team_id
            for position in range(qualifier_count)
            for team_id in (left[position], right[position])
        ]
        ordered.extend(
            local_seeds[seed - 1] for seed in seed_slots(qualifier_count * 2)
        )
    return ordered


def _create_knockout_bracket(
    *,
    competition: Competition,
    ordered_team_ids: Sequence[int],
) -> list[Round]:
    knockout_team_count = len(ordered_team_ids)
    round_count = int(log2(knockout_team_count))
    rounds = [
        Round.objects.create(
            competition=competition,
            stage=Round.Stage.KNOCKOUT,
            number=number,
        )
        for number in range(1, round_count + 1)
    ]

    previous_matches: list[Match] = []
    for round_index, round_ in enumerate(rounds):
        is_first = round_index == 0
        is_final = round_index == round_count - 1
        match_count = knockout_team_count // (2 ** (round_index + 1))
        current_matches: list[Match] = []
        for position in range(1, match_count + 1):
            if is_first:
                team_a_id = ordered_team_ids[(position - 1) * 2]
                team_b_id = ordered_team_ids[(position - 1) * 2 + 1]
                match = Match.objects.create(
                    round=round_,
                    position=position,
                    kind=Match.Kind.FINAL if is_final else Match.Kind.REGULAR,
                    team_a_id=team_a_id,
                    team_b_id=team_b_id,
                )
            else:
                source_a = previous_matches[(position - 1) * 2]
                source_b = previous_matches[(position - 1) * 2 + 1]
                match = Match.objects.create(
                    round=round_,
                    position=position,
                    kind=Match.Kind.FINAL if is_final else Match.Kind.REGULAR,
                    source_match_a=source_a,
                    source_outcome_a=Match.SourceOutcome.WINNER,
                    source_match_b=source_b,
                    source_outcome_b=Match.SourceOutcome.WINNER,
                )
            current_matches.append(match)
        previous_matches = current_matches

    if competition.third_place_enabled:
        semifinal_round = rounds[-2]
        semifinals = list(semifinal_round.matches.order_by("position"))
        Match.objects.create(
            round=rounds[-1],
            position=2,
            kind=Match.Kind.THIRD_PLACE,
            source_match_a=semifinals[0],
            source_outcome_a=Match.SourceOutcome.LOSER,
            source_match_b=semifinals[1],
            source_outcome_b=Match.SourceOutcome.LOSER,
        )
    return rounds


@transaction.atomic
def finalize_group_stage(
    *,
    competition: Competition,
    confirmed: bool,
) -> list[Round]:
    if competition.status != Competition.Status.GROUP_STAGE:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["Only an active group stage can be finalized."]}
        )
    if not confirmed:
        raise ValidationError(
            {"confirmed": ["Confirm that the group stage should be finalized."]}
        )
    if competition.rounds.filter(stage=Round.Stage.KNOCKOUT).exists():
        raise ValidationError(
            {NON_FIELD_ERRORS: ["This competition already has a knockout bracket."]}
        )
    group_matches = Match.objects.filter(
        round__competition=competition,
        round__stage=Round.Stage.GROUP,
    )
    expected_match_count = (
        competition.group_count
        * competition.teams_per_group
        * (competition.teams_per_group - 1)
        // 2
    )
    if group_matches.count() != expected_match_count:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["The generated group-stage fixture set is incomplete."]}
        )
    if competition.rounds.filter(
        stage=Round.Stage.GROUP,
        matches__status=Match.Status.PENDING,
    ).exists():
        raise ValidationError(
            {NON_FIELD_ERRORS: ["Every group-stage match must be completed first."]}
        )

    groups = list(competition.groups.order_by("ordinal"))
    if len(groups) != competition.group_count:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["The configured competition groups are incomplete."]}
        )

    group_qualifiers: list[list[int]] = []
    unresolved_group_labels: list[str] = []
    for group in groups:
        standings = calculate_group_standings(group)
        if len(standings.rows) != competition.teams_per_group:
            raise ValidationError(
                {NON_FIELD_ERRORS: [f"Group {group.label} is structurally incomplete."]}
            )
        if not standings.is_resolved:
            unresolved_group_labels.append(group.label)
        group_qualifiers.append(
            [
                row.team_id
                for row in standings.rows[: competition.qualifiers_per_group]
            ]
        )
    if unresolved_group_labels:
        raise ValidationError(
            {
                NON_FIELD_ERRORS: [
                    "Resolve every drawing-of-lots tie before finalizing groups: "
                    + ", ".join(unresolved_group_labels)
                    + "."
                ]
            }
        )

    ordered_team_ids = build_knockout_team_order(group_qualifiers)
    rounds = _create_knockout_bracket(
        competition=competition,
        ordered_team_ids=ordered_team_ids,
    )
    competition.status = Competition.Status.KNOCKOUT
    competition.save(update_fields=["status"])
    return rounds


@transaction.atomic
def reopen_group_stage(*, competition: Competition) -> None:
    if competition.status != Competition.Status.KNOCKOUT:
        raise ValidationError(
            {NON_FIELD_ERRORS: ["Only a knockout-stage competition can be reopened."]}
        )
    knockout_rounds = competition.rounds.filter(stage=Round.Stage.KNOCKOUT)
    if Match.objects.filter(
        round__in=knockout_rounds,
        status=Match.Status.COMPLETED,
    ).exists():
        raise ValidationError(
            {
                NON_FIELD_ERRORS: [
                    "The group stage cannot be reopened after a knockout result is completed."
                ]
            }
        )
    knockout_rounds.delete()
    competition.status = Competition.Status.GROUP_STAGE
    competition.save(update_fields=["status"])
