"""Transactional commands and validation for competition state changes."""

from competitions.services.competition_configuration import (
    validate_competition_configuration,
)
from competitions.services.competition_creation import create_competition
from competitions.services.draft_setup import (
    assign_team_to_group,
    create_team,
    delete_team,
    randomize_group_assignments,
)
from competitions.services.draw_lots import save_draw_lots_priorities
from competitions.services.rosters import (
    assign_player_to_team,
    create_player,
    create_player_and_assign,
    remove_player_from_roster,
    rename_player,
)
from competitions.services.group_fixtures import (
    build_round_robin,
    generate_group_fixtures,
    return_to_setup,
)
from competitions.services.match_results import (
    PlayerStatLine,
    TeamResult,
    complete_or_correct_match,
)
from competitions.services.knockout import (
    build_knockout_team_order,
    finalize_group_stage,
    reopen_group_stage,
    seed_slots,
)
from competitions.services.management import (
    delete_competition,
    delete_unreferenced_player,
    rename_competition,
    rename_team,
)


__all__ = [
    "assign_team_to_group",
    "assign_player_to_team",
    "complete_or_correct_match",
    "create_competition",
    "create_player",
    "create_player_and_assign",
    "create_team",
    "delete_team",
    "delete_competition",
    "delete_unreferenced_player",
    "build_round_robin",
    "build_knockout_team_order",
    "finalize_group_stage",
    "generate_group_fixtures",
    "randomize_group_assignments",
    "PlayerStatLine",
    "remove_player_from_roster",
    "rename_player",
    "rename_competition",
    "rename_team",
    "reopen_group_stage",
    "return_to_setup",
    "save_draw_lots_priorities",
    "seed_slots",
    "TeamResult",
    "validate_competition_configuration",
]
