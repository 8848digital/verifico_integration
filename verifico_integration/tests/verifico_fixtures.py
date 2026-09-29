# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Shared test setup: settings, a throwaway custom DocType + rule, and fake Verifico replies."""

from unittest.mock import MagicMock

import frappe

TEST_DOCTYPE = "Verifico Test Order"
RULE = "Test PAN Rule"
CLIENT_POST = "verifico_integration.verifico_core.services.client.requests.post"
VALID_PAN = "ABCDE1234F"
TEST_PANS = (VALID_PAN, "ZZZZZ9999Z")


def setup_verifico(action: str = "Block") -> None:
	"""
	Enable Verifico with a dummy key and create a submittable custom DocType
	(no ERPNext needed) guarded by a rule with a 200000 threshold.

	Parameters:
	        action (str, optional): Rule action, "Block" or "Warn".

	Returns:
	        None
	"""
	settings = frappe.get_single("Verifico Settings")
	settings.update(
		{
			"enabled": 1,
			"base_url": "https://api.theverifico.com",
			"api_key": "test-key",
			"reuse_valid_days": 365,
			"max_calls_per_user_per_hour": 0,
		}
	)
	settings.save()

	if not frappe.db.exists("DocType", TEST_DOCTYPE):
		frappe.get_doc(
			{
				"doctype": "DocType",
				"name": TEST_DOCTYPE,
				"module": "Verifico Core",
				"custom": 1,
				"is_submittable": 1,
				"autoname": "hash",
				"fields": [
					{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount"},
					{"fieldname": "party_user", "fieldtype": "Link", "options": "User", "label": "Party"},
				],
				"permissions": [
					{"role": "System Manager", "read": 1, "write": 1, "create": 1, "submit": 1, "delete": 1}
				],
			}
		).insert()

	if frappe.db.exists("PAN Verification Rule", RULE):
		frappe.delete_doc("PAN Verification Rule", RULE, force=1)
	frappe.get_doc(
		{
			"doctype": "PAN Verification Rule",
			"rule_name": RULE,
			"reference_doctype": TEST_DOCTYPE,
			"amount_field": "amount",
			"threshold_amount": 200000,
			"action": action,
			"check_on": "Submit",
			"party_field": "party_user",
		}
	).insert()


def make_order(amount: float, pan: str | None = None):
	"""
	Insert a draft test order.

	Parameters:
	        amount (float, required): Order amount.
	        pan (str, optional): PAN typed on the order.

	Returns:
	        Document: The order.
	"""
	return frappe.get_doc(
		{
			"doctype": TEST_DOCTYPE,
			"amount": amount,
			"party_user": "Administrator",
			"verifico_pan_number": pan,
		}
	).insert()


def reply(status_code: int = 200, body: dict | None = None) -> MagicMock:
	"""
	A fake requests.Response.

	Parameters:
	        status_code (int, optional): HTTP status.
	        body (dict, optional): JSON body.

	Returns:
	        MagicMock: Response-like object.
	"""
	return MagicMock(status_code=status_code, json=MagicMock(return_value=body or {}), text=str(body))


def verify_reply(pan: str = VALID_PAN, status: str = "valid") -> MagicMock:
	"""
	Verifico verify response in its documented shape.

	Parameters:
	        pan (str, optional): PAN echoed back.
	        status (str, optional): "valid" or "invalid".

	Returns:
	        MagicMock: Response-like object.
	"""
	return reply(
		200,
		{
			"success": True,
			"verification_type": "pan",
			"verification_data": {
				"pan_number": pan,
				"full_name": "JOHN DOE",
				"dob": "01-01-1990",
				"category": "Individual",
				"aadhaar_seeding_status": "Y",
				"status": status,
			},
			"credits_used": 3,
		},
	)


def ocr_reply(pan: str = VALID_PAN) -> MagicMock:
	"""
	Verifico PAN OCR response in its documented shape.

	Parameters:
	        pan (str, optional): PAN read from the card.

	Returns:
	        MagicMock: Response-like object.
	"""
	return reply(
		200,
		{
			"success": True,
			"document_id": "doc-1",
			"document_type": "pan",
			"status": "completed",
			"data": {
				"pan_number": pan,
				"name": "JOHN DOE",
				"father_name": "RICHARD DOE",
				"dob": "01/01/1990",
			},
			"credits_used": 1,
		},
	)


def clear_test_results() -> None:
	"""
	Delete only PAN Verifications created by these tests (test PANs / test
	DocType), never real or demo records on the site.

	Returns:
	        None
	"""
	frappe.db.delete("PAN Verification", {"pan_number": ["in", TEST_PANS]})
	frappe.db.delete("PAN Verification", {"reference_doctype": TEST_DOCTYPE})


def reset_cached_settings() -> None:
	"""
	Drop cached Verifico Settings and rules after a test class, so the dummy
	test key never lingers in the site cache after the database rolls back.

	Returns:
	        None
	"""
	frappe.clear_document_cache("Verifico Settings", "Verifico Settings")
	frappe.clear_cache(doctype="Verifico Settings")
	frappe.cache.delete_keys("verifico_integration:")
