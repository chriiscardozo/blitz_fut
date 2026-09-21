"""Pydantic and Django Ninja schemas for competition API boundaries."""

from ninja import Schema
from pydantic import Field


class MessageOut(Schema):
    detail: str


class CompetitionCreateIn(Schema):
    name: str = Field(min_length=1, max_length=120)
    year: int = Field(ge=1, le=32_767)
    group_count: int = Field(ge=1, le=32_767)
    total_team_count: int = Field(ge=2, le=32_767)
    qualifiers_per_group: int = Field(ge=1, le=32_767)
    third_place_enabled: bool = False


class NameIn(Schema):
    name: str = Field(min_length=1, max_length=120)


class ConfirmationIn(Schema):
    confirmed: bool


class CompetitionDeletionIn(Schema):
    confirmed_name: str = Field(min_length=1, max_length=120)


class CompetitionOut(Schema):
    id: int
    name: str
    year: int
    status: str
    group_count: int
    teams_per_group: int
    total_team_count: int
    qualifiers_per_group: int
    knockout_team_count: int
    third_place_enabled: bool


class CompetitionListsOut(Schema):
    active: list[CompetitionOut]
    past: list[CompetitionOut]


class TeamBriefOut(Schema):
    id: int
    name: str


class PlayerOut(Schema):
    id: int
    name: str


class RosterMembershipOut(Schema):
    id: int
    player: PlayerOut


class TeamOut(Schema):
    id: int
    name: str
    group_id: int | None
    group_label: str | None
    roster: list[RosterMembershipOut]


class GroupAssignmentIn(Schema):
    group_id: int = Field(ge=1)


class ExistingPlayerAssignmentIn(Schema):
    player_id: int = Field(ge=1)
    team_id: int = Field(ge=1)


class NewPlayerAssignmentIn(Schema):
    name: str = Field(min_length=1, max_length=120)
    team_id: int = Field(ge=1)


class StandingRowOut(Schema):
    position: int
    team_id: int
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    head_to_head_points: int
    head_to_head_goal_difference: int
    head_to_head_goals_for: int
    draw_lots_priority: int | None
    unresolved_tie: bool
    qualifies: bool


class GroupOut(Schema):
    id: int
    ordinal: int
    label: str
    standings_resolved: bool
    unresolved_ties: list[list[int]]
    standings: list[StandingRowOut]


class MatchOut(Schema):
    id: int
    stage: str
    round_number: int
    round_name: str
    group_id: int | None
    group_label: str | None
    position: int
    kind: str
    status: str
    team_a: TeamBriefOut | None
    team_b: TeamBriefOut | None
    score_a: int | None
    score_b: int | None
    shootout_winner_id: int | None


class RoundOut(Schema):
    id: int
    stage: str
    number: int
    name: str
    matches: list[MatchOut]


class LeaderboardRowOut(Schema):
    rank: int
    player_id: int
    player_name: str
    team_id: int
    team_name: str
    total: int


class LeaderboardsOut(Schema):
    scorers: list[LeaderboardRowOut]
    assisters: list[LeaderboardRowOut]


class CompetitionLocksOut(Schema):
    structure_locked: bool
    roster_locked: bool
    can_return_to_setup: bool
    can_finalize_group_stage: bool
    can_reopen_group_stage: bool


class CompetitionDetailOut(Schema):
    competition: CompetitionOut
    champion: TeamBriefOut | None
    third_place_finisher: TeamBriefOut | None
    locks: CompetitionLocksOut


class DrawLotsIn(Schema):
    priorities: dict[int, int]
    confirmed: bool


class PlayerStatLineIn(Schema):
    roster_membership_id: int = Field(ge=1)
    goals: int = Field(default=0, ge=0, le=32_767)
    assists: int = Field(default=0, ge=0, le=32_767)


class TeamResultIn(Schema):
    team_id: int = Field(ge=1)
    own_goals_received: int = Field(default=0, ge=0, le=32_767)
    player_stats: list[PlayerStatLineIn] = Field(default_factory=list)


class MatchResultIn(Schema):
    team_a: TeamResultIn
    team_b: TeamResultIn
    shootout_winner_id: int | None = Field(default=None, ge=1)


class MatchPlayerEntryOut(Schema):
    roster_membership_id: int
    player_id: int
    player_name: str
    goals: int
    assists: int


class MatchTeamEntryOut(Schema):
    team: TeamBriefOut
    own_goals_received: int
    players: list[MatchPlayerEntryOut]


class MatchEntryOut(Schema):
    match: MatchOut
    team_a: MatchTeamEntryOut
    team_b: MatchTeamEntryOut
