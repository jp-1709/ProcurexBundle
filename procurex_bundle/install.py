"""
procurex_bundle.install
-----------------------
Lifecycle hooks for ProcureX Bundle.

What happens on  bench --site <site> install-app procurex_bundle
----------------------------------------------------------------
1. [BACKEND]   bench get-app procurex  https://github.com/QuantbitERP/ProcureX-Backend.git
               bench --site <site> install-app procurex          ← Frappe handles this via
               required_apps = ["procurex"] in hooks.py

2. [FRONTEND]  git clone https://github.com/QuantbitERP/ProcureX.git
               into  apps/procurex_bundle/frontend/ProcureX/

3. [BUILD]     cd frontend/ProcureX && npm install && npm run build
               Vite writes the built output directly into
               apps/procurex_bundle/procurex_bundle/public/procurex/
               (configured via outDir in the frontend's vite.config.ts)

4. [REGISTER]  bench build --app procurex_bundle
               makes Frappe aware of the new assets

Pattern reference: apps/erp_ui  (ERP-CUSTOM-UI frontend inside erp_ui/frontend/)
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
FRONTEND_REPO   = "https://github.com/QuantbitERP/ProcureX.git"
FRONTEND_BRANCH = "main"

# The frontend is cloned into:
#   <bench>/apps/procurex_bundle/frontend/ProcureX/
# Its vite.config.ts must have:
#   build: { outDir: "../../procurex_bundle/public/procurex" }
FRONTEND_CLONE_DIR_NAME = "ProcureX"


# ---------------------------------------------------------------------------
# Public hook entry points (referenced in hooks.py)
# ---------------------------------------------------------------------------

def after_install():
    """Called once by `bench install-app procurex_bundle`."""
    frappe = _frappe()
    frappe.msgprint("ProcureX Bundle: setting up frontend…", alert=True)
    try:
        _setup_frontend(frappe)
        frappe.msgprint(
            "✅ ProcureX Bundle installed. Open /procurex to launch the app.",
            alert=True,
        )
    except Exception as exc:
        logger.exception("ProcureX Bundle after_install failed")
        frappe.log_error(str(exc), "ProcureX Bundle Install Error")
        frappe.msgprint(
            f"⚠️  ProcureX Bundle frontend setup failed — {exc}\n"
            "Run the steps manually (see README) then: bench build --app procurex_bundle",
            indicator="orange",
            alert=True,
        )


def after_migrate():
    """Called on every `bench migrate` — re-clones / rebuilds if needed."""
    frappe = _frappe()
    try:
        _setup_frontend(frappe)
    except Exception as exc:
        logger.warning("ProcureX Bundle after_migrate setup failed: %s", exc)


def before_uninstall():
    """Remove the built public assets so no stale files remain."""
    bench_path   = _bench_path()
    public_built = os.path.join(
        bench_path, "apps", "procurex_bundle",
        "procurex_bundle", "public", "procurex"
    )
    if os.path.exists(public_built):
        shutil.rmtree(public_built)
        logger.info("ProcureX Bundle: removed built assets at %s", public_built)


# ---------------------------------------------------------------------------
# Core setup — mirrors exactly how erp_ui handles its ERP-CUSTOM-UI frontend
# ---------------------------------------------------------------------------

def _setup_frontend(frappe):
    """
    1. git clone (or pull) ProcureX frontend into frontend/ProcureX/
    2. npm install  (or bun install)
    3. npm run build  → Vite writes directly to procurex_bundle/public/procurex/
    4. bench build --app procurex_bundle
    """
    conf = frappe.conf

    # --- optional overrides via site_config.json or environment ---
    repo_url = (
        conf.get("procurex_frontend_repo")
        or os.environ.get("PROCUREX_FRONTEND_REPO")
        or FRONTEND_REPO
    )
    branch = (
        conf.get("procurex_frontend_branch")
        or os.environ.get("PROCUREX_FRONTEND_BRANCH")
        or FRONTEND_BRANCH
    )
    skip_build = bool(int(
        conf.get("procurex_skip_build", 0)
        or os.environ.get("PROCUREX_SKIP_BUILD", "0")
    ))

    bench_path   = _bench_path()
    app_root     = os.path.join(bench_path, "apps", "procurex_bundle")

    # Where we clone the frontend repo — same layout as erp_ui/frontend/ERP-CUSTOM-UI
    frontend_dir = os.path.join(app_root, "frontend", FRONTEND_CLONE_DIR_NAME)

    # 1. Clone or pull
    _clone_or_pull(repo_url, branch, frontend_dir)

    if skip_build:
        logger.info("ProcureX Bundle: procurex_skip_build=1, skipping npm build")
        return

    # 2. Detect package manager (bun preferred if bun.lock present, else npm)
    node_bin = _detect_node_binary(conf, frontend_dir)

    # 3. Install dependencies
    _run(f"{node_bin} install", cwd=frontend_dir, label="install deps")

    # 4. Build — Vite writes directly into procurex_bundle/public/procurex/
    #    (outDir in vite.config.ts must be set to "../../procurex_bundle/public/procurex")
    _run(f"{node_bin} run build", cwd=frontend_dir, label="vite build")

    # Sanity check — confirm build output landed where expected
    expected_output = os.path.join(
        app_root, "procurex_bundle", "public", "procurex"
    )
    if not os.path.isdir(expected_output):
        raise RuntimeError(
            f"Build did not produce output at {expected_output}.\n"
            f"Make sure the frontend's vite.config.ts has:\n"
            f'  build: {{ outDir: "../../procurex_bundle/public/procurex" }}'
        )

    # 5. Register assets with Frappe
    _run(
        "bench build --app procurex_bundle",
        cwd=bench_path,
        label="bench build",
        check=False,   # non-fatal; assets may already be registered
    )

    logger.info("ProcureX Bundle: frontend ready at /procurex")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clone_or_pull(repo_url: str, branch: str, target_dir: str):
    """Clone the repo if missing, otherwise fetch + reset to latest."""
    if os.path.isdir(os.path.join(target_dir, ".git")):
        logger.info("ProcureX Bundle: pulling latest frontend from %s", repo_url)
        _run(f"git -C {target_dir} fetch origin", label="git fetch")
        _run(
            f"git -C {target_dir} reset --hard origin/{branch}",
            label="git reset",
        )
    else:
        logger.info("ProcureX Bundle: cloning frontend from %s", repo_url)
        parent = os.path.dirname(target_dir)
        os.makedirs(parent, exist_ok=True)
        _run(
            f"git clone --depth 1 --branch {branch} {repo_url} {target_dir}",
            label="git clone",
        )


def _detect_node_binary(conf, cwd: str) -> str:
    """Prefer bun if bun.lock present and bun is on PATH, otherwise use npm."""
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
    """Run a shell command, streaming output to stdout/stderr."""
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
