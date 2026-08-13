# ProcureX Bundle

A single Frappe app that, when installed, **automatically sets up both**:
- **ProcureX Backend** (`procurex`) — fetched via `bench get-app` and installed on the site
- **ProcureX Frontend** — built from the embedded source (git submodule) via Vite

No separate steps needed — one install command does everything.

## Repositories

| Component | GitHub URL |
|---|---|
| This bundle | `https://github.com/QuantbitERP/ProcureX-Bundle.git` |
| Frontend (ProcureX) | `https://github.com/QuantbitERP/ProcureX.git` (embedded as submodule) |
| Backend (procurex) | `https://github.com/QuantbitERP/ProcureX-Backend.git` (fetched on install) |

---

## Installation

### Step 1 — Get this bundle app (with submodules)

```bash
cd /path/to/bench
bench get-app procurex_bundle https://github.com/QuantbitERP/ProcureX-Bundle.git
```

> **Important:** The frontend is embedded as a git submodule.
> If cloning manually, use `--recurse-submodules`:
> ```bash
> git clone --recurse-submodules https://github.com/QuantbitERP/ProcureX-Bundle.git
> ```

### Step 2 — Install on your site (one command does everything)

```bash
bench --site <your-site> install-app procurex_bundle
```

**What happens automatically:**
1. `bench get-app procurex https://github.com/QuantbitERP/ProcureX-Backend.git`
2. `bench --site <site> install-app procurex` (backend installed first)
3. `npm install` inside `frontend/ProcureX/`
4. `npm run build` — Vite writes directly to `procurex_bundle/public/procurex/`
5. `bench build --app procurex_bundle` — Frappe registers the assets
6. App is live at `http://<your-site>/procurex` ✅

---

## App Structure

```
apps/procurex_bundle/
├── .gitmodules                       ← registers frontend/ProcureX submodule
├── .gitignore
├── MANIFEST.in
├── README.md
├── pyproject.toml                    ← apt deps: git, nodejs, npm
├── frontend/
│   └── ProcureX/                     ← git submodule (ProcureX React frontend)
│       └── vite.config.ts            ← outDir: "../../procurex_bundle/public/procurex"
└── procurex_bundle/
    ├── hooks.py                      ← route rules, apps-screen tile, install hooks
    ├── install.py                    ← backend bench get-app + frontend npm build
    ├── public/
    │   ├── images/logo.png           ← app logo
    │   └── procurex/                 ← Vite build output (auto-generated, gitignored)
    │       ├── index.html
    │       └── assets/
    │           ├── index-[hash].js
    │           └── index-[hash].css
    └── www/
        ├── procurex.html             ← SPA shell (Frappe page at /procurex)
        └── procurex.py               ← CSRF token injection + dynamic asset paths
```

---

## Pattern Reference

This follows the exact same pattern as `erp_ui`:

| | `erp_ui` | `procurex_bundle` |
|---|---|---|
| Frontend source | `frontend/ERP-CUSTOM-UI/` | `frontend/ProcureX/` |
| Vite `outDir` | `../../erp_ui/public/ui` | `../../procurex_bundle/public/procurex` |
| Served at | `/ui` | `/procurex` |
| Backend | N/A | `procurex` (fetched via `bench get-app`) |

---

## Optional `site_config.json` Overrides

```json
{
  "procurex_node_binary":  "bun",
  "procurex_skip_build":   0
}
```

---

## Rebuilding the Frontend Manually

```bash
cd apps/procurex_bundle/frontend/ProcureX
bun run build                         # or: npm run build
# Output lands in: apps/procurex_bundle/procurex_bundle/public/procurex/

bench build --app procurex_bundle
bench --site <site> clear-cache
```
