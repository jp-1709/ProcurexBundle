app_name = "procurex_bundle"
app_title = "ProcureX Bundle"
app_publisher = "Quantbit Technologies Pvt Ltd"
app_description = "Installs and wires up the ProcureX backend app and the ProcureX frontend"
app_email = "contact@quantbit.io"
app_license = "mit"

# Apps
# ------------------

add_to_apps_screen = [
	{
		"name": "procurex_bundle",
		"logo": "/assets/procurex_bundle/procurex/favicon.ico",
		"title": "ProcureX",
		"route": "/procurex",
	}
]

# Website
# ------------------

# Serves the prerendered SPA shell for /procurex and every route below it.
page_renderer = ["procurex_bundle.renderer.ProcureXSPARenderer"]

# Installation
# ------------

before_install = "procurex_bundle.install.before_install"
after_install = "procurex_bundle.install.after_install"
