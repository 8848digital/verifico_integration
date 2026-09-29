# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Find the PAN Verification Rule that applies to a document (cached)."""

import frappe
from frappe.utils import flt

DOCTYPES_CACHE_KEY = "verifico_integration:rule_doctypes"
RULES_CACHE_KEY = "verifico_integration:rules:{doctype}"
RULE_FIELDS = [
	"name",
	"condition",
	"amount_field",
	"threshold_amount",
	"action",
	"check_on",
	"party_field",
	"prefill_party_pan",
	"warn_on_pan_change",
]


def get_rule_doctypes() -> set[str]:
	"""
	DocTypes with at least one enabled rule. Cached because the "*" doc_events
	hook calls this on every save of every document.

	Returns:
	        set[str]: Reference DocType names.
	"""
	# During install/migrate DocTypes are synced before this app's tables exist.
	if frappe.flags.in_install or frappe.flags.in_migrate:
		return set()
	return set(frappe.cache.get_value(DOCTYPES_CACHE_KEY, generator=__load_rule_doctypes) or [])


def matching_rule(doc) -> dict | None:
	"""
	The first enabled rule whose condition matches and whose threshold the
	document's amount reaches.

	Parameters:
	        doc (Document, required): The document being saved/submitted.

	Returns:
	        dict | None: Rule row.
	"""
	for rule in __rules_for(doc.doctype):
		if flt(doc.get(rule["amount_field"])) >= flt(rule["threshold_amount"]) and __condition_matches(
			rule, doc
		):
			return rule
	return None


def party_of(doc) -> tuple[str | None, str | None]:
	"""
	(party DocType, party name) of a document, from its rule's Party Field.
	e.g. Sales Order with party field "customer" -> ("Customer", "CUST-0001")

	Parameters:
	        doc (Document, required): Reference document.

	Returns:
	        tuple: (party_doctype, party) or (None, None).
	"""
	_rule, party_doctype, party = party_rule(doc)
	return party_doctype, party


def party_rule(doc) -> tuple[dict | None, str | None, str | None]:
	"""
	The first rule of the document's DocType that has a Party Field, with the
	party it points to on this document.

	Parameters:
	        doc (Document, required): Reference document.

	Returns:
	        tuple: (rule row, party_doctype, party) — (None, None, None) without a party.
	"""
	rule = next((rule for rule in __rules_for(doc.doctype) if rule.get("party_field")), None)
	field = frappe.get_meta(doc.doctype).get_field(rule["party_field"]) if rule else None
	if not (field and doc.get(field.fieldname)):
		return None, None, None
	party_doctype = field.options if field.fieldtype == "Link" else doc.get(field.options)
	return rule, party_doctype, doc.get(field.fieldname)


def clear_rule_cache(doctype: str | None = None) -> None:
	"""
	Drop cached rule lookups after a rule is saved or deleted.

	Parameters:
	        doctype (str, optional): Reference DocType whose rules changed.

	Returns:
	        None
	"""
	frappe.cache.delete_value(DOCTYPES_CACHE_KEY)
	if doctype:
		frappe.cache.delete_value(RULES_CACHE_KEY.format(doctype=doctype))


def __rules_for(doctype: str) -> list[dict]:
	"""
	Cached enabled rules of a DocType, oldest first.

	Parameters:
	        doctype (str, required): Reference DocType.

	Returns:
	        list[dict]: Rule rows.
	"""
	return (
		frappe.cache.get_value(
			RULES_CACHE_KEY.format(doctype=doctype),
			generator=lambda: frappe.get_all(
				"PAN Verification Rule",
				filters={"enabled": 1, "reference_doctype": doctype},
				fields=RULE_FIELDS,
				order_by="creation asc",
			),
		)
		or []
	)


def __load_rule_doctypes() -> list[str]:
	"""
	Query reference DocTypes of enabled rules.

	Returns:
	        list[str]: DocType names.
	"""
	try:
		return frappe.get_all(
			"PAN Verification Rule", filters={"enabled": 1}, pluck="reference_doctype", distinct=True
		)
	except frappe.db.TableMissingError:
		return []


def __condition_matches(rule: dict, doc) -> bool:
	"""
	Evaluate the rule's optional Python condition with `doc` in scope.

	Parameters:
	        rule (dict, required): Rule row.
	        doc (Document, required): Reference document.

	Returns:
	        bool: True if there is no condition or it is truthy.
	"""
	if not (rule["condition"] or "").strip():
		return True
	try:
		return bool(frappe.safe_eval(rule["condition"], None, {"doc": frappe._dict(doc.as_dict())}))
	except Exception:
		frappe.log_error(f"Verifico | Condition error in rule {rule['name']}", frappe.get_traceback())
		return False
