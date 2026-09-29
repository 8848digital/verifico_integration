# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""PAN fields added to every DocType that has a PAN Verification Rule."""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

PAN_FIELDS = [
	{
		"fieldname": "verifico_pan_number",
		"fieldtype": "Data",
		"label": "PAN Number",
		"length": 10,
		"insert_after": "verifico_section",
		"description": "Verify with the PAN Verification button.",
	},
	{
		"fieldname": "verifico_pan_status",
		"fieldtype": "Select",
		"label": "PAN Status",
		"options": "Not Verified\nValid\nInvalid",
		"default": "Not Verified",
		"read_only": 1,
		"no_copy": 1,
		"in_standard_filter": 1,
		"insert_after": "verifico_pan_number",
	},
	{
		"fieldname": "verifico_pan_verification",
		"fieldtype": "Link",
		"label": "PAN Verification",
		"options": "PAN Verification",
		"read_only": 1,
		"no_copy": 1,
		"insert_after": "verifico_pan_status",
	},
]


def ensure_pan_fields(doctype: str) -> None:
	"""
	Add a "PAN Verification" tab (tabbed forms) or section (plain forms) with
	the PAN, its status and the verification link, after the last field.

	Parameters:
	        doctype (str, required): Reference DocType of a rule.

	Returns:
	        None
	"""
	fields = [
		field for field in frappe.get_meta(doctype).fields if not field.fieldname.startswith("verifico_")
	]
	has_tabs = any(field.fieldtype == "Tab Break" for field in fields)
	container = {
		"fieldname": "verifico_section",
		"fieldtype": "Tab Break" if has_tabs else "Section Break",
		"label": "PAN Verification",
		"insert_after": fields[-1].fieldname if fields else None,
	}
	# Frappe will not change a field's type in place; the container holds no data.
	existing = frappe.db.get_value(
		"Custom Field", {"dt": doctype, "fieldname": "verifico_section"}, ["name", "fieldtype"]
	)
	if existing and existing[1] != container["fieldtype"]:
		frappe.delete_doc("Custom Field", existing[0], ignore_permissions=True)

	create_custom_fields({doctype: [container, *PAN_FIELDS]}, update=True)
