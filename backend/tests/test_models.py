import pytest
from django.db import IntegrityError, transaction

from competitions.models import (
    Competition,
    Group,
    GroupMembership,
    Match,
    Player,
    RosterMembership,
    Round,
    Team,
)


@pytest.fixture
def competition(db) -> Competition:
    return Competition.objects.create(
        name="Friends Cup",
        year=2026,
        group_count=1,
        teams_per_group=4,
        qualifiers_per_group=2,
    )


@pytest.fixture
def teams(competition: Competition) -> tuple[Team, Team, Team]:
    return (
        Team.objects.create(competition=competition, name="Green"),
        Team.objects.create(competition=competition, name="Blue"),
        Team.objects.create(competition=competition, name="Red"),
    )


@pytest.mark.django_db
def test_group_label_uses_alphabetic_ordinal(competition: Competition):
    assert Group(competition=competition, ordinal=1).label == "A"
    assert Group(competition=competition, ordinal=27).label == "AA"


@pytest.mark.django_db
def test_team_name_is_unique_within_competition(
    competition: Competition,
    teams: tuple[Team, Team, Team],
):
    with pytest.raises(IntegrityError), transaction.atomic():
        Team.objects.create(competition=competition, name=teams[0].name)


@pytest.mark.django_db
def test_player_can_join_only_one_team_per_competition(
    competition: Competition,
    teams: tuple[Team, Team, Team],
):
    player = Player.objects.create(name="Alex")
    RosterMembership.objects.create(
        competition=competition,
        team=teams[0],
        player=player,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        RosterMembership.objects.create(
            competition=competition,
            team=teams[1],
            player=player,
        )


@pytest.mark.django_db
def test_draw_lots_priority_must_be_positive(
    competition: Competition,
    teams: tuple[Team, Team, Team],
):
    group = Group.objects.create(competition=competition, ordinal=1)

    with pytest.raises(IntegrityError), transaction.atomic():
        GroupMembership.objects.create(
            group=group,
            team=teams[0],
            draw_lots_priority=0,
        )


@pytest.mark.django_db
def test_match_teams_must_differ(
    competition: Competition,
    teams: tuple[Team, Team, Team],
):
    round_ = Round.objects.create(
        competition=competition,
        stage=Round.Stage.GROUP,
        number=1,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Match.objects.create(
            round=round_,
            position=1,
            team_a=teams[0],
            team_b=teams[0],
        )


@pytest.mark.django_db
def test_shootout_winner_must_be_a_participant(
    competition: Competition,
    teams: tuple[Team, Team, Team],
):
    round_ = Round.objects.create(
        competition=competition,
        stage=Round.Stage.KNOCKOUT,
        number=1,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Match.objects.create(
            round=round_,
            position=1,
            team_a=teams[0],
            team_b=teams[1],
            shootout_winner=teams[2],
        )


@pytest.mark.django_db
def test_shootout_winner_requires_populated_participant(
    competition: Competition,
    teams: tuple[Team, Team, Team],
):
    round_ = Round.objects.create(
        competition=competition,
        stage=Round.Stage.KNOCKOUT,
        number=1,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Match.objects.create(
            round=round_,
            position=1,
            shootout_winner=teams[0],
        )
