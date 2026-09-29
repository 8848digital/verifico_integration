# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

app_name = "verifico_integration"
app_title = "Verifico Integration"
app_publisher = "8848 Digital LLP"
app_description = "Verifico integration for Frappe/ERPNext"
app_email = "mahak@8848digital.com"
app_license = "Proprietary"

custom_fixtures = [{"dt": "Custom Field", "filters": {"module": "Verifico Core"}}]

commands = ["verifico_integration.commands.export_fixtures.export_fixtures"]

after_request = [
	"verifico_integration.utils.api_handlers.response_formatter.format_frappe_response_to_custom"
]

# Uncomment and point at the conventional locations as features are added
# (see CLAUDE.md "Key Conventions"):
#
# after_install = "verifico_integration.install.after_install"
#
# doc_events = {
# 	"<DocType>": {
# 		"on_update": "verifico_integration.verifico_core.customization.<doctype>.<doctype>.on_update"
# 	}
# }
#
# scheduler_events = {
# 	"hourly": ["verifico_integration.verifico_core.tasks.hourly"],
# }
