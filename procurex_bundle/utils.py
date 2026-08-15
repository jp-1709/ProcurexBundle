import os
import subprocess

import frappe

BACKEND_APP = "procurex"
BACKEND_REPO = "https://github.com/QuantbitERP/ProcureX-Backend.git"
BACKEND_BRANCH = "version-16"

FRONTEND_REPO = "https://github.com/QuantbitERP/ProcureX.git"
FRONTEND_BRANCH = "main"
FRONTEND_DIR = "ProcureX"

# URL path the SPA is served from, and the asset base it is built with.
SPA_ROUTE = "procurex"
ASSET_BASE = "/assets/procurex_bundle/procurex/"


def setting(key, default=None):
	"""Read an override from site_config.json / common_site_config.json."""
	value = frappe.conf.get(f"procurex_bundle_{key}")
	return default if value in (None, "") else value


def bench_path() -> str:
	return os.path.abspath(frappe.utils.get_bench_path())


def apps_path() -> str:
	return os.path.join(bench_path(), "apps")


def bundle_root() -> str:
	"""Repository root of this app (apps/procurex_bundle)."""
	return os.path.abspath(os.path.join(frappe.get_app_path("procurex_bundle"), ".."))


def frontend_source_path() -> str:
	return os.path.join(bundle_root(), "frontend", FRONTEND_DIR)


def frontend_build_path() -> str:
	"""Where the built SPA lives: served as /assets/procurex_bundle/procurex/."""
	return os.path.join(frappe.get_app_path("procurex_bundle"), "public", "procurex")


def spa_index_path() -> str:
	return os.path.join(frontend_build_path(), "index.html")


def log(message: str):
	print(f"[procurex_bundle] {message}", flush=True)


def run(command: list[str], cwd: str, env: dict | None = None, timeout: int = 3600) -> str:
	"""Run a command, streaming nothing but capturing output; raise with output on failure."""
	log(f"$ {' '.join(command)}  (in {cwd})")
	process_env = os.environ.copy()
	if env:
		process_env.update(env)

	result = subprocess.run(
		command,
		cwd=cwd,
		env=process_env,
		timeout=timeout,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
		text=True,
	)
	if result.returncode != 0:
		raise BundleCommandError(command, result.returncode, result.stdout)
	return result.stdout


class BundleCommandError(Exception):
	def __init__(self, command: list[str], returncode: int, output: str):
		self.command = command
		self.returncode = returncode
		self.output = output
		tail = "\n".join((output or "").strip().splitlines()[-40:])
		super().__init__(f"`{' '.join(command)}` failed with exit code {returncode}:\n{tail}")
