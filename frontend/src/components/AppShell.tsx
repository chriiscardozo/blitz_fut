import { AppBar, Box, Button, Container, Toolbar, Typography } from "@mui/material";
import { Link, Outlet, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthProvider";

export function AppShell() {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  async function signOut() { await logout(); navigate("/"); }
  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Container maxWidth="lg">
          <Toolbar disableGutters sx={{ gap: 1 }}>
            <Typography component={Link} to="/" variant="h6" color="text.primary"
              sx={{ flexGrow: 1, fontWeight: 900, textDecoration: "none" }}>
              Blitz Fut
            </Typography>
            {session?.is_admin ? (
              <><Button component={Link} to="/admin">Admin</Button><Button onClick={() => void signOut()}>Sign out</Button></>
            ) : <Button component={Link} to="/admin/login">Admin sign in</Button>}
          </Toolbar>
        </Container>
      </AppBar>
      <Container component="main" maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}><Outlet /></Container>
    </Box>
  );
}
