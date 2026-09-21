import pytest
from django.core.exceptions import ValidationError

from competitions.models import Competition, Player
from competitions.selectors import search_players
from competitions.services import (
    assign_player_to_team,
    create_competition,
    create_player,
    create_team,
    delete_empty_draft_competition,
    delete_unreferenced_player,
    rename_competition,
    rename_team,
)


@pytest.mark.django_db
def test_descriptive_names_can_be_corrected_after_structure_lock():
    competition = create_competition(
        name="Old Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    team_a = create_team(competition=competition, name="Old Team")
    create_team(competition=competition, name="Other")
    competition.status = Competition.Status.COMPLETED
    competition.save(update_fields=["status"])

    rename_competition(competition=competition, name="  New Cup  ")
    rename_team(team=team_a, name="  New Team  ")

    assert competition.name == "New Cup"
    assert team_a.name == "New Team"


@pytest.mark.django_db
def test_team_rename_rejects_blank_duplicate_and_overlong_names():
    competition = create_competition(
        name="Names Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    team_a = create_team(competition=competition, name="A")
    create_team(competition=competition, name="B")

    for invalid_name in ("   ", "x" * 121, "B"):
        with pytest.raises(ValidationError):
            rename_team(team=team_a, name=invalid_name)


@pytest.mark.django_db
def test_only_empty_draft_competition_can_be_deleted():
    competition = create_competition(
        name="Disposable Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    competition_id = competition.id
    delete_empty_draft_competition(competition=competition)
    assert not Competition.objects.filter(id=competition_id).exists()

    competition = create_competition(
        name="Used Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    create_team(competition=competition, name="A")
    with pytest.raises(ValidationError, match="empty draft"):
        delete_empty_draft_competition(competition=competition)


@pytest.mark.django_db
def test_only_unreferenced_global_player_can_be_deleted():
    unreferenced = create_player(name="Unused")
    player_id = unreferenced.id
    delete_unreferenced_player(player=unreferenced)
    assert not Player.objects.filter(id=player_id).exists()

    competition = create_competition(
        name="Player Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    team = create_team(competition=competition, name="A")
    referenced = create_player(name="Used")
    assign_player_to_team(player=referenced, team=team)
    with pytest.raises(ValidationError, match="history references"):
        delete_unreferenced_player(player=referenced)


@pytest.mark.django_db
def test_player_search_uses_name_or_identifier_and_has_a_limit():
    alex = create_player(name="Alex")
    create_player(name="Alexa")
    create_player(name="Blair")

    assert [player.name for player in search_players(query="alex")] == [
        "Alex",
        "Alexa",
    ]
    assert search_players(query=str(alex.id))[0] == alex
    assert len(search_players(limit=2)) == 2


@pytest.mark.django_db
def test_competition_creation_validates_descriptive_fields_and_types():
    base = {
        "name": "Cup",
        "year": 2026,
        "group_count": 1,
        "total_team_count": 2,
        "qualifiers_per_group": 2,
        "third_place_enabled": False,
    }
    for field, value in (
        ("name", "  "),
        ("name", "x" * 121),
        ("year", 0),
        ("year", True),
        ("group_count", True),
        ("total_team_count", "2"),
        ("third_place_enabled", 0),
    ):
        values = {**base, field: value}
        with pytest.raises(ValidationError):
            create_competition(**values)
