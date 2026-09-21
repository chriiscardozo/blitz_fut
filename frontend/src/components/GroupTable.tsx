import {
  Alert,
  Box,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import type { Group } from "../api/types";


export function GroupTable({ group }: { group: Group }) {
  return (
    <Paper variant="outlined" sx={{ overflow: "hidden" }}>
      <Box sx={{ px: 2, py: 1.5, display: "flex", gap: 1, alignItems: "center" }}>
        <Typography variant="h6" component="h3">Group {group.label}</Typography>
        {!group.standings_resolved && group.standings.length > 0 && (
          <Chip label="Tie unresolved" size="small" variant="outlined" />
        )}
      </Box>
      {group.standings.length === 0 ? (
        <Alert severity="info" sx={{ borderRadius: 0 }}>Teams have not been assigned yet.</Alert>
      ) : (
        <TableContainer>
          <Table size="small" aria-label={`Group ${group.label} standings`}>
            <TableHead>
              <TableRow>
                <TableCell width={42}>#</TableCell>
                <TableCell>Team</TableCell>
                <TableCell align="center">P</TableCell>
                <TableCell align="center" sx={{ display: { xs: "none", sm: "table-cell" } }}>W</TableCell>
                <TableCell align="center" sx={{ display: { xs: "none", sm: "table-cell" } }}>D</TableCell>
                <TableCell align="center" sx={{ display: { xs: "none", sm: "table-cell" } }}>L</TableCell>
                <TableCell align="center">GD</TableCell>
                <TableCell align="center">Pts</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {group.standings.map((row) => (
                <TableRow
                  key={row.team_id}
                  sx={{ bgcolor: row.qualifies ? "color-mix(in srgb, var(--mui-palette-primary-main) 8%, white)" : undefined }}
                >
                  <TableCell>{row.position}</TableCell>
                  <TableCell component="th" scope="row">
                    <Box component="span" sx={{ fontWeight: 700 }}>{row.team_name}</Box>
                    {row.unresolved_tie && <Box component="span" sx={{ color: "text.secondary" }}> *</Box>}
                  </TableCell>
                  <TableCell align="center">{row.played}</TableCell>
                  <TableCell align="center" sx={{ display: { xs: "none", sm: "table-cell" } }}>{row.wins}</TableCell>
                  <TableCell align="center" sx={{ display: { xs: "none", sm: "table-cell" } }}>{row.draws}</TableCell>
                  <TableCell align="center" sx={{ display: { xs: "none", sm: "table-cell" } }}>{row.losses}</TableCell>
                  <TableCell align="center">{row.goal_difference > 0 ? "+" : ""}{row.goal_difference}</TableCell>
                  <TableCell align="center"><strong>{row.points}</strong></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
}
