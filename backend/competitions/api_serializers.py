from competitions.models import Competition, Group, Match, Round, Team
from competitions.selectors import (
    calculate_group_standings,
    get_champion,
    get_competition_locks,
    get_knockout_round_name,
    get_match_score,
    get_player_leaderboards,
    get_third_place_finisher,
)


def competition_data(competition: Competition) -> dict[str, object]:
    return {
        "id": competition.id,
        "name": competition.name,
        "year": competition.year,
        "status": competition.status,
        "group_count": competition.group_count,
        "teams_per_group": competition.teams_per_group,
        "total_team_count": competition.total_team_count,
        "qualifiers_per_group": competition.qualifiers_per_group,
        "knockout_team_count": (
            competition.group_count * competition.qualifiers_per_group
        ),
        "third_place_enabled": competition.third_place_enabled,
    }


def team_brief_data(team: Team | None) -> dict[str, object] | None:
    if team is None:
        return None
    return {"id": team.id, "name": team.name}


def competition_detail_data(competition: Competition) -> dict[str, object]:
    champion = get_champion(competition)
    third_place = get_third_place_finisher(competition)
    locks = get_competition_locks(competition)
    return {
        "competition": competition_data(competition),
        "champion": team_brief_data(champion),
        "third_place_finisher": team_brief_data(third_place),
        "locks": {
            "structure_locked": locks.structure_locked,
            "roster_locked": locks.roster_locked,
            "can_return_to_setup": locks.can_return_to_setup,
            "can_finalize_group_stage": locks.can_finalize_group_stage,
            "can_reopen_group_stage": locks.can_reopen_group_stage,
        },
    }


def group_data(group: Group) -> dict[str, object]:
    standings = calculate_group_standings(group)
    return {
        "id": group.id,
        "ordinal": group.ordinal,
        "label": group.label,
        "standings_resolved": standings.is_resolved,
        "unresolved_ties": [list(cohort.team_ids) for cohort in standings.unresolved_ties],
        "standings": [
            {
                "position": row.position,
                "team_id": row.team_id,
                "team_name": row.team_name,
                "played": row.played,
                "wins": row.wins,
                "draws": row.draws,
                "losses": row.losses,
                "goals_for": row.goals_for,
                "goals_against": row.goals_against,
                "goal_difference": row.goal_difference,
                "points": row.points,
                "head_to_head_points": row.head_to_head_points,
                "head_to_head_goal_difference": row.head_to_head_goal_difference,
                "head_to_head_goals_for": row.head_to_head_goals_for,
                "draw_lots_priority": row.draw_lots_priority,
                "unresolved_tie": row.unresolved_tie,
                "qualifies": row.qualifies,
            }
            for row in standings.rows
        ],
    }


def round_name(round_: Round) -> str:
    if round_.stage == Round.Stage.GROUP:
        return f"Matchday {round_.number}"
    return get_knockout_round_name(round_)


def match_data(match: Match) -> dict[str, object]:
    score = get_match_score(match) if match.status == Match.Status.COMPLETED else None
    return {
        "id": match.id,
        "stage": match.round.stage,
        "round_number": match.round.number,
        "round_name": round_name(match.round),
        "group_id": match.group_id,
        "group_label": match.group.label if match.group_id else None,
        "position": match.position,
        "kind": match.kind,
        "status": match.status,
        "team_a": team_brief_data(match.team_a),
        "team_b": team_brief_data(match.team_b),
        "score_a": score.team_a if score else None,
        "score_b": score.team_b if score else None,
        "shootout_winner_id": match.shootout_winner_id,
    }


def round_data(round_: Round) -> dict[str, object]:
    matches = round_.matches.select_related(
        "round", "group", "team_a", "team_b", "shootout_winner"
    ).order_by("position")
    return {
        "id": round_.id,
        "stage": round_.stage,
        "number": round_.number,
        "name": round_name(round_),
        "matches": [match_data(match) for match in matches],
    }


def team_data(team: Team) -> dict[str, object]:
    membership = getattr(team, "group_membership", None)
    roster = team.roster_memberships.select_related("player").order_by(
        "player__name", "id"
    )
    return {
        "id": team.id,
        "name": team.name,
        "group_id": membership.group_id if membership else None,
        "group_label": membership.group.label if membership else None,
        "roster": [
            {
                "id": row.id,
                "player": {"id": row.player_id, "name": row.player.name},
            }
            for row in roster
        ],
    }


def leaderboards_data(competition: Competition) -> dict[str, object]:
    leaderboards = get_player_leaderboards(competition)

    def rows_data(rows):
        return [
            {
                "rank": row.rank,
                "player_id": row.player_id,
                "player_name": row.player_name,
                "team_id": row.team_id,
                "team_name": row.team_name,
                "total": row.total,
            }
            for row in rows
        ]

    return {
        "scorers": rows_data(leaderboards.scorers),
        "assisters": rows_data(leaderboards.assisters),
    }


def match_entry_data(match: Match) -> dict[str, object]:
    if match.team_a_id is None or match.team_b_id is None:
        raise ValueError("Both participants are required for result entry.")
    existing_player_stats = {
        row.roster_membership_id: row
        for row in match.player_stats.select_related("roster_membership").all()
    }
    existing_team_stats = {row.team_id: row for row in match.team_stats.all()}

    def entry_for_team(team: Team) -> dict[str, object]:
        memberships = team.roster_memberships.select_related("player").order_by(
            "player__name", "id"
        )
        return {
            "team": team_brief_data(team),
            "own_goals_received": getattr(
                existing_team_stats.get(team.id), "own_goals_received", 0
            ),
            "players": [
                {
                    "roster_membership_id": membership.id,
                    "player_id": membership.player_id,
                    "player_name": membership.player.name,
                    "goals": getattr(
                        existing_player_stats.get(membership.id), "goals", 0
                    ),
                    "assists": getattr(
                        existing_player_stats.get(membership.id), "assists", 0
                    ),
                }
                for membership in memberships
            ],
        }

    return {
        "match": match_data(match),
        "team_a": entry_for_team(match.team_a),
        "team_b": entry_for_team(match.team_b),
    }
