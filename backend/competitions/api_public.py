from django.shortcuts import get_object_or_404
from ninja import Router

from competitions.api_serializers import (
    competition_data,
    competition_detail_data,
    group_data,
    leaderboards_data,
    round_data,
    team_data,
)
from competitions.models import Competition
from competitions.schemas import (
    CompetitionDetailOut,
    CompetitionListsOut,
    GroupOut,
    LeaderboardsOut,
    RoundOut,
    TeamOut,
)


router = Router(tags=["Public competitions"])


@router.get("/competitions", response=CompetitionListsOut, auth=None)
def list_competitions(request):
    competitions = Competition.objects.order_by("-year", "name", "id")
    return {
        "active": [
            competition_data(competition)
            for competition in competitions
            if competition.status != Competition.Status.COMPLETED
        ],
        "past": [
            competition_data(competition)
            for competition in competitions
            if competition.status == Competition.Status.COMPLETED
        ],
    }


@router.get(
    "/competitions/{competition_id}",
    response=CompetitionDetailOut,
    auth=None,
)
def get_competition(request, competition_id: int):
    competition = get_object_or_404(Competition, id=competition_id)
    return competition_detail_data(competition)


@router.get(
    "/competitions/{competition_id}/groups",
    response=list[GroupOut],
    auth=None,
)
def list_groups(request, competition_id: int):
    competition = get_object_or_404(Competition, id=competition_id)
    return [group_data(group) for group in competition.groups.order_by("ordinal")]


@router.get(
    "/competitions/{competition_id}/rounds",
    response=list[RoundOut],
    auth=None,
)
def list_rounds(request, competition_id: int):
    competition = get_object_or_404(Competition, id=competition_id)
    return [
        round_data(round_)
        for round_ in competition.rounds.order_by("stage", "number")
    ]


@router.get(
    "/competitions/{competition_id}/teams",
    response=list[TeamOut],
    auth=None,
)
def list_teams(request, competition_id: int):
    competition = get_object_or_404(Competition, id=competition_id)
    teams = competition.teams.select_related("group_membership__group").order_by(
        "name", "id"
    )
    return [team_data(team) for team in teams]


@router.get(
    "/competitions/{competition_id}/leaderboards",
    response=LeaderboardsOut,
    auth=None,
)
def get_leaderboards(request, competition_id: int):
    competition = get_object_or_404(Competition, id=competition_id)
    return leaderboards_data(competition)
