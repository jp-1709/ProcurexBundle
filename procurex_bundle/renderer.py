"""Serve the prerendered ProcureX SPA shell for /procurex and every route below it."""

import os

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from frappe.website.utils import build_response

from procurex_bundle.utils import SPA_ROUTE, spa_index_path

NOT_BUILT_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ProcureX</title></head>
<body style="font-family: system-ui, sans-serif; padding: 3rem; max-width: 46rem">
<h1>ProcureX frontend is not built yet</h1>
<p>Run this on the bench host and reload:</p>
<pre style="background:#f4f5f6;padding:1rem;border-radius:6px">bench --site {site} procurex-bundle-build-frontend</pre>
</body></html>"""


class ProcureXSPARenderer(BaseRenderer):
	def can_render(self) -> bool:
		path = (self.path or "").strip("/")
		return path == SPA_ROUTE or path.startswith(f"{SPA_ROUTE}/")

	def render(self):
		return build_response(self.path, self.get_html(), 200, {"Cache-Control": "no-store"})

	def get_html(self) -> str:
		index = spa_index_path()
		if not os.path.exists(index):
			return NOT_BUILT_HTML.format(site=frappe.local.site)

		with open(index, encoding="utf-8") as f:
			html = f.read()

		return html.replace("</head>", f"{session_script()}</head>", 1)


def session_script() -> str:
	"""Hand the SPA a CSRF token so its fetch wrapper can call /api as the logged-in user."""
	csrf_token = frappe.sessions.get_csrf_token()
	return (
		"<script>"
		f"window.csrf_token={frappe.as_json(csrf_token)};"
		f"window.frappe_user={frappe.as_json(frappe.session.user)};"
		f"document.cookie='csrf_token='+encodeURIComponent({frappe.as_json(csrf_token)})+';path=/';"
		"</script>"
	)
