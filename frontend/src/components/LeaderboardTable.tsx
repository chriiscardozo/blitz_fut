import {
  Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography,
} from "@mui/material";
import type { LeaderboardRow } from "../api/types";

export function LeaderboardTable({ title, rows }: { title: string; rows: LeaderboardRow[] }) {
  return (
    <Paper variant="outlined" sx={{ overflow: "hidden" }}>
      <Typography variant="h6" component="h3" sx={{ p: 2 }}>{title}</Typography>
      <TableContainer>
        <Table size="small" aria-label={title}>
          <TableHead><TableRow><TableCell>#</TableCell><TableCell>Player</TableCell><TableCell>Team</TableCell><TableCell align="right">Total</TableCell></TableRow></TableHead>
          <TableBody>
            {rows.length === 0 ? (
              <TableRow><TableCell colSpan={4}><Typography color="text.secondary">No statistics yet.</Typography></TableCell></TableRow>
            ) : rows.map((row) => (
              <TableRow key={row.player_id}>
                <TableCell>{row.rank}</TableCell>
                <TableCell component="th" scope="row"><strong>{row.player_name}</strong></TableCell>
                <TableCell>{row.team_name}</TableCell>
                <TableCell align="right"><strong>{row.total}</strong></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}
