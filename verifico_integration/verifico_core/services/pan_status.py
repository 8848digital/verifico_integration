# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Read-side helpers for the PAN API: a document's PAN status and API responses."""

import frappe

from verifico_integration.verifico_core.services.enforcement import NOT_VERIFIED
from verifico_integration.verifico_core.services.rule_matcher import matching_rule
from verifico_integration.verifico_core.services.verification_log import (
	LINK_FIELD,
	PAN_FIELD,
	STATUS_FIELD,
	summarize,
)


def document_pan_status(reference_doctype: str, reference_name: str) -> dict:
	"""
	PAN status of a document the user can read, and whether its rule requires one.

	Parameters:
	        reference_doctype (str, required): Document type.
	        reference_name (str, required): Document name.

	Returns:
	        dict: {"required", "action", "threshold_amount", "pan_number", "status", "verification"}
	"""
	doc = frappe.get_doc(reference_doctype, reference_name)
	doc.check_permission("read")
	rule = matching_rule(doc)
	return {
		"required": bool(rule),
		"action": rule["action"] if rule else None,
		"threshold_amount": rule["threshold_amount"] if rule else None,
		"pan_number": doc.get(PAN_FIELD),
		"status": doc.get(STATUS_FIELD) or NOT_VERIFIED,
		"verification": doc.get(LINK_FIELD),
	}


def result_payload(log) -> dict:
	"""
	Arguments for api_response describing a PAN Verification outcome. A failed
	call is returned (not raised) so its audit record is kept.

	Parameters:
	        log (Document, required): PAN Verification record.

	Returns:
	        dict: {"status", "code", "message", "data"}
	"""
	messages = {
		"Valid": "PAN verified as valid",
		"Invalid": "PAN is not valid",
		"Extracted": "PAN details read from the card",
	}
	if log.status == "Failed":
		# 424 (failed dependency): Verifico, not this server, failed. The desk
		# shows 5xx as a generic "Internal Server Error" and would hide the reason.
		return {
			"status": False,
			"code": 424,
			"message": log.error or "PAN verification failed",
			"data": summarize(log),
		}
	return {"status": True, "code": 200, "message": messages[log.status], "data": summarize(log)}
