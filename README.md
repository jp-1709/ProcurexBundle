# ProcureX Bundle

One Frappe app that pulls in both halves of ProcureX and wires them together:

- **Backend** — [ProcureX-Backend](https://github.com/QuantbitERP/ProcureX-Backend) (`procurex`), fetched with `bench get-app` and installed on the site.
- **Frontend** — [ProcureX](https://github.com/QuantbitERP/ProcureX), cloned, built as a static SPA and served by Frappe itself at `/procurex`.

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/jp-1709/ProcurexBundle.git
bench --site <site> install-app procurex_bundle
```

That is the whole setup. `install-app` will:

1. `bench get-app` the backend repo into `apps/procurex` (if it is not there already) and install `procurex` on the site,
2. clone the frontend into `apps/procurex_bundle/frontend/ProcureX`,
3. `npm install` and build it into `apps/procurex_bundle/procurex_bundle/public/procurex`,
4. serve it at `https://<site>/procurex`.

Requirements on the bench host: `git`, and Node.js 20.19+ / 22.12+ with `npm` (the frontend uses Vite 8). The frontend build takes a few minutes.

## How the two halves connect

The SPA is built with `vite base = /assets/procurex_bundle/procurex/` and the TanStack router `basepath = /procurex`, and Frappe serves the prerendered shell for `/procurex/*` through a page renderer. Because the SPA is served by the site itself, its relative `/api/...` calls land on the same Frappe site with the session cookie already attached — no Node server, no PM2, no extra port, no reverse-proxy rules. The renderer also injects `window.csrf_token` (and a `csrf_token` cookie) so writes pass Frappe's CSRF check.

The frontend repository is never patched: the build uses `frontend/procurex-bundle.vite.config.ts` from this app, passed to `vite build --config`.

## Commands

```bash
# rebuild the frontend (e.g. after changing branches or a failed install)
bench --site <site> procurex-bundle-build-frontend [--update] [--clean]

# fetch + install the backend app only
bench --site <site> procurex-bundle-setup-backend
```

## Configuration

Optional overrides in `site_config.json` / `common_site_config.json`:

| Key | Default |
| --- | --- |
| `procurex_bundle_backend_repo` | `https://github.com/QuantbitERP/ProcureX-Backend.git` |
| `procurex_bundle_backend_branch` | `version-16` |
| `procurex_bundle_frontend_repo` | `https://github.com/QuantbitERP/ProcureX.git` |
| `procurex_bundle_frontend_branch` | `main` |
| `procurex_bundle_node_bin` | — (directory containing `node`/`npm`, when not on `PATH`) |
| `procurex_bundle_skip_frontend_build` | `false` (skip the build during `install-app`) |

## License

MIT
