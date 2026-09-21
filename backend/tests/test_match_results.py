from dataclasses import dataclass

import pytest
from django.core.exceptions import ValidationError

from competitions.models import (
    Competition,
    GroupMembership,
    Match,
    PlayerMatchStat,
    RosterMembership,
    Round,
    Team,
    TeamMatchStat,
)
from competitions.selectors import MatchScore, get_match_score
from competitions.services import (
    PlayerStatLine,
    TeamResult,
    assign_team_to_group,
    complete_or_correct_match,
    create_competition,
    create_player_and_assign,
    create_team,
    generate_group_fixtures,
)


@dataclass
class MatchSetup:
    competition: Competition
    match: Match
    team_a: Team
    team_b: Team
    team_a_players: list[RosterMembership]
    team_b_players: list[RosterMembership]


@pytest.fixture
def group_match(db) -> MatchSetup:
    competition = create_competition(
        name="Results Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    group = competition.groups.get()
    team_a = create_team(competition=competition, name="Green")
    team_b = create_team(competition=competition, name="Blue")
    assign_team_to_group(team=team_a, group=group)
    assign_team_to_group(team=team_b, group=group)
    team_a_players = [
        create_player_and_assign(name="Alex", team=team_a),
        create_player_and_assign(name="Blair", team=team_a),
    ]
    team_b_players = [create_player_and_assign(name="Casey", team=team_b)]
    generate_group_fixtures(competition=competition)
    return MatchSetup(
        competition=competition,
        match=Match.objects.get(round__competition=competition),
        team_a=team_a,
        team_b=team_b,
        team_a_players=team_a_players,
        team_b_players=team_b_players,
    )


@pytest.mark.django_db
def test_complete_match_derives_score_and_persists_aggregate_stats(
    group_match: MatchSetup,
):
    score = complete_or_correct_match(
        match=group_match.match,
        team_a_result=TeamResult(
            team_id=group_match.team_a.id,
            own_goals_received=1,
            player_stats=[
                PlayerStatLine(
                    roster_membership_id=group_match.team_a_players[0].id,
                    goals=2,
                ),
                PlayerStatLine(
                    roster_membership_id=group_match.team_a_players[1].id,
                    assists=2,
                ),
            ],
        ),
        team_b_result=TeamResult(
            team_id=group_match.team_b.id,
            player_stats=[
                PlayerStatLine(
                    roster_membership_id=group_match.team_b_players[0].id,
                    goals=1,
                )
            ],
        ),
    )

    group_match.match.refresh_from_db()
    assert score == MatchScore(team_a=3, team_b=1)
    assert get_match_score(group_match.match) == score
    assert group_match.match.status == Match.Status.COMPLETED
    assert PlayerMatchStat.objects.filter(match=group_match.match).count() == 3
    assert TeamMatchStat.objects.filter(match=group_match.match).count() == 2


@pytest.mark.django_db
def test_zero_zero_result_persists_team_rows(group_match: MatchSetup):
    score = complete_or_correct_match(
        match=group_match.match,
        team_a_result=TeamResult(team_id=group_match.team_a.id),
        team_b_result=TeamResult(team_id=group_match.team_b.id),
    )

    assert score == MatchScore(team_a=0, team_b=0)
    assert PlayerMatchStat.objects.filter(match=group_match.match).count() == 0
    assert TeamMatchStat.objects.filter(match=group_match.match).count() == 2


@pytest.mark.django_db
def test_team_assists_cannot_exceed_player_attributed_goals(
    group_match: MatchSetup,
):
    with pytest.raises(ValidationError) as error:
        complete_or_correct_match(
            match=group_match.match,
            team_a_result=TeamResult(
                team_id=group_match.team_a.id,
                player_stats=[
                    PlayerStatLine(
                        roster_membership_id=group_match.team_a_players[0].id,
                        goals=1,
                        assists=2,
                    )
                ],
            ),
            team_b_result=TeamResult(team_id=group_match.team_b.id),
        )

    group_match.match.refresh_from_db()
    assert "player_stats" in error.value.message_dict
    assert group_match.match.status == Match.Status.PENDING
    assert not PlayerMatchStat.objects.filter(match=group_match.match).exists()


@pytest.mark.django_db
def test_player_stat_must_belong_to_submitted_team(group_match: MatchSetup):
    with pytest.raises(ValidationError) as error:
        complete_or_correct_match(
            match=group_match.match,
            team_a_result=TeamResult(
                team_id=group_match.team_a.id,
                player_stats=[
                    PlayerStatLine(
                        roster_membership_id=group_match.team_b_players[0].id,
                        goals=1,
                    )
                ],
            ),
            team_b_result=TeamResult(team_id=group_match.team_b.id),
        )

    assert "player_stats" in error.value.message_dict


@pytest.mark.django_db
def test_group_match_rejects_shootout_winner(group_match: MatchSetup):
    with pytest.raises(ValidationError) as error:
        complete_or_correct_match(
            match=group_match.match,
            team_a_result=TeamResult(team_id=group_match.team_a.id),
            team_b_result=TeamResult(team_id=group_match.team_b.id),
            shootout_winner_id=group_match.team_a.id,
        )

    assert "shootout_winner" in error.value.message_dict


@pytest.mark.django_db
def test_correction_replaces_stats_and_clears_group_draw_priorities(
    group_match: MatchSetup,
):
    complete_or_correct_match(
        match=group_match.match,
        team_a_result=TeamResult(
            team_id=group_match.team_a.id,
            player_stats=[
                PlayerStatLine(
                    roster_membership_id=group_match.team_a_players[0].id,
                    goals=2,
                    assists=1,
                )
            ],
        ),
        team_b_result=TeamResult(team_id=group_match.team_b.id),
    )
    GroupMembership.objects.filter(group=group_match.match.group).update(
        draw_lots_priority=1
    )

    corrected_score = complete_or_correct_match(
        match=group_match.match,
        team_a_result=TeamResult(team_id=group_match.team_a.id),
        team_b_result=TeamResult(
            team_id=group_match.team_b.id,
            own_goals_received=1,
        ),
    )

    assert corrected_score == MatchScore(team_a=0, team_b=1)
    assert not PlayerMatchStat.objects.filter(match=group_match.match).exists()
    assert set(
        TeamMatchStat.objects.filter(match=group_match.match).values_list(
            "own_goals_received", flat=True
        )
    ) == {0, 1}
    assert not GroupMembership.objects.filter(
        group=group_match.match.group,
        draw_lots_priority__isnull=False,
    ).exists()


def create_knockout_match(*, db, team_count: int = 2) -> MatchSetup:
    competition = create_competition(
        name="Knockout Cup",
        year=2026,
        group_count=1,
        total_team_count=team_count,
        qualifiers_per_group=team_count,
        third_place_enabled=team_count >= 4,
    )
    teams = [
        create_team(competition=competition, name=f"Team {index + 1}")
        for index in range(team_count)
    ]
    memberships = [
        create_player_and_assign(name=f"Player {index + 1}", team=team)
        for index, team in enumerate(teams)
    ]
    competition.status = Competition.Status.KNOCKOUT
    competition.save(update_fields=["status"])
    round_ = Round.objects.create(
        competition=competition,
        stage=Round.Stage.KNOCKOUT,
        number=1,
    )
    match = Match.objects.create(
        round=round_,
        position=1,
        team_a=teams[0],
        team_b=teams[1],
    )
    return MatchSetup(
        competition=competition,
        match=match,
        team_a=teams[0],
        team_b=teams[1],
        team_a_players=[memberships[0]],
        team_b_players=[memberships[1]],
    )


@pytest.mark.django_db
def test_tied_knockout_match_requires_participant_as_winner(db):
    setup = create_knockout_match(db=db)

    with pytest.raises(ValidationError):
        complete_or_correct_match(
            match=setup.match,
            team_a_result=TeamResult(team_id=setup.team_a.id),
            team_b_result=TeamResult(team_id=setup.team_b.id),
        )

    score = complete_or_correct_match(
        match=setup.match,
        team_a_result=TeamResult(team_id=setup.team_a.id),
        team_b_result=TeamResult(team_id=setup.team_b.id),
        shootout_winner_id=setup.team_b.id,
    )

    setup.match.refresh_from_db()
    assert score == MatchScore(team_a=0, team_b=0)
    assert setup.match.shootout_winner == setup.team_b


@pytest.mark.django_db
def test_unequal_knockout_score_rejects_shootout_winner(db):
    setup = create_knockout_match(db=db)

    with pytest.raises(ValidationError) as error:
        complete_or_correct_match(
            match=setup.match,
            team_a_result=TeamResult(
                team_id=setup.team_a.id,
                player_stats=[
                    PlayerStatLine(
                        roster_membership_id=setup.team_a_players[0].id,
                        goals=1,
                    )
                ],
            ),
            team_b_result=TeamResult(team_id=setup.team_b.id),
            shootout_winner_id=setup.team_a.id,
        )

    assert "shootout_winner" in error.value.message_dict


@pytest.mark.django_db
def test_knockout_result_populates_and_corrects_pending_dependents(db):
    setup = create_knockout_match(db=db, team_count=4)
    next_round = Round.objects.create(
        competition=setup.competition,
        stage=Round.Stage.KNOCKOUT,
        number=2,
    )
    final = Match.objects.create(
        round=next_round,
        position=1,
        kind=Match.Kind.FINAL,
        source_match_a=setup.match,
        source_outcome_a=Match.SourceOutcome.WINNER,
    )
    third_place = Match.objects.create(
        round=next_round,
        position=2,
        kind=Match.Kind.THIRD_PLACE,
        source_match_a=setup.match,
        source_outcome_a=Match.SourceOutcome.LOSER,
    )

    complete_or_correct_match(
        match=setup.match,
        team_a_result=TeamResult(
            team_id=setup.team_a.id,
            player_stats=[
                PlayerStatLine(
                    roster_membership_id=setup.team_a_players[0].id,
                    goals=1,
                )
            ],
        ),
        team_b_result=TeamResult(team_id=setup.team_b.id),
    )
    complete_or_correct_match(
        match=setup.match,
        team_a_result=TeamResult(team_id=setup.team_a.id),
        team_b_result=TeamResult(
            team_id=setup.team_b.id,
            player_stats=[
                PlayerStatLine(
                    roster_membership_id=setup.team_b_players[0].id,
                    goals=1,
                )
            ],
        ),
    )

    final.refresh_from_db()
    third_place.refresh_from_db()
    assert final.team_a == setup.team_b
    assert third_place.team_a == setup.team_a


@pytest.mark.django_db
def test_knockout_correction_is_blocked_after_dependent_completion(db):
    setup = create_knockout_match(db=db, team_count=4)
    complete_or_correct_match(
        match=setup.match,
        team_a_result=TeamResult(
            team_id=setup.team_a.id,
            player_stats=[
                PlayerStatLine(
                    roster_membership_id=setup.team_a_players[0].id,
                    goals=1,
                )
            ],
        ),
        team_b_result=TeamResult(team_id=setup.team_b.id),
    )
    next_round = Round.objects.create(
        competition=setup.competition,
        stage=Round.Stage.KNOCKOUT,
        number=2,
    )
    other_team = setup.competition.teams.exclude(
        id__in=[setup.team_a.id, setup.team_b.id]
    ).first()
    assert other_team is not None
    dependent = Match.objects.create(
        round=next_round,
        position=1,
        kind=Match.Kind.FINAL,
        team_a=setup.team_a,
        team_b=other_team,
        source_match_a=setup.match,
        source_outcome_a=Match.SourceOutcome.WINNER,
        status=Match.Status.COMPLETED,
    )

    with pytest.raises(ValidationError):
        complete_or_correct_match(
            match=setup.match,
            team_a_result=TeamResult(team_id=setup.team_a.id),
            team_b_result=TeamResult(
                team_id=setup.team_b.id,
                player_stats=[
                    PlayerStatLine(
                        roster_membership_id=setup.team_b_players[0].id,
                        goals=1,
                    )
                ],
            ),
        )

    assert dependent.status == Match.Status.COMPLETED
    assert get_match_score(setup.match) == MatchScore(team_a=1, team_b=0)


@pytest.mark.django_db
def test_final_completion_completes_competition_without_third_place(db):
    setup = create_knockout_match(db=db)
    setup.match.kind = Match.Kind.FINAL
    setup.match.save(update_fields=["kind"])

    complete_or_correct_match(
        match=setup.match,
        team_a_result=TeamResult(
            team_id=setup.team_a.id,
            player_stats=[
                PlayerStatLine(
                    roster_membership_id=setup.team_a_players[0].id,
                    goals=1,
                )
            ],
        ),
        team_b_result=TeamResult(team_id=setup.team_b.id),
    )

    setup.competition.refresh_from_db()
    assert setup.competition.status == Competition.Status.COMPLETED


@pytest.mark.django_db
def test_enabled_third_place_must_finish_before_competition_completion(db):
    setup = create_knockout_match(db=db, team_count=4)
    knockout_round = setup.match.round
    setup.match.kind = Match.Kind.FINAL
    setup.match.save(update_fields=["kind"])
    remaining_teams = list(
        setup.competition.teams.exclude(
            id__in=[setup.team_a.id, setup.team_b.id]
        ).order_by("id")
    )
    third_place = Match.objects.create(
        round=knockout_round,
        position=2,
        kind=Match.Kind.THIRD_PLACE,
        team_a=remaining_teams[0],
        team_b=remaining_teams[1],
    )
    remaining_memberships = {
        membership.team_id: membership
        for membership in RosterMembership.objects.filter(team__in=remaining_teams)
    }

    complete_or_correct_match(
        match=setup.match,
        team_a_result=TeamResult(
            team_id=setup.team_a.id,
            player_stats=[
                PlayerStatLine(
                    roster_membership_id=setup.team_a_players[0].id,
                    goals=1,
                )
            ],
        ),
        team_b_result=TeamResult(team_id=setup.team_b.id),
    )
    setup.competition.refresh_from_db()
    assert setup.competition.status == Competition.Status.KNOCKOUT

    complete_or_correct_match(
        match=third_place,
        team_a_result=TeamResult(
            team_id=remaining_teams[0].id,
            player_stats=[
                PlayerStatLine(
                    roster_membership_id=remaining_memberships[
                        remaining_teams[0].id
                    ].id,
                    goals=1,
                )
            ],
        ),
        team_b_result=TeamResult(team_id=remaining_teams[1].id),
    )

    setup.competition.refresh_from_db()
    assert setup.competition.status == Competition.Status.COMPLETED
