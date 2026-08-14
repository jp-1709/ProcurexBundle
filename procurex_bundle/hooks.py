app_name = "procurex_bundle"
app_title = "ProcureX Bundle"
app_publisher = "Quantbit Technologies Pvt Ltd"
app_description = "Bundles ProcureX frontend and backend into a single installable Frappe app"
app_email = "contact@quantbit.io"
app_license = "mit"
app_version = "0.0.1"

# ---------------------------------------------------------------------------
# Note: Backend app (procurex) is fetched via bench get-app and installed
# on the site directly in before_install hook in install.py.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Website Route Rules
# Redirect all deep-links under /procurex/* back to the procurex page so
# the React/TanStack client-side router handles them.
# ---------------------------------------------------------------------------
website_route_rules = [
    {"from_route": "/procurex/<path:app_path>", "to_route": "procurex"},
]

# ---------------------------------------------------------------------------
# Apps Screen entry — shows ProcureX as a tile on the Frappe desk
# ---------------------------------------------------------------------------
add_to_apps_screen = [
    {
        "name": "procurex_bundle",
        "logo": "/assets/procurex_bundle/images/logo.png",
        "title": "ProcureX",
        "route": "/procurex",
    }
]

# ---------------------------------------------------------------------------
# Installation Hooks
# ---------------------------------------------------------------------------
before_install = "procurex_bundle.install.before_install"
after_install = "procurex_bundle.install.after_install"
after_migrate = "procurex_bundle.install.after_migrate"

# ---------------------------------------------------------------------------
# Uninstallation Hooks
# ---------------------------------------------------------------------------
before_uninstall = "procurex_bundle.install.before_uninstall"

