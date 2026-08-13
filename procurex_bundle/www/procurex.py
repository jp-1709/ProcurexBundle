"""
procurex_bundle.www.procurex
-----------------------------
Serves the ProcureX SPA at /procurex.

Approach (matching erp_ui pattern):
- The built Vite output lands in  procurex_bundle/public/procurex/
- Frappe serves it under          /assets/procurex_bundle/procurex/
- This page context reads the built index.html, extracts hashed asset
  filenames (so they always match whatever Vite produced), and injects
  the Frappe CSRF token.
"""

import os
import re

import frappe


def get_context(context):
    # Expose CSRF token — same as erp_ui/www/ui.py
    context["csrf_token"] = frappe.sessions.get_csrf_token()

    # Dynamically discover the hashed JS and CSS filenames from the built index.html
    # so the template stays correct across rebuilds without manual updates.
    context["procurex_js"]  = ""
    context["procurex_css"] = ""

    built_index = _built_index_path()
    if os.path.isfile(built_index):
        try:
            html = open(built_index).read()
            # Extract  src="assets/index-XXXX.js"
            js_match  = re.search(r'src=["\'](?:/[^"\']*)?assets/([^"\']+\.js)["\']', html)
            css_match = re.search(r'href=["\'](?:/[^"\']*)?assets/([^"\']+\.css)["\']', html)
            if js_match:
                context["procurex_js"]  = f"/assets/procurex_bundle/procurex/assets/{js_match.group(1)}"
            if css_match:
                context["procurex_css"] = f"/assets/procurex_bundle/procurex/assets/{css_match.group(1)}"
        except Exception:
            frappe.log_error(frappe.get_traceback(), "ProcureX Bundle: failed to parse built index.html")

    return context


def _built_index_path() -> str:
    """
    Returns the absolute path to the Vite-built index.html.
    Location: <bench>/apps/procurex_bundle/procurex_bundle/public/procurex/index.html
    """
    return os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),   # www/
            "..",                         # procurex_bundle/
            "public",
            "procurex",
            "index.html",
        )
    )
