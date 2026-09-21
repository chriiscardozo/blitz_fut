import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, RequestFactory

from competitions.models import Match
from competitions.services import (
    assign_team_to_group,
    create_competition,
    create_team,
    generate_group_fixtures,
)
from config.security import LoginRateThrottle


def json_request(client: Client, method: str, path: str, payload, *, csrf=None):
    extra = {"HTTP_X_CSRFTOKEN": csrf} if csrf else {}
    return getattr(client, method)(
        path,
        data=payload,
        content_type="application/json",
        **extra,
    )


def logged_in_admin_client(*, username: str = "organizer") -> tuple[Client, str]:
    user_model = get_user_model()
    user_model.objects.create_user(
        username=username,
        password="A-secure-test-password-428!",
        is_staff=True,
    )
    client = Client(enforce_csrf_checks=True)
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    response = json_request(
        client,
        "post",
        "/api/auth/login",
        {"username": username, "password": "A-secure-test-password-428!"},
        csrf=csrf,
    )
    assert response.status_code == 200
    return client, response.json()["csrf_token"]


@pytest.mark.django_db
def test_public_competition_endpoints_are_anonymous_and_read_only():
    competition = create_competition(
        name="Public Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    client = Client()

    listing = client.get("/api/competitions")
    detail = client.get(f"/api/competitions/{competition.id}")
    groups = client.get(f"/api/competitions/{competition.id}/groups")
    teams = client.get(f"/api/competitions/{competition.id}/teams")
    leaderboards = client.get(f"/api/competitions/{competition.id}/leaderboards")

    assert listing.status_code == 200
    assert listing.json()["active"][0]["name"] == "Public Cup"
    assert detail.status_code == 200
    assert detail.json()["competition"]["total_team_count"] == 2
    assert groups.status_code == 200
    assert groups.json()[0]["label"] == "A"
    assert teams.json() == []
    assert leaderboards.json() == {"scorers": [], "assisters": []}


@pytest.mark.django_db
def test_admin_mutations_require_an_authorized_session_and_csrf():
    client = Client(enforce_csrf_checks=True)
    payload = {
        "name": "Admin Cup",
        "year": 2026,
        "group_count": 1,
        "total_team_count": 2,
        "qualifiers_per_group": 2,
        "third_place_enabled": False,
    }
    anonymous_csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    assert (
        json_request(
            client,
            "post",
            "/api/admin/competitions",
            payload,
            csrf=anonymous_csrf,
        ).status_code
        == 401
    )

    client, csrf = logged_in_admin_client()
    assert (
        json_request(client, "post", "/api/admin/competitions", payload).status_code
        == 403
    )
    response = json_request(
        client,
        "post",
        "/api/admin/competitions",
        payload,
        csrf=csrf,
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Admin Cup"


@pytest.mark.django_db
def test_login_requires_csrf_and_returns_generic_failure_for_non_admin():
    user_model = get_user_model()
    user_model.objects.create_user(
        username="visitor",
        password="A-secure-test-password-428!",
    )
    client = Client(enforce_csrf_checks=True)
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]

    without_csrf = json_request(
        client,
        "post",
        "/api/auth/login",
        {"username": "visitor", "password": "wrong"},
    )
    assert without_csrf.status_code == 403

    response = json_request(
        client,
        "post",
        "/api/auth/login",
        {"username": "visitor", "password": "A-secure-test-password-428!"},
        csrf=csrf,
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials."}


@pytest.mark.django_db
def test_session_and_logout_work_for_admin():
    client, csrf = logged_in_admin_client(username="session-admin")
    session = client.get("/api/auth/session")
    assert session.json()["authenticated"] is True
    assert session.json()["is_admin"] is True
    assert session.json()["username"] == "session-admin"

    response = json_request(client, "post", "/api/auth/logout", {}, csrf=csrf)
    assert response.status_code == 200
    assert response.json()["authenticated"] is False


@pytest.mark.django_db
def test_validation_errors_have_a_stable_api_shape():
    client, csrf = logged_in_admin_client(username="validation-admin")
    response = json_request(
        client,
        "post",
        "/api/admin/competitions",
        {
            "name": "Invalid Cup",
            "year": 2026,
            "group_count": 3,
            "total_team_count": 6,
            "qualifiers_per_group": 1,
            "third_place_enabled": False,
        },
        csrf=csrf,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Validation failed."
    assert "group_count" in response.json()["errors"]


@pytest.mark.django_db
def test_match_entry_and_result_endpoints_use_rosters_and_derived_score():
    competition = create_competition(
        name="API Results Cup",
        year=2026,
        group_count=1,
        total_team_count=2,
        qualifiers_per_group=2,
        third_place_enabled=False,
    )
    group = competition.groups.get()
    teams = [
        create_team(competition=competition, name=name) for name in ("A", "B")
    ]
    for team in teams:
        assign_team_to_group(team=team, group=group)
    generate_group_fixtures(competition=competition)
    match = Match.objects.get(round__competition=competition)
    client, csrf = logged_in_admin_client(username="results-admin")

    entry = client.get(f"/api/admin/matches/{match.id}/entry")
    assert entry.status_code == 200
    team_a_id = entry.json()["team_a"]["team"]["id"]
    team_b_id = entry.json()["team_b"]["team"]["id"]
    response = json_request(
        client,
        "put",
        f"/api/admin/matches/{match.id}/result",
        {
            "team_a": {
                "team_id": team_a_id,
                "own_goals_received": 2,
                "player_stats": [],
            },
            "team_b": {
                "team_id": team_b_id,
                "own_goals_received": 0,
                "player_stats": [],
            },
            "shootout_winner_id": None,
        },
        csrf=csrf,
    )
    assert response.status_code == 200
    assert response.json()["match"]["score_a"] == 2
    assert response.json()["match"]["score_b"] == 0


def test_login_throttle_limits_repeated_requests_from_one_address():
    cache.clear()
    throttle = LoginRateThrottle(rate="2/min")
    request = RequestFactory().post("/api/auth/login", REMOTE_ADDR="203.0.113.8")
    assert throttle.allow_request(request)
    assert throttle.allow_request(request)
    assert not throttle.allow_request(request)


def test_openapi_document_contains_public_and_admin_contracts():
    response = Client().get("/api/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/competitions" in paths
    assert "/api/admin/competitions" in paths
    assert "/api/admin/matches/{match_id}/result" in paths
