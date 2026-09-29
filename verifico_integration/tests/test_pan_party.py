# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Party PAN history: pre-fill the last verified PAN and warn when a different PAN is given."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from verifico_integration.tests.verifico_fixtures import (
	CLIENT_POST,
	RULE,
	VALID_PAN,
	clear_test_results,
	make_order,
	reset_cached_settings,
	setup_verifico,
	verify_reply,
)
from verifico_integration.verifico_core.services.pan_service import PanVerificationService
from verifico_integration.verifico_core.services.pan_status import result_payload

OTHER_PAN = "ZZZZZ9999Z"


class TestPartyPan(FrappeTestCase):
	"""Pre-fill and different-PAN warning, driven by the rule's Party Field."""

	@classmethod
	def setUpClass(cls):
		"""
		Enable Verifico and create the test DocType and rule (party = party_user).

		Returns:
		        None
		"""
		super().setUpClass()
		setup_verifico()

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
		No earlier results; the party (Administrator) is verified once with VALID_PAN.

		Returns:
		        None
		"""
		clear_test_results()
		frappe.clear_messages()
		order = make_order(250000)
		with patch(CLIENT_POST, return_value=verify_reply()):
			self.first = PanVerificationService(order.doctype, order.name).verify_number(VALID_PAN)

	def test_new_order_is_prefilled_with_last_verified_pan(self):
		"""
		A new order for the same party gets the last valid PAN, and (being recent)
		is Valid straight away — no Verifico call.

		Returns:
		        None
		"""
		with patch(CLIENT_POST) as post:
			order = make_order(260000)
		post.assert_not_called()
		self.assertEqual((order.verifico_pan_number, order.verifico_pan_status), (VALID_PAN, "Valid"))

	def test_prefill_can_be_switched_off(self):
		"""
		With "Pre-fill Last Verified PAN" off, new orders start empty.

		Returns:
		        None
		"""
		self.__set_rule("prefill_party_pan", 0)
		try:
			self.assertIsNone(make_order(260000).verifico_pan_number)
		finally:
			self.__set_rule("prefill_party_pan", 1)

	def test_different_pan_warns_without_blocking(self):
		"""
		Entering another PAN for the same party saves, with a warning.

		Returns:
		        None
		"""
		order = make_order(260000, pan=OTHER_PAN)
		self.assertEqual(order.verifico_pan_number, OTHER_PAN)
		self.assertTrue(self.__warned())

	def test_same_pan_does_not_warn(self):
		"""
		The party's own PAN raises no warning.

		Returns:
		        None
		"""
		make_order(260000, pan=VALID_PAN)
		self.assertFalse(self.__warned())

	def test_verify_result_reports_previous_pan(self):
		"""
		Verifying a different PAN for the party returns the earlier PAN for the dialog.

		Returns:
		        None
		"""
		order = make_order(270000, pan=OTHER_PAN)
		with patch(CLIENT_POST, return_value=verify_reply(pan=OTHER_PAN)):
			log = PanVerificationService(order.doctype, order.name).verify_number(OTHER_PAN)
		previous = result_payload(log)["data"]["previous_party_pan"]
		self.assertEqual((previous["pan_number"], previous["name"]), (VALID_PAN, self.first.name))

	def __warned(self) -> bool:
		"""
		Whether a "previously verified with PAN" warning was shown.

		Returns:
		        bool: True if the warning is in the message log.
		"""
		return any(
			"previously verified with PAN" in str(message) for message in frappe.get_message_log()
		)

	def __set_rule(self, field: str, value: int) -> None:
		"""
		Change a field on the test rule and refresh the rule cache.

		Parameters:
		        field (str, required): Rule field.
		        value (int, required): New value.

		Returns:
		        None
		"""
		frappe.db.set_value("PAN Verification Rule", RULE, field, value)
		frappe.cache.delete_keys("verifico_integration:rules")
