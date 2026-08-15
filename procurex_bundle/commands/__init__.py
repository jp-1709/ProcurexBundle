import click
import frappe
from frappe.commands import get_site, pass_context


@click.command("procurex-bundle-build-frontend")
@click.option("--update", is_flag=True, default=False, help="Pull the latest frontend source first")
@click.option("--clean", is_flag=True, default=False, help="Reinstall node dependencies from scratch")
@pass_context
def build_frontend(context, update, clean):
	"""Clone/update and build the ProcureX frontend into procurex_bundle's public folder."""
	from procurex_bundle.frontend import setup_frontend

	site = get_site(context)
	frappe.init(site=site)
	frappe.connect()
	try:
		setup_frontend(update=update, clean=clean)
	finally:
		frappe.destroy()


@click.command("procurex-bundle-setup-backend")
@pass_context
def setup_backend_command(context):
	"""Fetch the ProcureX backend app and install it on the site."""
	from procurex_bundle.backend import setup_backend

	site = get_site(context)
	frappe.init(site=site)
	frappe.connect()
	try:
		setup_backend()
	finally:
		frappe.destroy()


commands = [build_frontend, setup_backend_command]
