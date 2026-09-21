import { useState, type FormEvent } from "react";
import { Alert, Box, Button, Card, CardContent, Stack, TextField, Typography } from "@mui/material";
import { Navigate, useLocation, useNavigate } from "react-router";

import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { LoadingState } from "../components/PageState";

export function LoginPage() {
  const { session, loading, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const location = useLocation();
  const navigate = useNavigate();
  if (loading) return <LoadingState />;
  if (session?.is_admin) return <Navigate to="/admin" replace />;
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      await login(username, password);
      const destination = (location.state as { from?: string } | null)?.from ?? "/admin";
      navigate(destination, { replace: true });
    } catch (value) { setError(errorMessage(value)); } finally { setBusy(false); }
  }
  return (
    <Box sx={{ maxWidth: 430, mx: "auto", py: { md: 6 } }}>
      <Card><CardContent sx={{ p: { xs: 3, sm: 4 } }}>
        <Typography variant="h3" component="h1" sx={{ mb: 1 }}>Administrator sign in</Typography>
        <Typography color="text.secondary" sx={{ mb: 3 }}>Competition management is restricted to the organizer.</Typography>
        <Box component="form" onSubmit={(event) => void submit(event)}>
          <Stack spacing={2}>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField label="Username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required autoFocus />
            <TextField label="Password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            <Button type="submit" variant="contained" size="large" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
          </Stack>
        </Box>
      </CardContent></Card>
    </Box>
  );
}
