import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { useAuth } from "../auth/AuthProvider";
import { LoadingState } from "./PageState";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingState />;
  if (!session?.is_admin) return <Navigate to="/admin/login" replace state={{ from: location.pathname }} />;
  return children;
}
