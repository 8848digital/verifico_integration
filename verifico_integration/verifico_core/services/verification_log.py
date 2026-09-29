# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""PAN Verification records: normalise PANs, reuse recent results, link results to documents."""

import json
import re

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
STATUS_FIELD = "verifico_pan_status"
LINK_FIELD = "verifico_pan_verification"
PAN_FIELD = "verifico_pan_number"


def normalize_pan(pan_number: str | None) -> str:
	"""
	Upper-case, strip and validate a PAN before any credit is spent.
	e.g. " abcde1234f " -> "ABCDE1234F"

	Parameters:
	        pan_number (str, optional): PAN as typed or read from a card.

	Returns:
	        str: Normalized PAN.
	"""
	pan = (pan_number or "").strip().upper()
	if not pan:
		frappe.throw(_("PAN Number is required"))
	if not PAN_PATTERN.match(pan):
		frappe.throw(
			_("{0} is not a valid PAN format (5 letters, 4 digits, 1 letter, e.g. ABCDE1234F)").format(pan)
		)
	return pan


def find_reusable(pan: str) -> str | None:
	"""
	A recent Valid result for the same PAN (within "Reuse Valid Result For"),
	so the same customer is not charged for twice.

	Parameters:
	        pan (str, required): Normalized PAN.

	Returns:
	        str | None: PAN Verification name to reuse.
	"""
	days = frappe.db.get_single_value("Verifico Settings", "reuse_valid_days") or 0
	if days <= 0:
		return None
	return frappe.db.get_value(
		"PAN Verification",
		{
			"pan_number": pan,
			"status": "Valid",
			"reused_from": ["is", "not set"],
			"verified_on": [">=", add_days(now_datetime(), -days)],
		},
		order_by="verified_on desc",
	)


def create_log(context: dict, values: dict) -> frappe._dict:
	"""
	Insert a PAN Verification record (system-created, read-only for users).

	Parameters:
	        context (dict, required): {"reference_doctype", "reference_name", "party_doctype", "party"}.
	        values (dict, required): Result fields (pan_number, status, source, ...).

	Returns:
	        frappe._dict: The saved record.
	"""
	doc = frappe.get_doc(
		{
			"doctype": "PAN Verification",
			**context,
			**values,
			"verified_by": frappe.session.user,
			"verified_on": now_datetime(),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def link_to_reference(context: dict, log) -> None:
	"""
	Store the PAN, the verification and its status on the reference document
	without re-running its hooks. Card-only (Extracted) results are not linked.

	Parameters:
	        context (dict, required): Reference and party of the request.
	        log (Document, required): PAN Verification record.

	Returns:
	        None
	"""
	if log.status not in ("Valid", "Invalid") or not context.get("reference_name"):
		return
	values = {PAN_FIELD: log.pan_number, LINK_FIELD: log.name, STATUS_FIELD: log.status}
	meta = frappe.get_meta(context["reference_doctype"])
	values = {field: value for field, value in values.items() if meta.has_field(field)}
	if values:
		frappe.db.set_value(
			context["reference_doctype"], context["reference_name"], values, update_modified=False
		)


def summarize(log) -> dict:
	"""
	API-friendly summary of a PAN Verification.

	Parameters:
	        log (Document, required): PAN Verification record.

	Returns:
	        dict: Key result fields.
	"""
	fields = ("name", "pan_number", "status", "full_name", "date_of_birth", "category")
	summary = {field: log.get(field) for field in fields}
	summary.update(
		{
			"aadhaar_seeding_status": log.aadhaar_seeding_status,
			"credits_used": log.credits_used or 0,
			"reused": bool(log.reused_from),
			"ocr_name": log.ocr_name,
			"error": log.error,
		}
	)
	return summary


def failure_values(error) -> dict:
	"""
	Map a Verifico error to PAN Verification fields. Verifico reports an
	unknown PAN as success=false "Verification failed: Invalid PAN" (not as
	status "invalid"), so that answer is an Invalid result, not a failure.

	Parameters:
	        error (VerificoError, required): Error raised by the client.

	Returns:
	        dict: status, error, credits_used and the raw reply.
	"""
	invalid_pan = error.answered and "invalid pan" in str(error).lower()
	return {
		"status": "Invalid" if invalid_pan else "Failed",
		"error": str(error),
		"credits_used": error.payload.get("credits_used") or 0,
		"response": json.dumps(error.payload, indent=1) if error.payload else None,
	}
