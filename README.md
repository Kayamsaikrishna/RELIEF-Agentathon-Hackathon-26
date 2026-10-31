# RELIEF Web Studio

A full-stack, responsive web application and facilitator workspace for **RELIEF** (Find the Block, Clear the Way) — solving cashless healthcare claim rejections under **Ayushman Bharat PM-JAY** and **Arogya Karnataka**.

---

## Brand & Visuals

This web studio features the official RELIEF branding:
- **Brand Emblem / Poster**: `Relief_ Clear the Way.png`
- **Application Icon & Mark**: `Roadblock R with Mint Check Arrow.png`
- **Full Poster Story**: The complete 10-poster journey from case denial to verified dispute escalation.

---

## Technology Stack

- **Framework**: [TanStack Start](https://tanstack.com/start) + [React 19](https://react.dev)
- **Styling**: [Tailwind CSS v4](https://tailwindcss.com) + Lucide Icons
- **State & Server Functions**: TanStack Query + TanStack Router
- **Database & Auth**: PostgreSQL / Supabase
- **Diagnosis Engine**: Deterministic rules engine with human approval gate

---

## Getting Started

### 1. Install Dependencies
```bash
npm install
# or bun install
```

### 2. Environment Setup
Copy the environment template if needed:
```bash
cp .env.example .env
```

Ensure your Supabase / Database variables are configured.

### 3. Run Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) (or the Vite dev port shown in your terminal).

### 4. Build for Production
```bash
npm run build
```
