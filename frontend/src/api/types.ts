export type CompetitionStatus =
  | "DRAFT"
  | "GROUP_STAGE"
  | "KNOCKOUT"
  | "COMPLETED";

export type Competition = {
  id: number;
  name: string;
  year: number;
  status: CompetitionStatus;
  group_count: number;
  teams_per_group: number;
  total_team_count: number;
  qualifiers_per_group: number;
  knockout_team_count: number;
  third_place_enabled: boolean;
};

export type CompetitionLists = {
  active: Competition[];
  past: Competition[];
};

export type TeamBrief = { id: number; name: string };
export type Player = { id: number; name: string };
export type RosterMembership = { id: number; player: Player };

export type Team = {
  id: number;
  name: string;
  group_id: number | null;
  group_label: string | null;
  roster: RosterMembership[];
};

export type StandingRow = {
  position: number;
  team_id: number;
  team_name: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  points: number;
  head_to_head_points: number;
  head_to_head_goal_difference: number;
  head_to_head_goals_for: number;
  draw_lots_priority: number | null;
  unresolved_tie: boolean;
  qualifies: boolean;
};

export type Group = {
  id: number;
  ordinal: number;
  label: string;
  standings_resolved: boolean;
  unresolved_ties: number[][];
  standings: StandingRow[];
};

export type Match = {
  id: number;
  stage: "GROUP" | "KNOCKOUT";
  round_number: number;
  round_name: string;
  group_id: number | null;
  group_label: string | null;
  position: number;
  kind: "REGULAR" | "FINAL" | "THIRD_PLACE";
  status: "PENDING" | "COMPLETED";
  team_a: TeamBrief | null;
  team_b: TeamBrief | null;
  score_a: number | null;
  score_b: number | null;
  shootout_winner_id: number | null;
};

export type Round = {
  id: number;
  stage: "GROUP" | "KNOCKOUT";
  number: number;
  name: string;
  matches: Match[];
};

export type LeaderboardRow = {
  rank: number;
  player_id: number;
  player_name: string;
  team_id: number;
  team_name: string;
  total: number;
};

export type Leaderboards = {
  scorers: LeaderboardRow[];
  assisters: LeaderboardRow[];
};

export type CompetitionLocks = {
  structure_locked: boolean;
  roster_locked: boolean;
  can_return_to_setup: boolean;
  can_finalize_group_stage: boolean;
  can_reopen_group_stage: boolean;
};

export type CompetitionDetail = {
  competition: Competition;
  champion: TeamBrief | null;
  third_place_finisher: TeamBrief | null;
  locks: CompetitionLocks;
};

export type Session = {
  authenticated: boolean;
  is_admin: boolean;
  username: string | null;
  csrf_token: string;
};

export type MatchPlayerEntry = {
  roster_membership_id: number;
  player_id: number;
  player_name: string;
  goals: number;
  assists: number;
};

export type MatchTeamEntry = {
  team: TeamBrief;
  own_goals_received: number;
  players: MatchPlayerEntry[];
};

export type MatchEntry = {
  match: Match;
  team_a: MatchTeamEntry;
  team_b: MatchTeamEntry;
};

export type TeamResultInput = {
  team_id: number;
  own_goals_received: number;
  player_stats: Array<{
    roster_membership_id: number;
    goals: number;
    assists: number;
  }>;
};
