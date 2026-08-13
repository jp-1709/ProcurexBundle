"""
procurex_bundle.www.procurex
-----------------------------
Serves the ProcureX SPA shell at /procurex.

The ProcureX frontend is built with TanStack Start (SSR framework).
The static client assets from .output/public/ are copied to
procurex_bundle/public/procurex/ during installation and served by
Frappe under /assets/procurex_bundle/procurex/.

This page context:
  1. Exposes the Frappe CSRF token (same as erp_ui/www/ui.py)
  2. Dynamically resolves the hashed JS/CSS filenames from the built
     assets directory so the template always loads the correct files
     regardless of build hash changes.
"""

import os
import re

import frappe


def get_context(context):
    # Expose CSRF token — same as erp_ui/www/ui.py
    context["csrf_token"] = frappe.sessions.get_csrf_token()

    # Resolve hashed asset filenames from the copied build output
    context["procurex_js"]  = ""
    context["procurex_css"] = ""

    assets_dir = _assets_dir()
    if os.path.isdir(assets_dir):
        try:
            files = os.listdir(assets_dir)

            # Main JS entry — named index-[hash].js by rollupOptions config
            js_files = [f for f in files if re.match(r"^index-[^.]+\.js$", f)]
            if js_files:
                context["procurex_js"] = (
                    f"/assets/procurex_bundle/procurex/assets/{js_files[0]}"
                )

            # Main CSS entry — named index-[hash].css (may not exist if Tailwind
            # injects via JS; the template handles the empty-string case)
            css_files = [f for f in files if re.match(r"^index-[^.]+\.css$", f)]
            if css_files:
                context["procurex_css"] = (
                    f"/assets/procurex_bundle/procurex/assets/{css_files[0]}"
                )

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "ProcureX Bundle: failed to resolve built asset filenames",
            )

    return context


def _assets_dir() -> str:
    """
    Absolute path to the copied build assets.
    Location: <bench>/apps/procurex_bundle/procurex_bundle/public/procurex/assets/
    """
    return os.path.realpath(
        os.path.join(
            os.path.dirname(__file__),  # www/
            "..",                        # procurex_bundle/
            "public",
            "procurex",
            "assets",
        )
    )
