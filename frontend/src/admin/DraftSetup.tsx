import { useState, type FormEvent } from "react";
import {
  Alert, Box, Button, Card, CardContent, FormControl, InputLabel, MenuItem, Select,
  Stack, TextField, Typography,
} from "@mui/material";

import { api } from "../api/client";
import type { Competition, Group, Team } from "../api/types";
import { ConfirmAction } from "../components/ConfirmAction";
import { RosterEditor } from "./RosterEditor";

type RunAction = (operation: () => Promise<unknown>, success: string) => Promise<void>;

function TeamRow({ team, groups, run }: { team: Team; groups: Group[]; run: RunAction }) {
  const [name, setName] = useState(team.name);
  return (
    <Card><CardContent>
      <Stack direction={{ xs: "column", md: "row" }} sx={{ gap: 1.5, alignItems: { md: "center" } }}>
        <TextField size="small" label="Team name" value={name} onChange={(event) => setName(event.target.value)} sx={{ flex: 1 }} />
        <Button variant="outlined" disabled={!name.trim() || name.trim() === team.name} onClick={() => void run(() => api.renameTeam(team.id, name), "Team name updated.")}>Save name</Button>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel id={`team-${team.id}-group`}>Group</InputLabel>
          <Select labelId={`team-${team.id}-group`} label="Group" value={team.group_id ?? ""} onChange={(event) => void run(() => api.assignGroup(team.id, Number(event.target.value)), `${team.name} assigned to a group.`)}>
            <MenuItem value="" disabled>Not assigned</MenuItem>
            {groups.map((group) => <MenuItem key={group.id} value={group.id}>Group {group.label}</MenuItem>)}
          </Select>
        </FormControl>
        <ConfirmAction
          label="Delete" title={`Delete ${team.name}?`}
          description="The team and its draft roster assignment will be removed."
          confirmLabel="Delete team" color="error"
          onConfirm={() => run(() => api.deleteTeam(team.id), `${team.name} deleted.`)}
        />
      </Stack>
    </CardContent></Card>
  );
}

export function DraftSetup({
  competition, groups, teams, run,
}: { competition: Competition; groups: Group[]; teams: Team[]; run: RunAction }) {
  const [teamName, setTeamName] = useState("");
  const completeTeamList = teams.length === competition.total_team_count;
  const assignmentsComplete = completeTeamList && teams.every((team) => team.group_id !== null);
  async function addTeam(event: FormEvent) {
    event.preventDefault(); if (!teamName.trim()) return;
    await run(() => api.createTeam(competition.id, teamName), `${teamName.trim()} created.`);
    setTeamName("");
  }
  return (
    <Stack spacing={4}>
      <section>
        <Stack direction={{ xs: "column", sm: "row" }} sx={{ justifyContent: "space-between", gap: 2, mb: 2 }}>
          <div><Typography variant="h4" component="h2">1. Teams and groups</Typography><Typography color="text.secondary">{teams.length} of {competition.total_team_count} teams created.</Typography></div>
          <ConfirmAction
            label="Randomize groups" title="Randomize group assignments?"
            description="Current assignments will be replaced with a new even random distribution."
            disabled={!completeTeamList}
            onConfirm={() => run(() => api.randomizeGroups(competition.id), "Groups randomized.")}
          />
        </Stack>
        <Box component="form" onSubmit={(event) => void addTeam(event)} sx={{ mb: 2 }}>
          <Stack direction={{ xs: "column", sm: "row" }} sx={{ gap: 1 }}>
            <TextField label="Team name" size="small" value={teamName} onChange={(event) => setTeamName(event.target.value)} fullWidth />
            <Button type="submit" variant="contained" disabled={!teamName.trim() || completeTeamList}>Add team</Button>
          </Stack>
        </Box>
        <Stack spacing={1.5}>{teams.map((team) => <TeamRow key={team.id} team={team} groups={groups} run={run} />)}</Stack>
      </section>
      <section>
        <Typography variant="h4" component="h2">2. Rosters</Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>Create players or reuse an existing player by identifier.</Typography>
        <Stack spacing={1}>{teams.map((team) => <RosterEditor key={team.id} competition={competition} team={team} run={run} />)}</Stack>
      </section>
      <section>
        <Typography variant="h4" component="h2">3. Generate fixtures</Typography>
        <Alert severity={assignmentsComplete ? "success" : "info"} sx={{ my: 2 }}>
          {assignmentsComplete ? "Every team is assigned. The group stage is ready to generate." : "Create every configured team and assign each one to a group first."}
        </Alert>
        <ConfirmAction
          label="Generate group fixtures" title="Generate group-stage fixtures?"
          description="Teams and group assignments will be locked while the generated fixtures exist."
          confirmLabel="Generate fixtures" disabled={!assignmentsComplete}
          onConfirm={() => run(() => api.generateFixtures(competition.id), "Group fixtures generated.")}
        />
      </section>
    </Stack>
  );
}
