import { useState } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Brand } from "../components/ui";
import { useAuth } from "../auth/AuthContext";

export default function PublicLayout() {
  const [open, setOpen] = useState(false);
  const { user } = useAuth();
  const { pathname } = useLocation();
  const home = pathname === "/";
  const a = (id: string, label: string) => (home ? <a href={`#${id}`} onClick={() => setOpen(false)}>{label}</a> : <Link to={`/#${id}`}>{label}</Link>);
  return (
    <div className="pub">
      <header className="nav">
        <div className="container nav-in">
          <Brand />
          <nav className={`nav-links ${open ? "open" : ""}`} aria-label="Main">
            {a("problem", "The problem")}
            {a("blockers", "Six blockers")}
            {a("how", "How it works")}
            {a("safety", "Safety")}
            {a("posters", "In pictures")}
            {a("faq", "FAQ")}
            <Link to="/safety" onClick={() => setOpen(false)}>Limits</Link>
          </nav>
          <div className="nav-cta">
            {user ? <Link className="btn btn-ink" to="/app">Open workspace</Link> : <Link className="btn btn-ink" to="/login">Sign in</Link>}
            <button className="btn btn-ghost nav-burger" aria-label="Menu" onClick={() => setOpen(!open)}>{open ? <X size={18} /> : <Menu size={18} />}</button>
          </div>
        </div>
      </header>
      <Outlet />
      <footer className="foot">
        <div className="container">
          <div className="foot-grid">
            <div><Brand sub={false} /><p style={{ marginTop: 14, maxWidth: 380 }}>An AI agent that finds why cashless treatment was blocked, cites the rule and prepares the fix. A person approves every action.</p></div>
            <div><h4>Product</h4><a href="/#blockers">Six blockers</a><a href="/#how">How it works</a><Link to="/safety">Safety and limits</Link><Link to="/login">Sign in</Link></div>
            <div><h4>Team</h4><span>CareCatalysts</span><span style={{ display: "block" }}>Agentathon 2026, PES University</span></div>
          </div>
          <div className="legal">
            <span>RELIEF is a prototype built for a hackathon. It is not an official service of any government body or insurer and is not affiliated with the National Health Authority.</span>
            <span>It gives no medical advice and makes no eligibility decisions. In an emergency call 112 or go to the nearest hospital.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
