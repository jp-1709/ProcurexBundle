"""Clone and build the ProcureX frontend (https://github.com/QuantbitERP/ProcureX).

The SPA is built as static files into procurex_bundle/public/procurex, which bench serves
as /assets/procurex_bundle/procurex/. `procurex_bundle.renderer` then serves the prerendered
shell for every /procurex/* request, so the frontend talks to the backend over same-origin
/api calls — no Node process, no reverse proxy, no extra port.
"""

import os
import shutil

import frappe

from procurex_bundle.utils import (
	ASSET_BASE,
	FRONTEND_BRANCH,
	FRONTEND_REPO,
	SPA_ROUTE,
	BundleCommandError,
	bundle_root,
	frontend_build_path,
	frontend_source_path,
	log,
	run,
	setting,
)

VITE_CONFIG = "procurex-bundle.vite.config.ts"
MIN_NODE_VERSION = (20, 19)


def frontend_repo() -> str:
	return setting("frontend_repo", FRONTEND_REPO)


def frontend_branch() -> str:
	return setting("frontend_branch", FRONTEND_BRANCH)


def node_bin_path() -> str | None:
	"""Directory holding node/npm/npx, when it is not on the PATH of the frappe process."""
	return setting("node_bin")


def node_env() -> dict:
	path = node_bin_path()
	if not path:
		return {}
	return {"PATH": f"{path}{os.pathsep}{os.environ.get('PATH', '')}"}


def which(program: str) -> str:
	path = node_bin_path()
	if path and os.path.exists(os.path.join(path, program)):
		return os.path.join(path, program)
	return shutil.which(program) or program


def check_node_version():
	output = run([which("node"), "--version"], cwd=bundle_root(), env=node_env()).strip()
	version = tuple(int(part) for part in output.lstrip("v").split(".")[:2])
	if version < MIN_NODE_VERSION:
		frappe.throw(
			f"Node.js {'.'.join(str(v) for v in MIN_NODE_VERSION)}+ is required to build the "
			f"ProcureX frontend, found {output}. Install a newer Node.js, or point "
			f"procurex_bundle_node_bin in site_config.json at one, then run "
			f"`bench --site {frappe.local.site} procurex-bundle-build-frontend`."
		)


def clone_or_update_source(update: bool = False):
	source = frontend_source_path()
	if not os.path.exists(source):
		os.makedirs(os.path.dirname(source), exist_ok=True)
		log(f"cloning frontend from {frontend_repo()} (branch {frontend_branch()})")
		run(
			[
				"git",
				"clone",
				"--branch",
				frontend_branch(),
				"--depth",
				"1",
				frontend_repo(),
				source,
			],
			cwd=bundle_root(),
		)
	elif update:
		log("updating frontend source")
		run(["git", "fetch", "--depth", "1", "origin", frontend_branch()], cwd=source)
		run(["git", "reset", "--hard", f"origin/{frontend_branch()}"], cwd=source)
	else:
		log(f"frontend source already present at {source}")


def install_dependencies(source: str, clean: bool = False):
	if clean:
		shutil.rmtree(os.path.join(source, "node_modules"), ignore_errors=True)
		# npm's optional-dependency bug (npm/cli#4828) makes the lockfile skip the rolldown
		# native binding for this platform; regenerating it pulls the right one in.
		lockfile = os.path.join(source, "package-lock.json")
		if os.path.exists(lockfile):
			os.remove(lockfile)

	log("installing frontend dependencies (this takes a few minutes)")
	run([which("npm"), "install", "--no-audit", "--no-fund"], cwd=source, env=node_env())


def build(source: str):
	shutil.copyfile(
		os.path.join(bundle_root(), "frontend", VITE_CONFIG),
		os.path.join(source, VITE_CONFIG),
	)
	env = {
		"PROCUREX_ASSET_BASE": ASSET_BASE,
		"PROCUREX_BASEPATH": f"/{SPA_ROUTE}",
		"NODE_ENV": "production",
		**node_env(),
	}
	log("building frontend")
	run([which("npx"), "vite", "build", "--config", VITE_CONFIG], cwd=source, env=env)


def publish(source: str):
	"""Move the built SPA into the app's public folder, where bench serves it from."""
	client = os.path.join(source, "dist", "client")
	shell = os.path.join(client, "_shell.html")
	if not os.path.exists(shell):
		frappe.throw(f"Frontend build did not produce {shell}")

	target = frontend_build_path()
	shutil.rmtree(target, ignore_errors=True)
	shutil.copytree(client, target)
	os.replace(os.path.join(target, "_shell.html"), os.path.join(target, "index.html"))
	log(f"published frontend to {target}")


def link_assets():
	"""bench serves sites/assets/<app> from apps/<app>/<app>/public."""
	from procurex_bundle.utils import bench_path

	target = os.path.join(frappe.get_app_path("procurex_bundle"), "public")
	link = os.path.join(bench_path(), "sites", "assets", "procurex_bundle")
	if os.path.islink(link) or os.path.exists(link):
		return

	os.makedirs(os.path.dirname(link), exist_ok=True)
	os.symlink(target, link)
	log(f"linked {link} -> {target}")


def setup_frontend(update: bool = False, clean: bool = False):
	check_node_version()
	clone_or_update_source(update=update)
	source = frontend_source_path()

	install_dependencies(source, clean=clean)
	try:
		build(source)
	except BundleCommandError as e:
		if "Cannot find native binding" not in (e.output or "") or clean:
			raise
		log("retrying build with a clean dependency install")
		install_dependencies(source, clean=True)
		build(source)

	publish(source)
	link_assets()
