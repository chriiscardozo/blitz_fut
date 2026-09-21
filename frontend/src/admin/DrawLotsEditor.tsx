import { useEffect, useState } from "react";
import { Alert, Button, Checkbox, FormControlLabel, Stack, TextField, Typography } from "@mui/material";

import { api } from "../api/client";
import type { Group } from "../api/types";

type RunAction = (operation: () => Promise<unknown>, success: string) => Promise<void>;

export function DrawLotsEditor({ group, teamIds, run }: { group: Group; teamIds: number[]; run: RunAction }) {
  const [values, setValues] = useState<Record<number, string>>({});
  const [confirmed, setConfirmed] = useState(false);
  useEffect(() => {
    setValues(Object.fromEntries(teamIds.map((id) => [id, group.standings.find((row) => row.team_id === id)?.draw_lots_priority?.toString() ?? ""])));
    setConfirmed(false);
  }, [group, teamIds]);
  const priorities = Object.fromEntries(teamIds.map((id) => [id, Number(values[id])]));
  const valid = confirmed && teamIds.every((id) => Number.isInteger(priorities[id]) && priorities[id] > 0) && new Set(Object.values(priorities)).size === teamIds.length;
  return (
    <Alert severity="warning">
      <Typography sx={{ mb: 1, fontWeight: 800 }}>Drawing of lots required in Group {group.label}</Typography>
      <Typography variant="body2" sx={{ mb: 2 }}>Higher priority ranks first. Enter a unique positive number for every tied team.</Typography>
      <Stack spacing={1.5}>
        {teamIds.map((id) => {
          const team = group.standings.find((row) => row.team_id === id);
          return <TextField key={id} size="small" type="number" label={team?.team_name ?? `Team ${id}`} value={values[id] ?? ""} onChange={(event) => setValues((current) => ({ ...current, [id]: event.target.value }))} slotProps={{ htmlInput: { min: 1 } }} />;
        })}
        <FormControlLabel control={<Checkbox checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />} label="I confirm this order reflects the drawing of lots." />
        <Button variant="contained" disabled={!valid} onClick={() => void run(() => api.saveDrawLots(group.id, priorities, confirmed), `Group ${group.label} tie resolved.`)}>Save draw order</Button>
      </Stack>
    </Alert>
  );
}
