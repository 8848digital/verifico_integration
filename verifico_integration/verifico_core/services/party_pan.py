# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Party (e.g. customer) PAN history: pre-fill the last verified PAN, warn when it changes."""

import frappe
from frappe import _

from verifico_integration.verifico_core.services.rule_matcher import party_rule
from verifico_integration.verifico_core.services.verification_log import PAN_FIELD


def prefill_party_pan(doc) -> None:
	"""
	On a new document with no PAN, fill in the party's most recent valid PAN
	(when the rule allows) so the cashier doesn't retype it. The status is then
	derived as usual, so an old result still needs a fresh Verify PAN.

	Parameters:
	        doc (Document, required): Document being saved.

	Returns:
	        None
	"""
	if not doc.is_new() or doc.get(PAN_FIELD):
		return
	rule, party_doctype, party = party_rule(doc)
	if not (rule and rule.get("prefill_party_pan")):
		return

	last = last_verified_pan(party_doctype, party)
	if last:
		doc.set(PAN_FIELD, last.pan_number)
		frappe.msgprint(
			_("PAN {0} pre-filled from {1}'s last verified PAN.").format(last.pan_number, party),
			alert=True,
			indicator="blue",
		)


def warn_on_party_pan_change(doc, pan: str) -> None:
	"""
	Warn (never block) when a newly entered or changed PAN differs from the
	party's last verified PAN — a hint the wrong PAN may have been given.

	Parameters:
	        doc (Document, required): Document being saved.
	        pan (str, required): Normalized PAN on the document.

	Returns:
	        None
	"""
	if not pan or not (doc.is_new() or doc.has_value_changed(PAN_FIELD)):
		return
	rule, party_doctype, party = party_rule(doc)
	if not (rule and rule.get("warn_on_pan_change")):
		return

	last = last_verified_pan(party_doctype, party)
	if last and last.pan_number != pan:
		frappe.msgprint(
			different_pan_message(party, pan, last), title=_("Different PAN"), indicator="orange"
		)


def previous_party_pan(log) -> dict | None:
	"""
	For a verification result: the party's last verified PAN when it differs
	from the PAN just checked (shown as a warning in the Verify PAN dialog).

	Parameters:
	        log (Document, required): PAN Verification just created.

	Returns:
	        dict | None: {"pan_number", "name", "message"} or None.
	"""
	if not (log.party and log.pan_number):
		return None
	last = last_verified_pan(log.party_doctype, log.party, exclude=log.name)
	if not last or last.pan_number == log.pan_number:
		return None
	return {
		"pan_number": last.pan_number,
		"name": last.name,
		"message": different_pan_message(log.party, log.pan_number, last),
	}


def last_verified_pan(party_doctype: str | None, party: str | None, exclude: str | None = None):
	"""
	The party's most recent Valid PAN Verification (reused results included).

	Parameters:
	        party_doctype (str, optional): Party DocType, e.g. "Customer".
	        party (str, optional): Party name.
	        exclude (str, optional): PAN Verification to ignore (the one just made).

	Returns:
	        frappe._dict | None: {"name", "pan_number"}
	"""
	if not (party_doctype and party):
		return None
	filters = {"party_doctype": party_doctype, "party": party, "status": "Valid"}
	if exclude:
		filters["name"] = ["!=", exclude]
	return frappe.db.get_value(
		"PAN Verification", filters, ["name", "pan_number"], as_dict=True, order_by="verified_on desc"
	)


def different_pan_message(party: str, pan: str, last) -> str:
	"""
	Warning text for a PAN that differs from the party's last verified one.

	Parameters:
	        party (str, required): Party name.
	        pan (str, required): PAN entered now.
	        last (frappe._dict, required): {"name", "pan_number"} of the earlier result.

	Returns:
	        str: Message.
	"""
	return _(
		"{0} was previously verified with PAN {1} ({2}), but PAN {3} is entered now. Please confirm with the customer."
	).format(party, last.pan_number, last.name, pan)
