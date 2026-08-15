"""Fetch and install the ProcureX backend app (https://github.com/QuantbitERP/ProcureX-Backend)."""

import importlib
import os
import shutil
import sys

import frappe

from procurex_bundle.utils import (
	BACKEND_APP,
	BACKEND_BRANCH,
	BACKEND_REPO,
	apps_path,
	bench_path,
	log,
	run,
	setting,
)


def backend_repo() -> str:
	return setting("backend_repo", BACKEND_REPO)


def backend_branch() -> str:
	return setting("backend_branch", BACKEND_BRANCH)


def backend_app_path() -> str:
	return os.path.join(apps_path(), BACKEND_APP)


def bench_executable() -> str:
	"""`bench` from the bench's own virtualenv, falling back to whatever is on PATH."""
	env_bench = os.path.join(bench_path(), "env", "bin", "bench")
	if os.path.exists(env_bench):
		return env_bench
	return shutil.which("bench") or "bench"


def pip_executable() -> str:
	env_pip = os.path.join(bench_path(), "env", "bin", "pip")
	return env_pip if os.path.exists(env_pip) else shutil.which("pip") or "pip"


def fetch_backend_source():
	"""`bench get-app` the backend into apps/procurex if it is not there yet."""
	if os.path.exists(backend_app_path()):
		log(f"backend app source already present at {backend_app_path()}")
		ensure_backend_installed_in_env()
		return

	log(f"fetching backend app from {backend_repo()} (branch {backend_branch()})")
	run(
		[
			bench_executable(),
			"get-app",
			backend_repo(),
			"--branch",
			backend_branch(),
			"--skip-assets",
		],
		cwd=bench_path(),
	)
	ensure_backend_installed_in_env()


def ensure_backend_installed_in_env():
	"""Make `import procurex` work in this very process, and in the bench env."""
	app_dir = backend_app_path()
	if app_dir not in sys.path:
		sys.path.insert(0, app_dir)
	importlib.invalidate_caches()

	try:
		importlib.import_module(BACKEND_APP)
	except ImportError:
		log("backend app is not installed in the bench environment, installing it now")
		run([pip_executable(), "install", "--quiet", "--upgrade", "-e", app_dir], cwd=bench_path())
		importlib.invalidate_caches()
		importlib.import_module(BACKEND_APP)

	register_in_apps_txt()
	frappe.clear_cache()


def register_in_apps_txt():
	"""bench keeps the list of available apps in sites/apps.txt; make sure ours is there."""
	apps_txt = os.path.join(bench_path(), "sites", "apps.txt")
	if not os.path.exists(apps_txt):
		return

	with open(apps_txt) as f:
		apps = [app.strip() for app in f.read().splitlines() if app.strip()]

	if BACKEND_APP not in apps:
		apps.append(BACKEND_APP)
		with open(apps_txt, "w") as f:
			f.write("\n".join(apps) + "\n")


def install_backend_on_site():
	"""Install the backend app on the site currently being installed into."""
	if BACKEND_APP in frappe.get_installed_apps():
		log(f"{BACKEND_APP} is already installed on {frappe.local.site}")
		return

	from frappe.installer import install_app

	log(f"installing {BACKEND_APP} on {frappe.local.site}")
	install_app(BACKEND_APP, verbose=True)
	frappe.db.commit()


def setup_backend():
	fetch_backend_source()
	install_backend_on_site()
