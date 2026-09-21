import { useEffect, useState } from "react";
import { Box, Stack, Typography } from "@mui/material";

import { api, errorMessage } from "../api/client";
import type { CompetitionLists } from "../api/types";
import { CompetitionCard } from "../components/CompetitionCard";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";

export function CompetitionListPage() {
  const [data, setData] = useState<CompetitionLists | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api.competitions().then(setData).catch((value) => setError(errorMessage(value))); }, []);
  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState label="Loading competitions…" />;
  return (
    <Stack spacing={5}>
      <Box>
        <Typography variant="overline" color="primary.main" sx={{ fontWeight: 800 }}>Five-a-side cup</Typography>
        <Typography variant="h1" sx={{ fontSize: { xs: "3rem", md: "5rem" } }}>Blitz Fut</Typography>
        <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 560, fontSize: "1.1rem" }}>
          Follow group tables, matchdays, knockout fixtures, scorers, and assisters.
        </Typography>
      </Box>
      <section>
        <Typography variant="h4" component="h2" sx={{ mb: 2 }}>Active competitions</Typography>
        {data.active.length ? (
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
            {data.active.map((competition) => <CompetitionCard key={competition.id} competition={competition} />)}
          </Box>
        ) : <EmptyState message="There is no active competition yet." />}
      </section>
      <section>
        <Typography variant="h4" component="h2" sx={{ mb: 2 }}>Past competitions</Typography>
        {data.past.length ? (
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
            {data.past.map((competition) => <CompetitionCard key={competition.id} competition={competition} />)}
          </Box>
        ) : <EmptyState message="Completed competitions will appear here." />}
      </section>
    </Stack>
  );
}
