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
BACKEND_BRANCH      = "main"

# The frontend lives at  apps/procurex_bundle/frontend/ProcureX/  (git submodule)
# Its vite.config.ts has outDir: "../../procurex_bundle/public/procurex"
FRONTEND_DIR_NAME   = "ProcureX"


# ---------------------------------------------------------------------------
# Public hook entry points (referenced in hooks.py)
# ---------------------------------------------------------------------------

def after_install():
    """Called once by `bench install-app procurex_bundle`."""
    frappe = _frappe()
    try:
        # Step 1: Install backend Frappe app (procurex) if not already present
        _install_backend(frappe)

        # Step 2: Build the frontend (source already embedded as submodule)
        frappe.msgprint("ProcureX Bundle: building frontend…", alert=True)
        _build_frontend(frappe)

        frappe.msgprint(
            "✅ ProcureX Bundle installed successfully. "
            "Navigate to /procurex to launch the app.",
            alert=True,
        )
    except Exception as exc:
        logger.exception("ProcureX Bundle after_install failed")
        frappe.log_error(str(exc), "ProcureX Bundle Install Error")
        frappe.msgprint(
            f"⚠️  ProcureX Bundle setup failed — {exc}\n"
            "Fix the issue then run: bench build --app procurex_bundle",
            indicator="orange",
            alert=True,
        )


def after_migrate():
    """Called on every `bench migrate` — rebuilds frontend assets if needed."""
    frappe = _frappe()
    try:
        _build_frontend(frappe)
    except Exception as exc:
        logger.warning("ProcureX Bundle after_migrate build failed: %s", exc)


def before_uninstall():
    """Remove the built public assets on uninstall."""
    bench_path   = _bench_path()
    public_built = os.path.join(
        bench_path, "apps", "procurex_bundle",
        "procurex_bundle", "public", "procurex"
    )
    if os.path.exists(public_built):
        shutil.rmtree(public_built)
        logger.info("ProcureX Bundle: removed built assets at %s", public_built)


# ---------------------------------------------------------------------------
# Backend installation
# ---------------------------------------------------------------------------

def _install_backend(frappe):
    """
    Use bench get-app to fetch the procurex backend app from GitHub,
    then install it on the current site — only if not already installed.
    """
    bench_path = _bench_path()
    site       = frappe.local.site

    # Check if already installed on this site
    installed_apps = frappe.get_installed_apps()
    if BACKEND_APP_NAME in installed_apps:
        logger.info("ProcureX Bundle: procurex already installed, skipping")
        return

    frappe.msgprint(
        "ProcureX Bundle: fetching procurex backend app from GitHub…",
        alert=True,
    )

    # Check if the app is already fetched (bench get-app already run)
    backend_app_dir = os.path.join(bench_path, "apps", BACKEND_APP_NAME)
    if not os.path.isdir(backend_app_dir):
        _run(
            f"bench get-app {BACKEND_APP_NAME} {BACKEND_REPO} --branch {BACKEND_BRANCH}",
            cwd=bench_path,
            label="bench get-app procurex",
        )

    # Install the backend app on the current site
    _run(
        f"bench --site {site} install-app {BACKEND_APP_NAME}",
        cwd=bench_path,
        label="bench install-app procurex",
    )

    logger.info("ProcureX Bundle: procurex backend installed on site %s", site)


# ---------------------------------------------------------------------------
# Frontend build — source is already embedded as a git submodule
# ---------------------------------------------------------------------------

def _build_frontend(frappe):
    """
    Build the ProcureX React frontend from  frontend/ProcureX/
    (already in the repo as a git submodule — no git clone needed).

    Vite writes the output directly to  procurex_bundle/public/procurex/
    as configured in frontend/ProcureX/vite.config.ts:
        build: { outDir: "../../procurex_bundle/public/procurex" }
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

    if not os.path.isdir(frontend_dir):
        raise RuntimeError(
            f"Frontend source not found at {frontend_dir}.\n"
            "Make sure you cloned the repo with submodules:\n"
            "  git clone --recurse-submodules <bundle-repo-url>"
        )

    # Detect package manager (bun preferred if bun.lock present, else npm)
    node_bin = _detect_node_binary(conf, frontend_dir)

    # Install dependencies
    _run(f"{node_bin} install", cwd=frontend_dir, label="npm install")

    # Build — Vite writes directly to procurex_bundle/public/procurex/
    _run(f"{node_bin} run build", cwd=frontend_dir, label="npm run build")

    # Sanity check: verify the output landed where we expect
    expected_output = os.path.join(
        app_root, "procurex_bundle", "public", "procurex"
    )
    if not os.path.isdir(expected_output):
        raise RuntimeError(
            f"Build did not produce output at {expected_output}.\n"
            "Check that frontend/ProcureX/vite.config.ts has:\n"
            '  build: { outDir: "../../procurex_bundle/public/procurex" }'
        )

    # Register the built assets with Frappe
    _run(
        "bench build --app procurex_bundle",
        cwd=bench_path,
        label="bench build",
        check=False,  # non-fatal
    )

    logger.info("ProcureX Bundle: frontend built and registered at /procurex")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"ProcureX Bundle: '{label or cmd}' failed (exit {result.returncode})"
        )
    return result


def _frappe():
    """Lazy import so this module is testable without a Frappe context."""
    import frappe as _f
    return _f
