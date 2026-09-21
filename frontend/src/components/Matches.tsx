import { Box, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { Link } from "react-router";

import type { Match, Round } from "../api/types";


function participantName(match: Match, side: "a" | "b") {
  return (side === "a" ? match.team_a : match.team_b)?.name ?? "To be decided";
}

export function MatchCard({ match, admin = false }: { match: Match; admin?: boolean }) {
  const complete = match.status === "COMPLETED";
  const content = (
    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
      <Stack direction="row" sx={{ justifyContent: "space-between", gap: 1, mb: 1.5 }}>
        <Typography variant="caption" color="text.secondary">
          {match.group_label ? `Group ${match.group_label}` : match.kind === "THIRD_PLACE" ? "Third place" : match.round_name}
        </Typography>
        <Chip label={complete ? "Final" : "Pending"} size="small" variant="outlined" />
      </Stack>
      {(["a", "b"] as const).map((side) => {
        const team = side === "a" ? match.team_a : match.team_b;
        const score = side === "a" ? match.score_a : match.score_b;
        return (
          <Stack key={side} direction="row" sx={{ justifyContent: "space-between", gap: 2, py: 0.35 }}>
            <Typography color={team ? "text.primary" : "text.secondary"} sx={{ fontWeight: team ? 700 : 400 }}>
              {participantName(match, side)}
              {complete && match.shootout_winner_id === team?.id ? " (p)" : ""}
            </Typography>
            <Typography sx={{ fontWeight: 900 }}>{complete ? score : "–"}</Typography>
          </Stack>
        );
      })}
    </CardContent>
  );
  const canEnter = admin && match.team_a && match.team_b;
  return (
    <Card sx={{ minWidth: 220 }}>
      {canEnter ? (
        <Box component={Link} to={`/admin/matches/${match.id}`} sx={{ color: "inherit", textDecoration: "none", display: "block" }}>
          {content}
        </Box>
      ) : content}
    </Card>
  );
}

export function RoundList({ rounds, admin = false }: { rounds: Round[]; admin?: boolean }) {
  return (
    <Stack spacing={3}>
      {rounds.map((round) => (
        <Box key={round.id}>
          <Typography variant="h6" component="h3" sx={{ mb: 1.5 }}>{round.name}</Typography>
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" }, gap: 1.5 }}>
            {round.matches.map((match) => <MatchCard key={match.id} match={match} admin={admin} />)}
          </Box>
        </Box>
      ))}
    </Stack>
  );
}

export function KnockoutBracket({ rounds, admin = false }: { rounds: Round[]; admin?: boolean }) {
  return (
    <Box sx={{ overflowX: "auto", pb: 2 }}>
      <Box sx={{ display: "flex", gap: 2, minWidth: Math.max(280, rounds.length * 250), alignItems: "stretch" }}>
        {rounds.map((round) => (
          <Box key={round.id} sx={{ flex: "1 0 230px", display: "flex", flexDirection: "column" }}>
            <Typography variant="overline" color="text.secondary" sx={{ mb: 1 }}>{round.name}</Typography>
            <Stack spacing={2} sx={{ flexGrow: 1, justifyContent: "space-around" }}>
              {round.matches.map((match) => <MatchCard key={match.id} match={match} admin={admin} />)}
            </Stack>
          </Box>
        ))}
      </Box>
    </Box>
  );
}
