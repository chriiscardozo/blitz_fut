import { useEffect, useState } from "react";
import { Box, Button, Stack, Typography } from "@mui/material";
import { Link } from "react-router";

import { api, errorMessage } from "../api/client";
import type { CompetitionLists } from "../api/types";
import { CompetitionCard } from "../components/CompetitionCard";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";

export function AdminHomePage() {
  const [data, setData] = useState<CompetitionLists | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api.competitions().then(setData).catch((value) => setError(errorMessage(value))); }, []);
  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;
  const competitions = [...data.active, ...data.past];
  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, gap: 2 }}>
        <div><Typography variant="h2" component="h1">Administration</Typography><Typography color="text.secondary">Configure and operate Blitz Fut competitions.</Typography></div>
        <Button component={Link} to="/admin/competitions/new" variant="contained">New competition</Button>
      </Stack>
      {competitions.length ? (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
          {competitions.map((competition) => <CompetitionCard key={competition.id} competition={competition} admin />)}
        </Box>
      ) : <EmptyState message="Create the first competition to get started." />}
    </Stack>
  );
}
