import { useEffect, useMemo, useState, type FormEvent } from "react";
import {
  Alert, Box, Button, Card, CardContent, Checkbox, FormControl, FormControlLabel,
  InputLabel, MenuItem, Select, Stack, TextField, Typography,
} from "@mui/material";
import { useNavigate } from "react-router";

import { api, errorMessage } from "../api/client";

const powers = [1, 2, 4, 8, 16];

export function CreateCompetitionPage() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [totalTeams, setTotalTeams] = useState(4);
  const [groups, setGroups] = useState(1);
  const [qualifiers, setQualifiers] = useState(2);
  const [thirdPlace, setThirdPlace] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const teamsPerGroup = totalTeams > 0 && totalTeams % groups === 0 ? totalTeams / groups : null;
  const knockoutTeams = groups * qualifiers;
  const valid = Boolean(name.trim() && teamsPerGroup && teamsPerGroup >= 2 && qualifiers <= teamsPerGroup && knockoutTeams >= 2 && (!thirdPlace || knockoutTeams >= 4));
  const qualifierOptions = useMemo(() => powers.filter((value) => !teamsPerGroup || value <= teamsPerGroup), [teamsPerGroup]);
  useEffect(() => {
    if (!qualifierOptions.includes(qualifiers)) setQualifiers(qualifierOptions.at(-1) ?? 1);
  }, [qualifierOptions, qualifiers]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const competition = await api.createCompetition({
        name, year, group_count: groups, total_team_count: totalTeams,
        qualifiers_per_group: qualifiers, third_place_enabled: thirdPlace,
      });
      navigate(`/admin/competitions/${competition.id}`);
    } catch (value) { setError(errorMessage(value)); } finally { setBusy(false); }
  }

  return (
    <Box sx={{ maxWidth: 720, mx: "auto" }}>
      <Typography variant="h2" component="h1" sx={{ mb: 1 }}>New competition</Typography>
      <Typography color="text.secondary" sx={{ mb: 3 }}>The format is locked after creation, before teams and rosters are added.</Typography>
      <Card><CardContent sx={{ p: { xs: 2.5, sm: 4 } }}>
        <Box component="form" onSubmit={(event) => void submit(event)}>
          <Stack spacing={2.5}>
          {error && <Alert severity="error">{error}</Alert>}
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "2fr 1fr" }, gap: 2 }}>
            <TextField label="Competition name" value={name} onChange={(event) => setName(event.target.value)} required autoFocus />
            <TextField label="Year" type="number" value={year} onChange={(event) => setYear(Number(event.target.value))} slotProps={{ htmlInput: { min: 1, max: 32767 } }} required />
          </Box>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2 }}>
            <TextField label="Total teams" type="number" value={totalTeams} onChange={(event) => setTotalTeams(Number(event.target.value))} slotProps={{ htmlInput: { min: 2, max: 32767 } }} required />
            <FormControl><InputLabel id="group-count-label">Groups</InputLabel><Select labelId="group-count-label" label="Groups" value={groups} onChange={(event) => setGroups(Number(event.target.value))}>{powers.map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</Select></FormControl>
            <FormControl><InputLabel id="qualifier-count-label">Qualifiers / group</InputLabel><Select labelId="qualifier-count-label" label="Qualifiers / group" value={qualifiers} onChange={(event) => setQualifiers(Number(event.target.value))}>{qualifierOptions.map((value) => <MenuItem key={value} value={value}>{value}</MenuItem>)}</Select></FormControl>
          </Box>
          <FormControlLabel control={<Checkbox checked={thirdPlace} onChange={(event) => setThirdPlace(event.target.checked)} />} label="Include a third-place match" />
          <Alert severity={valid ? "success" : "info"}>
            {teamsPerGroup ? `${groups} group${groups === 1 ? "" : "s"} of ${teamsPerGroup}; ${knockoutTeams} teams qualify.` : "The total number of teams must divide evenly between the groups."}
          </Alert>
          <Button type="submit" variant="contained" size="large" disabled={!valid || busy}>{busy ? "Creating…" : "Create competition"}</Button>
          </Stack>
        </Box>
      </CardContent></Card>
    </Box>
  );
}
