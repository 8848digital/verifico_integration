# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Validation for PAN Verification Rule."""

import frappe
from frappe import _

OWN_DOCTYPES = ("PAN Verification", "PAN Verification Rule", "Verifico Settings")
AMOUNT_TYPES = ("Currency", "Float", "Int")
PARTY_TYPES = ("Link", "Dynamic Link")


def validate_rule(doc) -> None:
	"""
	Validate DocType, fields, threshold, trigger and condition of a rule.

	Parameters:
	        doc (Document, required): PAN Verification Rule.

	Returns:
	        None
	"""
	meta = frappe.get_meta(doc.reference_doctype)
	if meta.istable or meta.issingle or meta.is_virtual or doc.reference_doctype in OWN_DOCTYPES:
		frappe.throw(
			_("{0} cannot use PAN verification (child, single, virtual or internal DocType)").format(
				doc.reference_doctype
			)
		)

	__validate_field(meta, doc.amount_field, AMOUNT_TYPES, _("Amount Field"))
	if doc.party_field:
		__validate_field(meta, doc.party_field, PARTY_TYPES, _("Party Field"))
	if (doc.threshold_amount or 0) <= 0:
		frappe.throw(_("Threshold Amount must be greater than zero"))
	if doc.check_on == "Submit" and not meta.is_submittable:
		frappe.throw(_("{0} is not submittable; use Check On = Save").format(doc.reference_doctype))
	__validate_condition(doc.condition)
	__validate_overlap(doc)


def __validate_field(meta, fieldname: str, allowed: tuple, label: str) -> None:
	"""
	The field must exist on the DocType with one of the allowed types.

	Parameters:
	        meta (Meta, required): Reference DocType meta.
	        fieldname (str, required): Field to check.
	        allowed (tuple, required): Allowed field types.
	        label (str, required): Label for the error message.

	Returns:
	        None
	"""
	field = meta.get_field(fieldname)
	if not field or field.fieldtype not in allowed:
		frappe.throw(
			_("{0}: {1} is not a {2} field of {3}").format(label, fieldname, "/".join(allowed), meta.name)
		)


def __validate_condition(condition: str | None) -> None:
	"""
	The condition must be a single valid Python expression.

	Parameters:
	        condition (str, optional): Python expression using doc.

	Returns:
	        None
	"""
	if not (condition or "").strip():
		return
	try:
		compile(condition, "<condition>", "eval")
	except SyntaxError as error:
		frappe.throw(_("Condition is not a valid Python expression: {0}").format(error.msg))


def __validate_overlap(doc) -> None:
	"""
	Two enabled rules for the same DocType with the same condition would make
	the result depend on creation order.

	Parameters:
	        doc (Document, required): PAN Verification Rule.

	Returns:
	        None
	"""
	if not doc.enabled:
		return
	clash = frappe.db.exists(
		"PAN Verification Rule",
		{
			"name": ["!=", doc.name],
			"enabled": 1,
			"reference_doctype": doc.reference_doctype,
			"condition": doc.condition or ["is", "not set"],
		},
	)
	if clash:
		frappe.throw(
			_("Rule {0} already applies to {1} with the same condition").format(
				clash, doc.reference_doctype
			)
		)
