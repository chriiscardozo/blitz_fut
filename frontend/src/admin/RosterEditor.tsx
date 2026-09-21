import { useEffect, useState, type FormEvent } from "react";
import {
  Accordion, AccordionDetails, AccordionSummary, Autocomplete, Box, Button,
  Divider, Stack, TextField, Typography,
} from "@mui/material";

import { api } from "../api/client";
import type { Competition, Player, Team } from "../api/types";
import { ConfirmAction } from "../components/ConfirmAction";

type RunAction = (operation: () => Promise<unknown>, success: string) => Promise<void>;

function RosterMemberRow({
  membership,
  teamName,
  run,
}: {
  membership: Team["roster"][number];
  teamName: string;
  run: RunAction;
}) {
  const [name, setName] = useState(membership.player.name);
  return (
    <Stack direction={{ xs: "column", sm: "row" }} sx={{ gap: 1, alignItems: { sm: "center" } }}>
      <TextField size="small" label="Player name" value={name} onChange={(event) => setName(event.target.value)} fullWidth />
      <Button variant="outlined" disabled={!name.trim() || name.trim() === membership.player.name} onClick={() => void run(() => api.renamePlayer(membership.player.id, name), "Player name updated.")}>Save name</Button>
      <ConfirmAction
        label="Remove" title={`Remove ${membership.player.name}?`}
        description={`The player will be removed from ${teamName}, but their reusable player record will be kept.`}
        confirmLabel="Remove player" color="error"
        onConfirm={() => run(() => api.removeRoster(membership.id), `${membership.player.name} removed from ${teamName}.`)}
      />
    </Stack>
  );
}

export function RosterEditor({
  competition,
  team,
  run,
}: {
  competition: Competition;
  team: Team;
  run: RunAction;
}) {
  const [newPlayerName, setNewPlayerName] = useState("");
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<Player[]>([]);
  const [selected, setSelected] = useState<Player | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      api.searchPlayers(query).then(setOptions).catch(() => setOptions([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  async function addNew(event: FormEvent) {
    event.preventDefault();
    if (!newPlayerName.trim()) return;
    await run(
      () => api.createPlayer(competition.id, team.id, newPlayerName),
      `${newPlayerName.trim()} added to ${team.name}.`,
    );
    setNewPlayerName("");
  }

  async function addExisting() {
    if (!selected) return;
    await run(
      () => api.assignPlayer(competition.id, team.id, selected.id),
      `${selected.name} assigned to ${team.name}.`,
    );
    setSelected(null); setQuery("");
  }

  return (
    <Accordion disableGutters elevation={0} sx={{ border: 1, borderColor: "divider", "&:before": { display: "none" } }}>
      <AccordionSummary expandIcon={<span aria-hidden>⌄</span>}>
        <Box sx={{ flexGrow: 1 }}><Typography sx={{ fontWeight: 800 }}>{team.name}</Typography><Typography variant="body2" color="text.secondary">{team.roster.length} {team.roster.length === 1 ? "player" : "players"}</Typography></Box>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={2}>
          <Stack sx={{ gap: 1 }}>
            {team.roster.length ? team.roster.map((membership) => (
              <RosterMemberRow key={membership.id} membership={membership} teamName={team.name} run={run} />
            )) : <Typography color="text.secondary">No players assigned.</Typography>}
          </Stack>
          <Divider />
          <Box component="form" onSubmit={(event) => void addNew(event)}>
            <Stack direction={{ xs: "column", sm: "row" }} sx={{ gap: 1 }}>
              <TextField size="small" label="New player name" value={newPlayerName} onChange={(event) => setNewPlayerName(event.target.value)} fullWidth />
              <Button type="submit" variant="outlined" disabled={!newPlayerName.trim()}>Create and add</Button>
            </Stack>
          </Box>
          <Stack direction={{ xs: "column", sm: "row" }} sx={{ gap: 1 }}>
            <Autocomplete
              size="small"
              fullWidth
              options={options}
              value={selected}
              inputValue={query}
              onInputChange={(_, value) => setQuery(value)}
              onChange={(_, value) => setSelected(value)}
              getOptionLabel={(option) => `${option.name} (#${option.id})`}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              renderInput={(params) => <TextField {...params} label="Find an existing player" />}
            />
            <Button variant="outlined" disabled={!selected} onClick={() => void addExisting()}>Assign existing</Button>
          </Stack>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}
