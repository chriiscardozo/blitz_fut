from django.shortcuts import get_object_or_404
from ninja import Router, Status
from ninja.errors import HttpError

from competitions.api_serializers import (
    competition_data,
    group_data,
    match_entry_data,
    round_data,
    team_data,
)
from competitions.models import (
    Competition,
    Group,
    Match,
    Player,
    RosterMembership,
    Team,
)
from competitions.schemas import (
    CompetitionCreateIn,
    CompetitionOut,
    ConfirmationIn,
    DrawLotsIn,
    ExistingPlayerAssignmentIn,
    GroupAssignmentIn,
    GroupOut,
    MatchEntryOut,
    MatchResultIn,
    MessageOut,
    NameIn,
    NewPlayerAssignmentIn,
    PlayerOut,
    RoundOut,
    TeamOut,
)
from competitions.selectors import search_players
from competitions.services import (
    PlayerStatLine,
    TeamResult,
    assign_player_to_team,
    assign_team_to_group,
    complete_or_correct_match,
    create_competition,
    create_player_and_assign,
    create_team,
    delete_empty_draft_competition,
    delete_team,
    delete_unreferenced_player,
    finalize_group_stage,
    generate_group_fixtures,
    randomize_group_assignments,
    remove_player_from_roster,
    rename_competition,
    rename_player,
    rename_team,
    reopen_group_stage,
    return_to_setup,
    save_draw_lots_priorities,
)
from config.security import admin_auth


router = Router(tags=["Administration"], auth=admin_auth)


def _competition(competition_id: int) -> Competition:
    return get_object_or_404(Competition, id=competition_id)


@router.post("/admin/competitions", response={201: CompetitionOut})
def create_competition_endpoint(request, payload: CompetitionCreateIn):
    competition = create_competition(**payload.model_dump())
    return Status(201, competition_data(competition))


@router.patch(
    "/admin/competitions/{competition_id}",
    response=CompetitionOut,
)
def rename_competition_endpoint(request, competition_id: int, payload: NameIn):
    competition = rename_competition(
        competition=_competition(competition_id),
        name=payload.name,
    )
    return competition_data(competition)


@router.delete(
    "/admin/competitions/{competition_id}",
    response=MessageOut,
)
def delete_competition_endpoint(request, competition_id: int):
    delete_empty_draft_competition(competition=_competition(competition_id))
    return {"detail": "Competition deleted."}


@router.post(
    "/admin/competitions/{competition_id}/teams",
    response={201: TeamOut},
)
def create_team_endpoint(request, competition_id: int, payload: NameIn):
    team = create_team(competition=_competition(competition_id), name=payload.name)
    return Status(201, team_data(team))


@router.patch("/admin/teams/{team_id}", response=TeamOut)
def rename_team_endpoint(request, team_id: int, payload: NameIn):
    team = rename_team(team=get_object_or_404(Team, id=team_id), name=payload.name)
    return team_data(team)


@router.delete("/admin/teams/{team_id}", response=MessageOut)
def delete_team_endpoint(request, team_id: int):
    delete_team(team=get_object_or_404(Team, id=team_id))
    return {"detail": "Team deleted."}


@router.put("/admin/teams/{team_id}/group", response=TeamOut)
def assign_group_endpoint(
    request,
    team_id: int,
    payload: GroupAssignmentIn,
):
    team = get_object_or_404(Team, id=team_id)
    group = get_object_or_404(Group, id=payload.group_id)
    assign_team_to_group(team=team, group=group)
    team = Team.objects.select_related("group_membership__group").get(id=team.id)
    return team_data(team)


@router.post(
    "/admin/competitions/{competition_id}/groups/randomize",
    response=list[TeamOut],
)
def randomize_groups_endpoint(request, competition_id: int):
    competition = _competition(competition_id)
    randomize_group_assignments(competition=competition)
    teams = competition.teams.select_related("group_membership__group").order_by(
        "name", "id"
    )
    return [team_data(team) for team in teams]


@router.get("/admin/players", response=list[PlayerOut])
def search_players_endpoint(request, query: str = ""):
    return [
        {"id": player.id, "name": player.name}
        for player in search_players(query=query)
    ]


@router.post(
    "/admin/competitions/{competition_id}/players",
    response={201: TeamOut},
)
def create_player_endpoint(
    request,
    competition_id: int,
    payload: NewPlayerAssignmentIn,
):
    team = get_object_or_404(
        Team,
        id=payload.team_id,
        competition_id=competition_id,
    )
    create_player_and_assign(name=payload.name, team=team)
    return Status(201, team_data(team))


@router.post(
    "/admin/competitions/{competition_id}/rosters/assign",
    response=TeamOut,
)
def assign_player_endpoint(
    request,
    competition_id: int,
    payload: ExistingPlayerAssignmentIn,
):
    player = get_object_or_404(Player, id=payload.player_id)
    team = get_object_or_404(
        Team,
        id=payload.team_id,
        competition_id=competition_id,
    )
    assign_player_to_team(player=player, team=team)
    return team_data(team)


@router.delete("/admin/rosters/{membership_id}", response=MessageOut)
def remove_roster_endpoint(request, membership_id: int):
    membership = get_object_or_404(RosterMembership, id=membership_id)
    remove_player_from_roster(membership=membership)
    return {"detail": "Player removed from the roster."}


@router.patch("/admin/players/{player_id}", response=PlayerOut)
def rename_player_endpoint(request, player_id: int, payload: NameIn):
    player = rename_player(
        player=get_object_or_404(Player, id=player_id),
        name=payload.name,
    )
    return {"id": player.id, "name": player.name}


@router.delete("/admin/players/{player_id}", response=MessageOut)
def delete_player_endpoint(request, player_id: int):
    delete_unreferenced_player(player=get_object_or_404(Player, id=player_id))
    return {"detail": "Player deleted."}


@router.post(
    "/admin/competitions/{competition_id}/fixtures/generate",
    response=list[RoundOut],
)
def generate_fixtures_endpoint(request, competition_id: int):
    rounds = generate_group_fixtures(competition=_competition(competition_id))
    return [round_data(round_) for round_ in rounds]


@router.post(
    "/admin/competitions/{competition_id}/return-to-setup",
    response=MessageOut,
)
def return_to_setup_endpoint(request, competition_id: int):
    return_to_setup(competition=_competition(competition_id))
    return {"detail": "Competition returned to draft setup."}


def _match(match_id: int) -> Match:
    return get_object_or_404(
        Match.objects.select_related(
            "round__competition",
            "group",
            "team_a",
            "team_b",
            "shootout_winner",
        ),
        id=match_id,
    )


@router.get("/admin/matches/{match_id}/entry", response=MatchEntryOut)
def get_match_entry_endpoint(request, match_id: int):
    match = _match(match_id)
    if match.team_a_id is None or match.team_b_id is None:
        raise HttpError(409, "This match does not have both participants yet.")
    return match_entry_data(match)


@router.put("/admin/matches/{match_id}/result", response=MatchEntryOut)
def save_match_result_endpoint(request, match_id: int, payload: MatchResultIn):
    match = _match(match_id)

    def team_result(value) -> TeamResult:
        return TeamResult(
            team_id=value.team_id,
            own_goals_received=value.own_goals_received,
            player_stats=tuple(
                PlayerStatLine(
                    roster_membership_id=line.roster_membership_id,
                    goals=line.goals,
                    assists=line.assists,
                )
                for line in value.player_stats
            ),
        )

    complete_or_correct_match(
        match=match,
        team_a_result=team_result(payload.team_a),
        team_b_result=team_result(payload.team_b),
        shootout_winner_id=payload.shootout_winner_id,
    )
    match.refresh_from_db()
    return match_entry_data(_match(match.id))


@router.put("/admin/groups/{group_id}/draw-lots", response=GroupOut)
def save_draw_lots_endpoint(request, group_id: int, payload: DrawLotsIn):
    group = get_object_or_404(Group.objects.select_related("competition"), id=group_id)
    save_draw_lots_priorities(
        group=group,
        priorities=payload.priorities,
        confirmed=payload.confirmed,
    )
    return group_data(group)


@router.post(
    "/admin/competitions/{competition_id}/finalize-group-stage",
    response=list[RoundOut],
)
def finalize_group_stage_endpoint(
    request,
    competition_id: int,
    payload: ConfirmationIn,
):
    rounds = finalize_group_stage(
        competition=_competition(competition_id),
        confirmed=payload.confirmed,
    )
    return [round_data(round_) for round_ in rounds]


@router.post(
    "/admin/competitions/{competition_id}/reopen-group-stage",
    response=MessageOut,
)
def reopen_group_stage_endpoint(request, competition_id: int):
    reopen_group_stage(competition=_competition(competition_id))
    return {"detail": "Group stage reopened."}
