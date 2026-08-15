import frappe

from procurex_bundle.backend import setup_backend
from procurex_bundle.frontend import setup_frontend
from procurex_bundle.utils import log, setting


def before_install():
	"""Bring in the backend app before this app is registered on the site."""
	setup_backend()


def after_install():
	"""Build the frontend. A failure here must not roll back the install."""
	if setting("skip_frontend_build"):
		log("skipping frontend build (procurex_bundle_skip_frontend_build is set)")
		return

	try:
		setup_frontend()
	except Exception:
		frappe.log_error(title="ProcureX frontend build failed")
		log(
			"frontend build failed, the rest of the install is unaffected. Fix the cause and run "
			f"`bench --site {frappe.local.site} procurex-bundle-build-frontend`.\n" + frappe.get_traceback()
		)
