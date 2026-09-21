import { useEffect, useState } from "react";
import {
  Alert, Box, Button, Card, CardContent, Stack, Tab, Tabs, Typography,
} from "@mui/material";
import { Link, useParams } from "react-router";

import { api, errorMessage } from "../api/client";
import type { CompetitionDetail, Group, Leaderboards, Round, Team } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { GroupTable } from "../components/GroupTable";
import { LeaderboardTable } from "../components/LeaderboardTable";
import { KnockoutBracket, RoundList } from "../components/Matches";
import { ErrorState, LoadingState } from "../components/PageState";
import { StatusChip } from "../components/StatusChip";

type PageData = { detail: CompetitionDetail; groups: Group[]; rounds: Round[]; teams: Team[]; leaderboards: Leaderboards };

export function CompetitionPage() {
  const id = Number(useParams().competitionId);
  const { session } = useAuth();
  const [data, setData] = useState<PageData | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState(0);
  useEffect(() => {
    Promise.all([api.competition(id), api.groups(id), api.rounds(id), api.teams(id), api.leaderboards(id)])
      .then(([detail, groups, rounds, teams, leaderboards]) => setData({ detail, groups, rounds, teams, leaderboards }))
      .catch((value) => setError(errorMessage(value)));
  }, [id]);
  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Loading competition…" />;
  const competition = data.detail.competition;
  const groupRounds = data.rounds.filter((round) => round.stage === "GROUP");
  const knockoutRounds = data.rounds.filter((round) => round.stage === "KNOCKOUT");
  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} sx={{ justifyContent: "space-between", gap: 2, alignItems: { sm: "flex-start" } }}>
        <Box>
          <Stack direction="row" sx={{ gap: 1.5, alignItems: "center", flexWrap: "wrap" }}>
            <Typography variant="h2" sx={{ fontSize: { xs: "2.2rem", md: "3.4rem" } }}>{competition.name}</Typography>
            <StatusChip status={competition.status} />
          </Stack>
          <Typography color="text.secondary">{competition.year} · {competition.total_team_count} teams</Typography>
        </Box>
        {session?.is_admin && <Button component={Link} variant="outlined" to={`/admin/competitions/${id}`}>Manage competition</Button>}
      </Stack>
      {data.detail.champion && <Alert severity="success"><strong>{data.detail.champion.name}</strong> are the champions.</Alert>}
      <Tabs value={tab} onChange={(_, value: number) => setTab(value)} variant="scrollable" scrollButtons="auto" aria-label="Competition sections">
        <Tab label="Groups" /><Tab label="Matches" /><Tab label="Knockout" /><Tab label="Statistics" /><Tab label="Teams" />
      </Tabs>
      {tab === 0 && <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" }, gap: 2 }}>{data.groups.map((group) => <GroupTable key={group.id} group={group} />)}</Box>}
      {tab === 1 && (groupRounds.length ? <RoundList rounds={groupRounds} /> : <Alert severity="info">Fixtures have not been generated yet.</Alert>)}
      {tab === 2 && (knockoutRounds.length ? <KnockoutBracket rounds={knockoutRounds} /> : <Alert severity="info">The knockout bracket will appear after the group stage is finalized.</Alert>)}
      {tab === 3 && <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}><LeaderboardTable title="Top scorers" rows={data.leaderboards.scorers} /><LeaderboardTable title="Top assisters" rows={data.leaderboards.assisters} /></Box>}
      {tab === 4 && <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>{data.teams.map((team) => <Card key={team.id}><CardContent><Typography variant="h6">{team.name}</Typography><Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{team.group_label ? `Group ${team.group_label}` : "Not assigned"}</Typography>{team.roster.length ? team.roster.map((membership) => <Typography key={membership.id}>{membership.player.name}</Typography>) : <Typography color="text.secondary">No players yet.</Typography>}</CardContent></Card>)}</Box>}
    </Stack>
  );
}
