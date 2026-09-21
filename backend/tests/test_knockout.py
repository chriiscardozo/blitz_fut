import pytest
from django.core.exceptions import ValidationError

from competitions.models import Competition, Match, Round
from competitions.services import (
    TeamResult,
    assign_team_to_group,
    build_knockout_team_order,
    complete_or_correct_match,
    create_competition,
    create_team,
    finalize_group_stage,
    generate_group_fixtures,
    reopen_group_stage,
    seed_slots,
)


def ready_group_stage(
    *,
    group_count: int,
    teams_per_group: int,
    qualifiers_per_group: int,
    third_place_enabled: bool = False,
) -> Competition:
    competition = create_competition(
        name="Bracket Cup",
        year=2026,
        group_count=group_count,
        total_team_count=group_count * teams_per_group,
        qualifiers_per_group=qualifiers_per_group,
        third_place_enabled=third_place_enabled,
    )
    for group in competition.groups.order_by("ordinal"):
        for position in range(1, teams_per_group + 1):
            team = create_team(
                competition=competition,
                name=f"{group.label}{position}",
            )
            membership = assign_team_to_group(team=team, group=group)
            membership.draw_lots_priority = teams_per_group - position + 1
            membership.save(update_fields=["draw_lots_priority"])
    generate_group_fixtures(competition=competition)
    for match in Match.objects.filter(
        round__competition=competition,
        round__stage=Round.Stage.GROUP,
    ).select_related("team_a", "team_b", "round__competition"):
        complete_or_correct_match(
            match=match,
            team_a_result=TeamResult(team_id=match.team_a_id),
            team_b_result=TeamResult(team_id=match.team_b_id),
        )
    return competition


def test_seed_slots_follow_standard_recursive_placement():
    assert seed_slots(2) == [1, 2]
    assert seed_slots(4) == [1, 4, 2, 3]
    assert seed_slots(8) == [1, 8, 4, 5, 2, 7, 3, 6]
    with pytest.raises(ValueError):
        seed_slots(6)


@pytest.mark.parametrize(
    ("group_count", "qualifier_count"),
    [(1, 2), (1, 4), (2, 1), (2, 2), (2, 4), (4, 1), (4, 2), (8, 1)],
)
def test_knockout_order_contains_every_qualifier_once_and_cross_seeds(
    group_count: int,
    qualifier_count: int,
):
    qualifiers = [
        [group * 100 + position for position in range(1, qualifier_count + 1)]
        for group in range(1, group_count + 1)
    ]

    order = build_knockout_team_order(qualifiers)

    assert len(order) == group_count * qualifier_count
    assert set(order) == {team_id for group in qualifiers for team_id in group}
    if group_count > 1:
        for team_a, team_b in zip(order[::2], order[1::2], strict=True):
            assert team_a // 100 != team_b // 100
            assert abs(team_a // 100 - team_b // 100) == 1
            assert team_a % 100 + team_b % 100 == qualifier_count + 1


def test_documented_two_group_four_qualifier_placement():
    order = build_knockout_team_order(
        [[11, 12, 13, 14], [21, 22, 23, 24]]
    )
    assert list(zip(order[::2], order[1::2], strict=True)) == [
        (11, 24),
        (22, 13),
        (21, 14),
        (12, 23),
    ]


@pytest.mark.django_db
def test_finalization_builds_all_rounds_and_fixed_sources():
    competition = ready_group_stage(
        group_count=2,
        teams_per_group=4,
        qualifiers_per_group=4,
    )

    rounds = finalize_group_stage(competition=competition, confirmed=True)

    competition.refresh_from_db()
    assert competition.status == Competition.Status.KNOCKOUT
    assert [round_.matches.count() for round_ in rounds] == [4, 2, 1]
    first_round_pairs = [
        (match.team_a.name, match.team_b.name)
        for match in rounds[0].matches.select_related("team_a", "team_b")
    ]
    assert first_round_pairs == [
        ("A1", "B4"),
        ("B2", "A3"),
        ("B1", "A4"),
        ("A2", "B3"),
    ]
    for round_ in rounds[1:]:
        for match in round_.matches.all():
            assert match.source_match_a is not None
            assert match.source_match_b is not None
            assert match.source_outcome_a == Match.SourceOutcome.WINNER
            assert match.source_outcome_b == Match.SourceOutcome.WINNER
    final = rounds[-1].matches.get()
    assert final.kind == Match.Kind.FINAL


@pytest.mark.django_db
def test_finalization_creates_third_place_from_semifinal_losers():
    competition = ready_group_stage(
        group_count=2,
        teams_per_group=2,
        qualifiers_per_group=2,
        third_place_enabled=True,
    )

    rounds = finalize_group_stage(competition=competition, confirmed=True)

    final_round_matches = list(rounds[-1].matches.order_by("position"))
    assert [match.kind for match in final_round_matches] == [
        Match.Kind.FINAL,
        Match.Kind.THIRD_PLACE,
    ]
    third_place = final_round_matches[1]
    assert third_place.source_outcome_a == Match.SourceOutcome.LOSER
    assert third_place.source_outcome_b == Match.SourceOutcome.LOSER
    assert third_place.source_match_a.round == rounds[-2]
    assert third_place.source_match_b.round == rounds[-2]


@pytest.mark.django_db
def test_finalization_requires_completion_resolution_and_confirmation():
    competition = create_competition(
        name="Not Ready Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    group = competition.groups.get()
    for name in ("A", "B"):
        assign_team_to_group(
            team=create_team(competition=competition, name=name),
            group=group,
        )
    generate_group_fixtures(competition=competition)

    with pytest.raises(ValidationError, match="must be completed"):
        finalize_group_stage(competition=competition, confirmed=True)

    match = Match.objects.get(round__competition=competition)
    complete_or_correct_match(
        match=match,
        team_a_result=TeamResult(team_id=match.team_a_id),
        team_b_result=TeamResult(team_id=match.team_b_id),
    )
    with pytest.raises(ValidationError, match="drawing-of-lots"):
        finalize_group_stage(competition=competition, confirmed=True)

    group.memberships.filter(team=match.team_a).update(draw_lots_priority=2)
    group.memberships.filter(team=match.team_b).update(draw_lots_priority=1)
    with pytest.raises(ValidationError) as error:
        finalize_group_stage(competition=competition, confirmed=False)
    assert "confirmed" in error.value.message_dict


@pytest.mark.django_db
def test_reopen_removes_unplayed_bracket_and_restores_group_stage():
    competition = ready_group_stage(
        group_count=1,
        teams_per_group=4,
        qualifiers_per_group=4,
    )
    finalize_group_stage(competition=competition, confirmed=True)

    reopen_group_stage(competition=competition)

    competition.refresh_from_db()
    assert competition.status == Competition.Status.GROUP_STAGE
    assert not competition.rounds.filter(stage=Round.Stage.KNOCKOUT).exists()
    assert competition.rounds.filter(stage=Round.Stage.GROUP).exists()


@pytest.mark.django_db
def test_reopen_is_blocked_after_first_knockout_result():
    competition = ready_group_stage(
        group_count=1,
        teams_per_group=4,
        qualifiers_per_group=4,
    )
    rounds = finalize_group_stage(competition=competition, confirmed=True)
    semifinal = rounds[0].matches.select_related("team_a", "team_b").first()
    complete_or_correct_match(
        match=semifinal,
        team_a_result=TeamResult(team_id=semifinal.team_a_id),
        team_b_result=TeamResult(team_id=semifinal.team_b_id),
        shootout_winner_id=semifinal.team_a_id,
    )

    with pytest.raises(ValidationError, match="knockout result"):
        reopen_group_stage(competition=competition)
