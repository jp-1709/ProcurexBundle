from . import __version__


def get_config():
    return [
        {
            "label": "ProcureX Bundle",
            "icon": "fa fa-box",
            "items": [
                {
                    "type": "doctype",
                    "name": "ProcureX Bundle Settings",
                    "description": "Configure ProcureX Bundle",
                }
            ],
        }
    ]
