import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { Spinner } from "../components/ui";

export function RequireAuth({ admin = false }: { admin?: boolean }) {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <div style={{ display: "grid", placeItems: "center", minHeight: "60vh" }}><Spinner /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />;
  if (admin && user.role !== "admin") return <Navigate to="/app" replace />;
  return <Outlet />;
}
