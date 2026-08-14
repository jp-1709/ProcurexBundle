"""
procurex_bundle.install
-----------------------
Lifecycle hooks for ProcureX Bundle.

What happens on  bench --site <site> install-app procurex_bundle
----------------------------------------------------------------
1. [BACKEND]   bench get-app procurex https://github.com/QuantbitERP/ProcureX-Backend.git
               bench --site <site> install-app procurex
               (only if procurex is not already installed on this site)

2. [FRONTEND]  The ProcureX frontend source is already embedded in this repo at
               frontend/ProcureX/  (git submodule — no git clone needed here)

               cd frontend/ProcureX && npm install && npm run build
               Vite writes the built output directly into:
               apps/procurex_bundle/procurex_bundle/public/procurex/
               (configured in frontend/ProcureX/vite.config.ts via outDir)

3. [REGISTER]  bench build --app procurex_bundle

Pattern reference: apps/erp_ui  (ERP-CUSTOM-UI embedded at erp_ui/frontend/ERP-CUSTOM-UI/,
                   builds directly to erp_ui/public/ui/ via vite.config.ts outDir)
"""

import logging
import os
import shutil
import subprocess
import sys

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Repository constants
# ---------------------------------------------------------------------------
BACKEND_REPO        = "https://github.com/QuantbitERP/ProcureX-Backend.git"
BACKEND_APP_NAME    = "procurex"
# No branch specified — bench will auto-detect the repo's default branch

# The frontend lives at  apps/procurex_bundle/frontend/ProcureX/  (git submodule)
# Its vite.config.ts has outDir: "../../procurex_bundle/public/procurex"
FRONTEND_DIR_NAME   = "ProcureX"


# ---------------------------------------------------------------------------
# Public hook entry points (referenced in hooks.py)
# ---------------------------------------------------------------------------

def before_install():
    """
    Called before procurex_bundle is installed on the site.
    1. Ensures procurex backend app is fetched into the bench apps/ directory and installed.
    2. Ensures frontend/ProcureX source is populated (git submodule or clone).
    """
    frappe = _frappe()
    _install_backend(frappe)

    bench_path   = _bench_path()
    app_root     = os.path.join(bench_path, "apps", "procurex_bundle")
    frontend_dir = os.path.join(app_root, "frontend", FRONTEND_DIR_NAME)
    _ensure_frontend_source(app_root, frontend_dir)


def after_install():
    """Called once after procurex_bundle is installed."""
    frappe = _frappe()
    frappe.msgprint(
        "✅ ProcureX Bundle installed successfully.",
        alert=True,
    )


def after_migrate():
    """Called on every bench migrate."""
    pass


def before_uninstall():
    """Remove built public assets on uninstall."""
    bench_path = _bench_path()
    public_built = os.path.join(
        bench_path, "apps", "procurex_bundle",
        "procurex_bundle", "public", "procurex"
    )
    if os.path.exists(public_built):
        shutil.rmtree(public_built)
        logger.info("ProcureX Bundle: removed built assets at %s", public_built)


# ---------------------------------------------------------------------------
# Backend fetching & installation
# ---------------------------------------------------------------------------

def _install_backend(frappe):
    """
    Fetch procurex backend app via bench get-app if missing from bench,
    then install it on the current site using frappe.installer.install_app() directly.

    Why direct frappe.installer.install_app() call?
    ----------------------------------------------
    Calling `bench --site install-app` from inside Python triggers CLI filelocks.
    Calling `frappe.installer.install_app("procurex")` directly runs inside the
    active site session and installs procurex without any lock collisions.
    """
    bench_path = _bench_path()

    # Step 1 — Fetch app to bench if apps/procurex missing
    backend_app_dir = os.path.join(bench_path, "apps", BACKEND_APP_NAME)
    if not os.path.isdir(backend_app_dir):
        frappe.msgprint(
            "ProcureX Bundle: fetching procurex backend app from GitHub…",
            alert=True,
        )
        _run(
            f"bench get-app {BACKEND_APP_NAME} {BACKEND_REPO}",
            cwd=bench_path,
            label="bench get-app procurex",
        )
        logger.info("ProcureX Bundle: procurex backend fetched to bench")

    # Step 2 — Install procurex on the current site if not already installed
    installed_apps = frappe.get_installed_apps()
    if BACKEND_APP_NAME not in installed_apps:
        frappe.msgprint(
            "ProcureX Bundle: installing procurex backend on site…",
            alert=True,
        )
        try:
            import sys
            import importlib
            if backend_app_dir not in sys.path:
                sys.path.insert(0, backend_app_dir)
            importlib.invalidate_caches()

            from frappe.installer import install_app as _frappe_install_app
            _frappe_install_app(BACKEND_APP_NAME)
            logger.info("ProcureX Bundle: procurex backend installed successfully on site")
        except Exception as exc:
            logger.exception("ProcureX Bundle: failed to install backend procurex app")
            raise RuntimeError(
                f"ProcureX Bundle: failed to install procurex backend on site — {exc}"
            ) from exc





# ---------------------------------------------------------------------------
# Frontend build — source is already embedded as a git submodule
# ---------------------------------------------------------------------------

def _build_frontend(frappe):
    """
    Build the ProcureX React/TanStack Start frontend from  frontend/ProcureX/
    (already in the repo as a git submodule — no git clone needed).

    TanStack Start build output structure
    --------------------------------------
    `npm run build` (via @lovable.dev/vite-tanstack-config + nitro) produces:

        frontend/ProcureX/.output/
            public/         ← static client-side assets (JS, CSS, favicon)
                assets/
                    index-[hash].js
                    index-[hash].css
                    ...
            server/         ← Node.js SSR server (NOT used by Frappe)

    We copy  .output/public/  →  procurex_bundle/public/procurex/
    Frappe then serves these at  /assets/procurex_bundle/procurex/
    and our www/procurex.html shell loads them.
    """
    conf = frappe.conf

    skip_build = bool(int(
        conf.get("procurex_skip_build", 0)
        or os.environ.get("PROCUREX_SKIP_BUILD", "0")
    ))
    if skip_build:
        logger.info("ProcureX Bundle: procurex_skip_build=1, skipping build")
        return

    bench_path   = _bench_path()
    app_root     = os.path.join(bench_path, "apps", "procurex_bundle")

    # Frontend source — embedded at  apps/procurex_bundle/frontend/ProcureX/
    frontend_dir = os.path.join(app_root, "frontend", FRONTEND_DIR_NAME)

    # Automatically initialize git submodule or clone frontend if missing/empty
    _ensure_frontend_source(app_root, frontend_dir)


    # Detect package manager (bun preferred if bun.lock present AND bun is on PATH)
    node_bin = _detect_node_binary(conf, frontend_dir)

    # Step 1 — Install dependencies (ensure devDependencies like vite are included)
    install_cmd = f"{node_bin} install --include=dev" if node_bin == "npm" else f"{node_bin} install"
    _run(install_cmd, cwd=frontend_dir, label=f"{node_bin} install")

    # Step 2 — Build
    # TanStack Start writes its output to  frontend/ProcureX/.output/
    _run(f"{node_bin} run build", cwd=frontend_dir, label=f"{node_bin} run build")


    # Step 3 — Copy .output/public/ → procurex_bundle/public/procurex/
    #
    # TanStack Start produces:
    #   .output/public/   ← static assets Frappe needs to serve
    #   .output/server/   ← SSR Node server (not used here)
    #
    built_public = os.path.join(frontend_dir, ".output", "public")
    if not os.path.isdir(built_public):
        raise RuntimeError(
            f"Build did not produce .output/public/ at {built_public}.\n"
            "Expected TanStack Start output structure:\n"
            "  .output/public/assets/index-[hash].js\n"
            "  .output/public/assets/index-[hash].css"
        )

    dest_public = os.path.join(
        app_root, "procurex_bundle", "public", "procurex"
    )
    if os.path.exists(dest_public):
        shutil.rmtree(dest_public)
    shutil.copytree(built_public, dest_public)
    logger.info(
        "ProcureX Bundle: copied .output/public/ → %s", dest_public
    )

    # Step 4 — Register the built assets with Frappe
    # Use bench CLI (bench build handles yarn/esbuild asset linking)
    _run(
        "bench build --app procurex_bundle",
        cwd=bench_path,
        label="bench build --app procurex_bundle",
        check=False,  # non-fatal — assets may already be linked
    )

    logger.info("ProcureX Bundle: frontend built and assets registered at /assets/procurex_bundle/procurex/")




# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_frontend_source(app_root: str, frontend_dir: str):
    """
    Ensures that the ProcureX frontend source code exists at frontend/ProcureX/.
    If package.json is missing (e.g. when app was cloned without --recurse-submodules via bench get-app):
      1. Tries `git submodule update --init --recursive`
      2. If still missing, falls back to cloning ProcureX directly into frontend/ProcureX/
    """
    package_json = os.path.join(frontend_dir, "package.json")
    if os.path.isfile(package_json):
        return

    logger.info("ProcureX Bundle: frontend source missing package.json, initializing git submodule...")

    # Step 1: Attempt git submodule update
    if os.path.isdir(os.path.join(app_root, ".git")):
        _run(
            "git submodule update --init --recursive",
            cwd=app_root,
            label="git submodule update",
            check=False,
        )

    # Step 2: If package.json is still missing, fallback to direct git clone
    if not os.path.isfile(package_json):
        logger.info("ProcureX Bundle: cloning ProcureX frontend repository...")
        if os.path.exists(frontend_dir):
            if os.path.isdir(frontend_dir):
                shutil.rmtree(frontend_dir, ignore_errors=True)
            else:
                try:
                    os.remove(frontend_dir)
                except Exception:
                    pass
        os.makedirs(os.path.dirname(frontend_dir), exist_ok=True)
        _run(
            f'git clone --depth 1 https://github.com/QuantbitERP/ProcureX.git "{frontend_dir}"',
            label="git clone frontend",
        )


    if not os.path.isfile(package_json):
        raise RuntimeError(
            f"ProcureX Bundle: Failed to fetch frontend source code into {frontend_dir}.\n"
            "Please check git / internet access and try again."
        )


def _detect_node_binary(conf, cwd: str) -> str:

    """Prefer bun if bun.lock is present and bun is on PATH, otherwise use npm."""
    override = conf.get("procurex_node_binary") or os.environ.get("PROCUREX_NODE_BINARY")
    if override:
        return override
    if os.path.exists(os.path.join(cwd, "bun.lock")) and shutil.which("bun"):
        return "bun"
    return "npm"


def _bench_path() -> str:
    """
    Return the absolute bench root path.
    __file__ lives at <bench>/apps/procurex_bundle/procurex_bundle/install.py
    """
    return os.path.realpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )


def _run(cmd: str, cwd: str = None, label: str = "", check: bool = True):
    """Run a shell command, streaming output, raising RuntimeError on failure."""
    logger.info("ProcureX Bundle [%s]: %s", label or cmd, cmd)

    # Ensure NODE_ENV is development so npm does not omit devDependencies like vite
    cmd_env = os.environ.copy()
    cmd_env["NODE_ENV"] = "development"

    result = subprocess.run(cmd, shell=True, cwd=cwd, env=cmd_env)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"ProcureX Bundle: '{label or cmd}' failed (exit {result.returncode})"
        )
    return result



def _frappe():
    """Lazy import so this module is testable without a Frappe context."""
    import frappe as _f
    return _f
