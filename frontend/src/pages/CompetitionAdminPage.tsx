import { useCallback, useEffect, useState } from "react";
import {
  Alert, Box, Button, Snackbar, Stack, TextField, Typography,
} from "@mui/material";
import { Link, useNavigate, useParams } from "react-router";

import { DraftSetup } from "../admin/DraftSetup";
import { DrawLotsEditor } from "../admin/DrawLotsEditor";
import { RosterEditor } from "../admin/RosterEditor";
import { api, errorMessage } from "../api/client";
import type { CompetitionDetail, Group, Round, Team } from "../api/types";
import { ConfirmAction } from "../components/ConfirmAction";
import { GroupTable } from "../components/GroupTable";
import { KnockoutBracket, RoundList } from "../components/Matches";
import { ErrorState, LoadingState } from "../components/PageState";
import { StatusChip } from "../components/StatusChip";

type AdminData = { detail: CompetitionDetail; groups: Group[]; rounds: Round[]; teams: Team[] };

export function CompetitionAdminPage() {
  const id = Number(useParams().competitionId);
  const navigate = useNavigate();
  const [data, setData] = useState<AdminData | null>(null);
  const [pageError, setPageError] = useState("");
  const [actionError, setActionError] = useState("");
  const [notice, setNotice] = useState("");
  const [name, setName] = useState("");

  const load = useCallback(async () => {
    const [detail, groups, rounds, teams] = await Promise.all([
      api.competition(id), api.groups(id), api.rounds(id), api.teams(id),
    ]);
    setData({ detail, groups, rounds, teams });
    setName(detail.competition.name);
  }, [id]);

  useEffect(() => { load().catch((value) => setPageError(errorMessage(value))); }, [load]);

  const run = useCallback(async (operation: () => Promise<unknown>, success: string) => {
    setActionError("");
    try { await operation(); await load(); setNotice(success); }
    catch (value) { setActionError(errorMessage(value)); }
  }, [load]);

  if (pageError) return <ErrorState message={pageError} />;
  if (!data) return <LoadingState label="Loading administration…" />;
  const competition = data.detail.competition;
  const groupRounds = data.rounds.filter((round) => round.stage === "GROUP");
  const knockoutRounds = data.rounds.filter((round) => round.stage === "KNOCKOUT");
  const allGroupMatchesComplete = groupRounds.length > 0 && groupRounds.every(
    (round) => round.matches.every((match) => match.status === "COMPLETED"),
  );

  async function deleteCompetition() {
    try { await api.deleteCompetition(id); navigate("/admin"); }
    catch (value) { setActionError(errorMessage(value)); }
  }

  return (
    <Stack spacing={4}>
      <Stack direction={{ xs: "column", md: "row" }} sx={{ justifyContent: "space-between", gap: 2, alignItems: { md: "flex-start" } }}>
        <Box sx={{ flex: 1 }}>
          <Stack direction="row" sx={{ gap: 1.5, alignItems: "center", flexWrap: "wrap" }}>
            <TextField
              value={name}
              onChange={(event) => setName(event.target.value)}
              variant="standard"
              slotProps={{ htmlInput: { "aria-label": "Competition name" } }}
              sx={{ maxWidth: 520, "& input": { fontSize: { xs: "2rem", md: "3rem" }, fontWeight: 800, letterSpacing: "-0.04em" } }}
            />
            <StatusChip status={competition.status} />
          </Stack>
          <Stack direction="row" sx={{ gap: 1, alignItems: "center", mt: 1 }}>
            <Typography color="text.secondary">{competition.year} · {competition.total_team_count} teams</Typography>
            <Button size="small" disabled={!name.trim() || name.trim() === competition.name} onClick={() => void run(() => api.renameCompetition(id, name), "Competition name updated.")}>Save name</Button>
          </Stack>
        </Box>
        <Button component={Link} to={`/competitions/${id}`} variant="outlined">View public page</Button>
      </Stack>

      {actionError && <Alert severity="error" onClose={() => setActionError("")}>{actionError}</Alert>}

      {competition.status === "DRAFT" && (
        <>
          <DraftSetup competition={competition} groups={data.groups} teams={data.teams} run={run} />
          {data.teams.length === 0 && (
            <Box sx={{ borderTop: 1, borderColor: "divider", pt: 2 }}>
              <ConfirmAction label="Delete empty draft" title="Delete this competition?" description="This empty draft and its configuration will be permanently removed." confirmLabel="Delete competition" color="error" onConfirm={deleteCompetition} />
            </Box>
          )}
        </>
      )}

      {competition.status === "GROUP_STAGE" && (
        <Stack spacing={4}>
          <Stack direction={{ xs: "column", sm: "row" }} sx={{ gap: 1 }}>
            <ConfirmAction
              label="Return to setup" title="Return to setup?"
              description="All pending group fixtures will be removed. This is allowed only before the first completed result."
              disabled={!data.detail.locks.can_return_to_setup}
              onConfirm={() => run(() => api.returnToSetup(id), "Returned to draft setup.")}
            />
            <ConfirmAction
              label="Finalize group stage" title="Finalize the group stage?"
              description="Group results will be locked and the complete knockout bracket will be generated."
              confirmLabel="Finalize and create bracket" disabled={!data.detail.locks.can_finalize_group_stage}
              onConfirm={() => run(() => api.finalizeGroups(id), "Group stage finalized.")}
            />
          </Stack>
          {!data.detail.locks.roster_locked && (
            <Box>
              <Typography variant="h4" component="h2">Rosters</Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>Rosters remain editable until the first result is completed.</Typography>
              <Stack spacing={1}>{data.teams.map((team) => <RosterEditor key={team.id} competition={competition} team={team} run={run} />)}</Stack>
            </Box>
          )}
          {allGroupMatchesComplete && data.groups.some((group) => group.unresolved_ties.length > 0) && (
            <Stack spacing={2}>
              <Typography variant="h4" component="h2">Tie resolution</Typography>
              {data.groups.flatMap((group) => group.unresolved_ties.map((cohort) => (
                <DrawLotsEditor key={`${group.id}-${cohort.join("-")}`} group={group} teamIds={cohort} run={run} />
              )))}
            </Stack>
          )}
          <Box>
            <Typography variant="h4" component="h2" sx={{ mb: 2 }}>Standings</Typography>
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "repeat(2, 1fr)" }, gap: 2 }}>
              {data.groups.map((group) => <GroupTable key={group.id} group={group} />)}
            </Box>
          </Box>
          <Box><Typography variant="h4" component="h2" sx={{ mb: 2 }}>Group matches</Typography><RoundList rounds={groupRounds} admin /></Box>
        </Stack>
      )}

      {competition.status === "KNOCKOUT" && (
        <Stack spacing={3}>
          <Box><ConfirmAction label="Reopen group stage" title="Reopen the group stage?" description="The unplayed knockout bracket will be removed and group results will become editable again." disabled={!data.detail.locks.can_reopen_group_stage} onConfirm={() => run(() => api.reopenGroups(id), "Group stage reopened.")} /></Box>
          <Typography variant="h4" component="h2">Knockout bracket</Typography>
          <KnockoutBracket rounds={knockoutRounds} admin />
        </Stack>
      )}

      {competition.status === "COMPLETED" && (
        <Alert severity="success">Competition completed{data.detail.champion ? ` — ${data.detail.champion.name} are the champions.` : "."} Historical results are read-only.</Alert>
      )}

      <Snackbar open={Boolean(notice)} autoHideDuration={3500} onClose={() => setNotice("")} message={notice} />
    </Stack>
  );
}
