# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Rule enforcement: Block/Warn above the threshold, status follows the PAN field."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from verifico_integration.tests.verifico_fixtures import (
	CLIENT_POST,
	RULE,
	TEST_DOCTYPE,
	VALID_PAN,
	clear_test_results,
	make_order,
	reset_cached_settings,
	setup_verifico,
	verify_reply,
)
from verifico_integration.verifico_core.services.pan_service import PanVerificationService


class TestPanEnforcement(FrappeTestCase):
	"""PAN Verification Rule behaviour on save/submit."""

	@classmethod
	def setUpClass(cls):
		"""
		Enable Verifico and create the test DocType and a Block rule.

		Returns:
		        None
		"""
		super().setUpClass()
		setup_verifico("Block")

	@classmethod
	def tearDownClass(cls):
		"""
		Roll back and drop cached test settings.

		Returns:
		        None
		"""
		super().tearDownClass()
		reset_cached_settings()

	def setUp(self):
		"""
		No earlier results, so every test starts unverified.

		Returns:
		        None
		"""
		clear_test_results()

	def test_submit_blocked_above_threshold_without_pan(self):
		"""
		Above the threshold a submit without a valid PAN is refused.

		Returns:
		        None
		"""
		order = make_order(250000)
		self.assertRaises(frappe.ValidationError, order.submit)

	def test_submit_allowed_after_valid_verification(self):
		"""
		Once the PAN is verified as valid the document can be submitted.

		Returns:
		        None
		"""
		order = make_order(250000)
		self.__verify(order)
		order.reload()
		order.submit()
		self.assertEqual(order.docstatus, 1)

	def test_below_threshold_needs_no_pan(self):
		"""
		Amounts under the threshold are not checked.

		Returns:
		        None
		"""
		order = make_order(150000)
		order.submit()
		self.assertEqual(order.docstatus, 1)

	def test_warn_rule_does_not_block(self):
		"""
		A Warn rule shows a message but lets the submit through.

		Returns:
		        None
		"""
		frappe.db.set_value("PAN Verification Rule", RULE, "action", "Warn")
		frappe.cache.delete_keys("verifico_integration:rules")
		try:
			order = make_order(250000)
			order.submit()
			self.assertEqual(order.docstatus, 1)
		finally:
			frappe.db.set_value("PAN Verification Rule", RULE, "action", "Block")
			frappe.cache.delete_keys("verifico_integration:rules")

	def test_changing_pan_resets_status(self):
		"""
		Editing the PAN after verification makes the document unverified again.

		Returns:
		        None
		"""
		order = make_order(250000)
		self.__verify(order)
		order.reload()
		order.verifico_pan_number = "ZZZZZ9999Z"
		order.save()
		self.assertEqual(
			(order.verifico_pan_status, order.verifico_pan_verification), ("Not Verified", None)
		)

	def test_pan_verified_before_first_save_is_linked(self):
		"""
		Verifying on an unsaved form, then saving with that PAN, links the result.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, return_value=verify_reply()):
			log = PanVerificationService(TEST_DOCTYPE, None).verify_number(VALID_PAN)
		order = make_order(250000, pan=VALID_PAN)
		self.assertEqual(
			(order.verifico_pan_status, order.verifico_pan_verification), ("Valid", log.name)
		)

	def __verify(self, order) -> None:
		"""
		Verify the default PAN for an order with a fake valid reply.

		Parameters:
		        order (Document, required): Test order.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, return_value=verify_reply()):
			PanVerificationService(order.doctype, order.name).verify_number(VALID_PAN)
