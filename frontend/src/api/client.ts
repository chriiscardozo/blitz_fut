import type {
  Competition,
  CompetitionDetail,
  CompetitionLists,
  Group,
  Leaderboards,
  MatchEntry,
  Player,
  Round,
  Session,
  Team,
  TeamResultInput,
} from "./types";


let csrfToken: string | null = null;

export class ApiError extends Error {
  readonly status: number;
  readonly errors?: Record<string, string[]>;

  constructor(
    message: string,
    status: number,
    errors?: Record<string, string[]>,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errors = errors;
  }
}

export function setCsrfToken(value: string) {
  csrfToken = value;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method) && csrfToken) {
    headers.set("X-CSRFToken", csrfToken);
  }
  const response = await fetch(`/api${path}`, {
    ...init,
    headers,
    credentials: "same-origin",
  });
  const data = (await response.json().catch(() => null)) as
    | { detail?: string; errors?: Record<string, string[]> }
    | T
    | null;
  if (!response.ok) {
    const failure = data as {
      detail?: string;
      errors?: Record<string, string[]>;
    } | null;
    throw new ApiError(
      failure?.detail ?? `Request failed with status ${response.status}.`,
      response.status,
      failure?.errors,
    );
  }
  return data as T;
}

export const api = {
  async session() {
    const value = await request<Session>("/auth/session");
    setCsrfToken(value.csrf_token);
    return value;
  },
  async login(username: string, password: string) {
    const value = await request<Session>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    setCsrfToken(value.csrf_token);
    return value;
  },
  async logout() {
    const value = await request<Session>("/auth/logout", { method: "POST" });
    setCsrfToken(value.csrf_token);
    return value;
  },
  competitions: () => request<CompetitionLists>("/competitions"),
  competition: (id: number) => request<CompetitionDetail>(`/competitions/${id}`),
  groups: (id: number) => request<Group[]>(`/competitions/${id}/groups`),
  rounds: (id: number) => request<Round[]>(`/competitions/${id}/rounds`),
  teams: (id: number) => request<Team[]>(`/competitions/${id}/teams`),
  leaderboards: (id: number) =>
    request<Leaderboards>(`/competitions/${id}/leaderboards`),
  createCompetition: (payload: {
    name: string;
    year: number;
    group_count: number;
    total_team_count: number;
    qualifiers_per_group: number;
    third_place_enabled: boolean;
  }) => request<Competition>("/admin/competitions", {
    method: "POST", body: JSON.stringify(payload),
  }),
  renameCompetition: (id: number, name: string) =>
    request<Competition>(`/admin/competitions/${id}`, {
      method: "PATCH", body: JSON.stringify({ name }),
    }),
  deleteCompetition: (id: number) =>
    request<{ detail: string }>(`/admin/competitions/${id}`, { method: "DELETE" }),
  createTeam: (competitionId: number, name: string) =>
    request<Team>(`/admin/competitions/${competitionId}/teams`, {
      method: "POST", body: JSON.stringify({ name }),
    }),
  renameTeam: (teamId: number, name: string) =>
    request<Team>(`/admin/teams/${teamId}`, {
      method: "PATCH", body: JSON.stringify({ name }),
    }),
  deleteTeam: (teamId: number) =>
    request<{ detail: string }>(`/admin/teams/${teamId}`, { method: "DELETE" }),
  assignGroup: (teamId: number, groupId: number) =>
    request<Team>(`/admin/teams/${teamId}/group`, {
      method: "PUT", body: JSON.stringify({ group_id: groupId }),
    }),
  randomizeGroups: (competitionId: number) =>
    request<Team[]>(`/admin/competitions/${competitionId}/groups/randomize`, {
      method: "POST",
    }),
  searchPlayers: (query: string) =>
    request<Player[]>(`/admin/players?query=${encodeURIComponent(query)}`),
  createPlayer: (competitionId: number, teamId: number, name: string) =>
    request<Team>(`/admin/competitions/${competitionId}/players`, {
      method: "POST", body: JSON.stringify({ team_id: teamId, name }),
    }),
  assignPlayer: (competitionId: number, teamId: number, playerId: number) =>
    request<Team>(`/admin/competitions/${competitionId}/rosters/assign`, {
      method: "POST", body: JSON.stringify({ team_id: teamId, player_id: playerId }),
    }),
  removeRoster: (membershipId: number) =>
    request<{ detail: string }>(`/admin/rosters/${membershipId}`, { method: "DELETE" }),
  renamePlayer: (playerId: number, name: string) =>
    request<Player>(`/admin/players/${playerId}`, {
      method: "PATCH", body: JSON.stringify({ name }),
    }),
  generateFixtures: (competitionId: number) =>
    request<Round[]>(`/admin/competitions/${competitionId}/fixtures/generate`, {
      method: "POST",
    }),
  returnToSetup: (competitionId: number) =>
    request<{ detail: string }>(`/admin/competitions/${competitionId}/return-to-setup`, {
      method: "POST",
    }),
  matchEntry: (matchId: number) => request<MatchEntry>(`/admin/matches/${matchId}/entry`),
  saveMatchResult: (
    matchId: number,
    teamA: TeamResultInput,
    teamB: TeamResultInput,
    shootoutWinnerId: number | null,
  ) => request<MatchEntry>(`/admin/matches/${matchId}/result`, {
    method: "PUT",
    body: JSON.stringify({
      team_a: teamA, team_b: teamB, shootout_winner_id: shootoutWinnerId,
    }),
  }),
  saveDrawLots: (
    groupId: number,
    priorities: Record<number, number>,
    confirmed: boolean,
  ) => request<Group>(`/admin/groups/${groupId}/draw-lots`, {
    method: "PUT", body: JSON.stringify({ priorities, confirmed }),
  }),
  finalizeGroups: (competitionId: number) =>
    request<Round[]>(`/admin/competitions/${competitionId}/finalize-group-stage`, {
      method: "POST", body: JSON.stringify({ confirmed: true }),
    }),
  reopenGroups: (competitionId: number) =>
    request<{ detail: string }>(`/admin/competitions/${competitionId}/reopen-group-stage`, {
      method: "POST",
    }),
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const validation = error.errors ? Object.values(error.errors).flat()[0] : undefined;
    return validation ?? error.message;
  }
  return error instanceof Error ? error.message : "Something went wrong.";
}
