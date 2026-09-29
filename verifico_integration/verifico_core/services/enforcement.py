# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Keep a document's PAN status in line with its PAN field, and enforce the rule."""

import frappe
from frappe import _
from frappe.utils import add_days, fmt_money, now_datetime

from verifico_integration.verifico_core.services.rule_matcher import matching_rule
from verifico_integration.verifico_core.services.verification_log import (
	LINK_FIELD,
	PAN_FIELD,
	PAN_PATTERN,
	STATUS_FIELD,
)

NOT_VERIFIED = "Not Verified"


def sync_pan_status(doc) -> None:
	"""
	Derive the status from the PAN typed on the document: the newest recent
	result for that PAN (e.g. verified before the first save), else the
	document's own earlier result, else "Not Verified". Editing the PAN
	therefore always resets the status.

	Parameters:
	        doc (Document, required): Document with the PAN verification fields.

	Returns:
	        None
	"""
	pan = (doc.get(PAN_FIELD) or "").strip().upper()
	doc.set(PAN_FIELD, pan or None)
	if pan and not PAN_PATTERN.match(pan):
		frappe.throw(_("{0} is not a valid PAN format (e.g. ABCDE1234F)").format(pan))

	result = __current_result(doc, pan) if pan else None
	doc.set(LINK_FIELD, result.name if result else None)
	doc.set(STATUS_FIELD, result.status if result else NOT_VERIFIED)


def enforce_rule(doc, event: str) -> None:
	"""
	Block or warn when the document reaches its rule's threshold without a
	PAN verified as Valid.

	Parameters:
	        doc (Document, required): Document being saved/submitted.
	        event (str, required): "Save" or "Submit".

	Returns:
	        None
	"""
	# While the integration is off nobody can verify, so never block documents.
	if not frappe.db.get_single_value("Verifico Settings", "enabled", cache=True):
		return
	rule = matching_rule(doc)
	if not rule or rule["check_on"] != event or doc.get(STATUS_FIELD) == "Valid":
		return

	amount = fmt_money(rule["threshold_amount"], currency=doc.get("currency"))
	message = _("PAN verification is required for {0} of {1} or more.").format(_(doc.doctype), amount)
	message += " " + __next_step(doc.get(PAN_FIELD), doc.get(STATUS_FIELD))
	if rule["action"] == "Block":
		frappe.throw(message, title=_("PAN Verification Required"))
	frappe.msgprint(message, title=_("PAN Verification Recommended"), indicator="orange")


def __next_step(pan: str | None, status: str | None) -> str:
	"""
	Tell the user what to do: typing a PAN only stores it; the check runs
	from the "Verify PAN" button (each check costs Verifico credits).

	Parameters:
	        pan (str, optional): PAN on the document.
	        status (str, optional): Current PAN status.

	Returns:
	        str: Instruction for the message.
	"""
	if not pan:
		return _(
			"Click Verify PAN at the top of the form and enter the customer's PAN or upload the PAN card."
		)
	if status == "Invalid":
		return _("PAN {0} was checked and is not valid. Correct it and click Verify PAN again.").format(
			pan
		)
	return _(
		"PAN {0} is entered but not verified yet. Click Verify PAN at the top of the form."
	).format(pan)


def __current_result(doc, pan: str):
	"""
	The newest Valid/Invalid result for this PAN within the reuse window (at
	least 1 day); if there is none, the document's own linked result when it is
	for the same PAN (keeps old documents verified after the window passes).

	Parameters:
	        doc (Document, required): Reference document.
	        pan (str, required): Normalized PAN on the document.

	Returns:
	        frappe._dict | None: {"name", "status"}
	"""
	days = max(frappe.db.get_single_value("Verifico Settings", "reuse_valid_days") or 0, 1)
	latest = frappe.db.get_value(
		"PAN Verification",
		{
			"pan_number": pan,
			"status": ["in", ["Valid", "Invalid"]],
			"verified_on": [">=", add_days(now_datetime(), -days)],
		},
		["name", "status"],
		as_dict=True,
		order_by="verified_on desc",
	)
	if latest:
		return latest

	linked = doc.get(LINK_FIELD)
	result = (
		frappe.db.get_value("PAN Verification", linked, ["name", "status", "pan_number"], as_dict=True)
		if linked
		else None
	)
	return result if result and result.pan_number == pan else None
