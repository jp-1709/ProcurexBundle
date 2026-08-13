# ProcureX Bundle

A single Frappe app that, when installed, automatically sets up **both**:
- **ProcureX Backend** (`procurex`) — Frappe app via `bench get-app`
- **ProcureX Frontend** — React/TanStack app via `git clone` + Vite build

## Repositories

| Component | GitHub URL |
|---|---|
| This bundle | `https://github.com/QuantbitERP/ProcureX-Bundle.git` |
| Frontend (ProcureX) | `https://github.com/QuantbitERP/ProcureX.git` |
| Backend (procurex) | `https://github.com/QuantbitERP/ProcureX-Backend.git` |

---

## Installation

### Step 1 — Get the backend app

```bash
cd /path/to/bench
bench get-app procurex https://github.com/QuantbitERP/ProcureX-Backend.git
```

### Step 2 — Get this bundle app

```bash
bench get-app procurex_bundle https://github.com/QuantbitERP/ProcureX-Bundle.git
```

### Step 3 — Install on your site (one command does everything)

```bash
bench --site <your-site> install-app procurex_bundle
```

**What happens automatically:**
1. Frappe installs `procurex` (backend) first — enforced by `required_apps`
2. `git clone https://github.com/QuantbitERP/ProcureX.git` → `apps/procurex_bundle/frontend/ProcureX/`
3. `npm install` (or `bun install` if bun is available)
4. `npm run build` — Vite writes directly to `procurex_bundle/public/procurex/`
5. `bench build --app procurex_bundle` — registers assets with Frappe
6. App is live at `http://<your-site>/procurex` ✅

---

## App Structure

```
apps/procurex_bundle/
├── .gitignore
├── MANIFEST.in
├── README.md
├── pyproject.toml                    ← apt deps: git, nodejs, npm
└── procurex_bundle/
    ├── hooks.py                      ← required_apps, route rules, apps-screen tile
    ├── install.py                    ← git clone + build logic (after_install hook)
    ├── modules.txt
    ├── patches.txt
    ├── config/desktop.py
    ├── public/
    │   ├── images/logo.png           ← app logo (add manually)
    │   └── procurex/                 ← Vite build output (auto-generated on install)
    │       ├── index.html
    │       └── assets/
    │           ├── index-[hash].js
    │           └── index-[hash].css
    ├── frontend/
    │   └── ProcureX/                 ← git cloned on install (gitignored)
    └── www/
        ├── procurex.html             ← SPA shell (Frappe page at /procurex)
        └── procurex.py               ← dynamically resolves hashed asset paths + CSRF
```

---

## Frontend `vite.config.ts` Requirement

The ProcureX frontend's `vite.config.ts` must have this `outDir`:

```ts
build: {
  outDir: "../../procurex_bundle/public/procurex",
  emptyOutDir: true,
}
```

This mirrors exactly how `erp_ui` does it:
```ts
// erp_ui reference
outDir: "../../erp_ui/public/ui"
```

---

## Optional `site_config.json` Overrides

```json
{
  "procurex_frontend_repo":   "https://github.com/QuantbitERP/ProcureX.git",
  "procurex_frontend_branch": "main",
  "procurex_node_binary":     "bun",
  "procurex_skip_build":      0
}
```

---

## Rebuilding the Frontend Manually

```bash
cd apps/procurex_bundle/frontend/ProcureX
bun run build                           # or: npm run build
# output lands in: apps/procurex_bundle/procurex_bundle/public/procurex/

bench build --app procurex_bundle
bench --site <site> clear-cache
```
