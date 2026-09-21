import { Typography } from "@mui/material";
import { Route, Routes } from "react-router";

import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AdminHomePage } from "./pages/AdminHomePage";
import { CompetitionListPage } from "./pages/CompetitionListPage";
import { CompetitionAdminPage } from "./pages/CompetitionAdminPage";
import { CompetitionPage } from "./pages/CompetitionPage";
import { CreateCompetitionPage } from "./pages/CreateCompetitionPage";
import { LoginPage } from "./pages/LoginPage";
import { MatchResultPage } from "./pages/MatchResultPage";

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<CompetitionListPage />} />
        <Route path="competitions/:competitionId" element={<CompetitionPage />} />
        <Route path="admin/login" element={<LoginPage />} />
        <Route path="admin" element={<ProtectedRoute><AdminHomePage /></ProtectedRoute>} />
        <Route path="admin/competitions/new" element={<ProtectedRoute><CreateCompetitionPage /></ProtectedRoute>} />
        <Route path="admin/competitions/:competitionId" element={<ProtectedRoute><CompetitionAdminPage /></ProtectedRoute>} />
        <Route path="admin/matches/:matchId" element={<ProtectedRoute><MatchResultPage /></ProtectedRoute>} />
        <Route path="*" element={<Typography variant="h3">Page not found</Typography>} />
      </Route>
    </Routes>
  );
}

export default App;
