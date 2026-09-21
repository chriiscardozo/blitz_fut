import { useEffect, useMemo, useState } from "react";
import {
  Alert, Box, Button, ButtonGroup, Card, CardContent, Divider, FormControl,
  FormControlLabel, FormLabel, Radio, RadioGroup, Stack, Typography,
} from "@mui/material";
import { useNavigate, useParams } from "react-router";

import { api, errorMessage } from "../api/client";
import type { MatchEntry, MatchTeamEntry, TeamResultInput } from "../api/types";
import { ErrorState, LoadingState } from "../components/PageState";

type CounterProps = {
  label: string;
  value: number;
  decrementDisabled?: boolean;
  incrementDisabled?: boolean;
  onChange: (value: number) => void;
};

function Counter({ label, value, decrementDisabled, incrementDisabled, onChange }: CounterProps) {
  return (
    <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between", gap: 1 }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <ButtonGroup size="small" variant="outlined" aria-label={`${label}: ${value}`}>
        <Button aria-label={`Remove one ${label.toLowerCase()}`} disabled={value === 0 || decrementDisabled} onClick={() => onChange(value - 1)}>−</Button>
        <Button component="span" tabIndex={-1} sx={{ minWidth: 42, color: "text.primary", pointerEvents: "none" }}>{value}</Button>
        <Button aria-label={`Add one ${label.toLowerCase()}`} disabled={incrementDisabled || value >= 32767} onClick={() => onChange(value + 1)}>+</Button>
      </ButtonGroup>
    </Stack>
  );
}

function teamScore(team: MatchTeamEntry) {
  return team.own_goals_received + team.players.reduce((total, player) => total + player.goals, 0);
}

function ResultTeamCard({ team, onChange }: { team: MatchTeamEntry; onChange: (team: MatchTeamEntry) => void }) {
  const playerGoals = team.players.reduce((total, player) => total + player.goals, 0);
  const assists = team.players.reduce((total, player) => total + player.assists, 0);
  function changePlayer(id: number, field: "goals" | "assists", value: number) {
    onChange({ ...team, players: team.players.map((player) => player.roster_membership_id === id ? { ...player, [field]: value } : player) });
  }
  return (
    <Card><CardContent>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "baseline", mb: 2 }}>
        <Typography variant="h5" component="h2">{team.team.name}</Typography>
        <Typography variant="h3" aria-label={`${team.team.name} score ${teamScore(team)}`}>{teamScore(team)}</Typography>
      </Stack>
      <Stack spacing={2}>
        {team.players.length ? team.players.map((player) => (
          <Box key={player.roster_membership_id} sx={{ borderTop: 1, borderColor: "divider", pt: 1.5 }}>
            <Typography sx={{ mb: 1, fontWeight: 800 }}>{player.player_name}</Typography>
            <Stack spacing={1}>
              <Counter label="Goals" value={player.goals} decrementDisabled={playerGoals - 1 < assists} onChange={(value) => changePlayer(player.roster_membership_id, "goals", value)} />
              <Counter label="Assists" value={player.assists} incrementDisabled={assists >= playerGoals} onChange={(value) => changePlayer(player.roster_membership_id, "assists", value)} />
            </Stack>
          </Box>
        )) : <Alert severity="info">This team has no roster. Only own goals received can be entered.</Alert>}
        <Divider />
        <Counter label="Own goals received" value={team.own_goals_received} onChange={(value) => onChange({ ...team, own_goals_received: value })} />
      </Stack>
    </CardContent></Card>
  );
}

function toInput(team: MatchTeamEntry): TeamResultInput {
  return {
    team_id: team.team.id,
    own_goals_received: team.own_goals_received,
    player_stats: team.players.map((player) => ({
      roster_membership_id: player.roster_membership_id,
      goals: player.goals,
      assists: player.assists,
    })),
  };
}

export function MatchResultPage() {
  const matchId = Number(useParams().matchId);
  const navigate = useNavigate();
  const [entry, setEntry] = useState<MatchEntry | null>(null);
  const [shootoutWinner, setShootoutWinner] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api.matchEntry(matchId).then((value) => { setEntry(value); setShootoutWinner(value.match.shootout_winner_id); }).catch((value) => setError(errorMessage(value)));
  }, [matchId]);
  const scoreA = entry ? teamScore(entry.team_a) : 0;
  const scoreB = entry ? teamScore(entry.team_b) : 0;
  const tiedKnockout = entry?.match.stage === "KNOCKOUT" && scoreA === scoreB;
  const winnerLabel = entry?.match.kind === "FINAL" || entry?.match.kind === "THIRD_PLACE" ? "Winner" : "Qualified team";
  const canSave = entry && (!tiedKnockout || shootoutWinner !== null);
  const heading = useMemo(() => entry ? `${entry.team_a.team.name} vs ${entry.team_b.team.name}` : "Match result", [entry]);

  async function save() {
    if (!entry) return;
    setBusy(true); setError("");
    try {
      await api.saveMatchResult(matchId, toInput(entry.team_a), toInput(entry.team_b), tiedKnockout ? shootoutWinner : null);
      navigate(-1);
    } catch (value) { setError(errorMessage(value)); } finally { setBusy(false); }
  }

  if (error && !entry) return <ErrorState message={error} />;
  if (!entry) return <LoadingState label="Loading match…" />;
  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="overline" color="primary.main">{entry.match.round_name}{entry.match.group_label ? ` · Group ${entry.match.group_label}` : ""}</Typography>
        <Typography variant="h2" component="h1">{heading}</Typography>
        <Typography color="text.secondary">Distribute every normal-time goal before completing the match.</Typography>
      </Box>
      {error && <Alert severity="error">{error}</Alert>}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
        <ResultTeamCard team={entry.team_a} onChange={(team) => setEntry({ ...entry, team_a: team })} />
        <ResultTeamCard team={entry.team_b} onChange={(team) => setEntry({ ...entry, team_b: team })} />
      </Box>
      {tiedKnockout && (
        <Card><CardContent>
          <FormControl required>
            <FormLabel>{winnerLabel} after penalties</FormLabel>
            <RadioGroup value={shootoutWinner ?? ""} onChange={(event) => setShootoutWinner(Number(event.target.value))}>
              <FormControlLabel value={entry.team_a.team.id} control={<Radio />} label={entry.team_a.team.name} />
              <FormControlLabel value={entry.team_b.team.id} control={<Radio />} label={entry.team_b.team.name} />
            </RadioGroup>
          </FormControl>
        </CardContent></Card>
      )}
      <Stack direction={{ xs: "column-reverse", sm: "row" }} sx={{ justifyContent: "flex-end", gap: 1 }}>
        <Button onClick={() => navigate(-1)} disabled={busy}>Cancel</Button>
        <Button variant="contained" size="large" disabled={!canSave || busy} onClick={() => void save()}>{busy ? "Saving…" : entry.match.status === "COMPLETED" ? "Save corrected result" : "Complete match"}</Button>
      </Stack>
    </Stack>
  );
}
