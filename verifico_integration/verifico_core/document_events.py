# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""
doc_events "*" targets: every save on the site passes through here, so each
handler exits after one cached set lookup unless the DocType has a PAN rule.
"""

from verifico_integration.verifico_core.services.enforcement import enforce_rule, sync_pan_status
from verifico_integration.verifico_core.services.rule_matcher import get_rule_doctypes


def validate(doc, method=None):
	"""
	Refresh the PAN status from the PAN field, then apply "Check On: Save" rules.

	Parameters:
	        doc (Document, required): The document being saved.
	        method (str, optional): Hook name passed by Frappe.

	Returns:
	        None
	"""
	if doc.doctype in get_rule_doctypes():
		sync_pan_status(doc)
		enforce_rule(doc, "Save")


def before_submit(doc, method=None):
	"""
	Apply "Check On: Submit" rules.

	Parameters:
	        doc (Document, required): The document being submitted.
	        method (str, optional): Hook name passed by Frappe.

	Returns:
	        None
	"""
	if doc.doctype in get_rule_doctypes():
		enforce_rule(doc, "Submit")
