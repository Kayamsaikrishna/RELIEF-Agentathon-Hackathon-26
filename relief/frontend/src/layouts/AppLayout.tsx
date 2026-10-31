import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Activity, Bell, BookOpen, Database, FolderOpen, LayoutDashboard, LogOut, Menu, PlusCircle, ScrollText, Server, UserCog, Users } from "lucide-react";
import { Brand } from "../components/ui";
import { useAuth } from "../auth/AuthContext";
import { api } from "../api/client";
import { initials } from "../lib";
import type { Stats } from "../api/types";

export default function AppLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [badge, setBadge] = useState({ approve: 0, rem: 0 });
  useEffect(() => { setOpen(false); }, [loc.pathname]);
  useEffect(() => {
    let live = true;
    const load = () => api<Stats>("/stats").then((s) => live && setBadge({ approve: s.by_status.awaiting_approval ?? 0, rem: s.reminders_due })).catch(() => {});
    load(); const t = setInterval(load, 20000);
    return () => { live = false; clearInterval(t); };
  }, [loc.pathname]);
  if (!user) return null;
  const link = (to: string, icon: JSX.Element, label: string, count?: number, end = false) => (
    <NavLink to={to} end={end} className={({ isActive }) => `item ${isActive ? "active" : ""}`}>{icon}{label}{!!count && <span className="count">{count}</span>}</NavLink>
  );
  const crumb = loc.pathname.startsWith("/admin") ? "Administration" : "Workspace";
  return (
    <div className="shell">
      {open && <div className="scrim" onClick={() => setOpen(false)} />}
      <aside className={`side ${open ? "open" : ""}`} aria-label="Sidebar">
        <Brand to="/app" />
        <div className="grp">Workspace</div>
        {link("/app", <LayoutDashboard size={19} />, "Dashboard", undefined, true)}
        {link("/app/cases/new", <PlusCircle size={19} />, "New case")}
        {link("/app/cases", <FolderOpen size={19} />, "Cases", badge.approve)}
        {link("/app/reminders", <Bell size={19} />, "Reminders", badge.rem)}
        {user.role === "admin" && <>
          <div className="grp">Administration</div>
          {link("/admin", <Activity size={19} />, "Overview", undefined, true)}
          {link("/admin/users", <Users size={19} />, "Users")}
          {link("/admin/rules", <BookOpen size={19} />, "Rules")}
          {link("/admin/registry", <Database size={19} />, "Registry")}
          {link("/admin/audit", <ScrollText size={19} />, "Audit log")}
          {link("/admin/system", <Server size={19} />, "System")}
        </>}
        <div className="who">
          <div className="avatar">{initials(user.name)}</div>
          <div style={{ minWidth: 0 }}><b>{user.name}</b><span>{user.role === "admin" ? "Administrator" : "Facilitator"}</span></div>
          <button className="btn btn-sm" style={{ marginLeft: "auto", background: "rgba(255,255,255,.08)", color: "#fff", padding: 8 }} aria-label="Account" onClick={() => nav("/app/account")}><UserCog size={16} /></button>
          <button className="btn btn-sm" style={{ background: "rgba(255,255,255,.08)", color: "#fff", padding: 8 }} aria-label="Sign out" onClick={() => { logout(); nav("/"); }}><LogOut size={16} /></button>
        </div>
      </aside>
      <div className="main">
        <header className="top">
          <div className="row"><button className="btn btn-ghost btn-sm burger" aria-label="Open menu" onClick={() => setOpen(true)}><Menu size={18} /></button><span className="crumbs"><b>{crumb}</b></span></div>
          <span className="badge green" title="NHA guidelines and empanelment registry connected">Live Claim Engine · NHA Codified</span>
        </header>
        <div className="page"><Outlet /></div>
      </div>
    </div>
  );
}
