import { Alert, Box, CircularProgress, Typography } from "@mui/material";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <Box sx={{ py: 8, textAlign: "center" }} role="status">
      <CircularProgress size={32} />
      <Typography color="text.secondary" sx={{ mt: 2 }}>{label}</Typography>
    </Box>
  );
}

export function ErrorState({ message }: { message: string }) {
  return <Alert severity="error">{message}</Alert>;
}

export function EmptyState({ message }: { message: string }) {
  return (
    <Box sx={{ border: 1, borderColor: "divider", borderRadius: 2, p: 3 }}>
      <Typography color="text.secondary">{message}</Typography>
    </Box>
  );
}
