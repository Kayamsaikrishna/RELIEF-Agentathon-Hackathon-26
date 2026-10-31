import { Link, Route, Routes, useLocation } from "react-router-dom";
import { useEffect } from "react";
import { RequireAuth } from "./auth/RequireAuth";
import PublicLayout from "./layouts/PublicLayout";
import AppLayout from "./layouts/AppLayout";
import Landing from "./pages/public/Landing";
import Safety from "./pages/public/Safety";
import Login from "./pages/public/Login";
import Dashboard from "./pages/app/Dashboard";
import Cases from "./pages/app/Cases";
import NewCase from "./pages/app/NewCase";
import CaseDetail from "./pages/app/CaseDetail";
import Reminders from "./pages/app/Reminders";
import Account from "./pages/app/Account";
import { AdminAudit, AdminOverview, AdminRegistry, AdminRules, AdminSystem, AdminUsers } from "./pages/admin/Admin";

function ScrollTop() {
  const { pathname, hash } = useLocation();
  useEffect(() => { if (hash) { setTimeout(() => document.querySelector(hash)?.scrollIntoView({ behavior: "smooth" }), 50); } else window.scrollTo(0, 0); }, [pathname, hash]);
  return null;
}
const NotFound = () => <div style={{ display: "grid", placeItems: "center", minHeight: "70vh", textAlign: "center", gap: 14, padding: 20 }}><div><h1 style={{ fontSize: "4rem" }}>404</h1><p className="muted" style={{ margin: "8px 0 18px" }}>This page does not exist.</p><Link className="btn btn-ink" to="/">Go home</Link></div></div>;

export default function App() {
  return (
    <>
      <ScrollTop />
      <Routes>
        <Route element={<PublicLayout />}><Route path="/" element={<Landing />} /><Route path="/safety" element={<Safety />} /></Route>
        <Route path="/login" element={<Login />} />
        <Route element={<RequireAuth />}>
          <Route element={<AppLayout />}>
            <Route path="/app" element={<Dashboard />} />
            <Route path="/app/cases" element={<Cases />} />
            <Route path="/app/cases/new" element={<NewCase />} />
            <Route path="/app/cases/:id" element={<CaseDetail />} />
            <Route path="/app/reminders" element={<Reminders />} />
            <Route path="/app/account" element={<Account />} />
            <Route element={<RequireAuth admin />}>
              <Route path="/admin" element={<AdminOverview />} />
              <Route path="/admin/users" element={<AdminUsers />} />
              <Route path="/admin/rules" element={<AdminRules />} />
              <Route path="/admin/registry" element={<AdminRegistry />} />
              <Route path="/admin/audit" element={<AdminAudit />} />
              <Route path="/admin/system" element={<AdminSystem />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}
