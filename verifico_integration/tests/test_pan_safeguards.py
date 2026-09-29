# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Credit and data safeguards: no double charge, quotas, file checks, draft-only, newest result."""

from unittest.mock import patch

import requests

import frappe
from frappe.tests.utils import FrappeTestCase

from verifico_integration.tests.verifico_fixtures import (
	CLIENT_POST,
	VALID_PAN,
	clear_test_results,
	make_order,
	ocr_reply,
	reply,
	reset_cached_settings,
	setup_verifico,
	verify_reply,
)
from verifico_integration.verifico_core.services.pan_service import PanVerificationService
from verifico_integration.verifico_core.services.pan_status import result_payload


class TestPanSafeguards(FrappeTestCase):
	"""Behaviour added in review to protect credits and keep statuses right."""

	@classmethod
	def setUpClass(cls):
		"""
		Enable Verifico and create the test DocType and rule.

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
		Fresh order, no earlier results, no quota used.

		Returns:
		        None
		"""
		clear_test_results()
		frappe.cache.delete_keys("verifico_integration:calls:")
		self.order = make_order(250000)
		self.service = PanVerificationService(self.order.doctype, self.order.name)

	def test_timeout_is_not_retried(self):
		"""
		A timed-out call may already be charged, so it is not sent again.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, side_effect=requests.Timeout("read timed out")) as post:
			log = self.service.verify_number(VALID_PAN)
		self.assertEqual((post.call_count, log.status), (1, "Failed"))

	def test_submitted_document_is_refused(self):
		"""
		Only drafts can be verified (no credits spent on finished documents).

		Returns:
		        None
		"""
		order = make_order(100)
		order.submit()
		self.assertRaises(frappe.ValidationError, PanVerificationService, order.doctype, order.name)

	def test_renamed_file_is_refused(self):
		"""
		A file named .png whose content is not an image never reaches Verifico.

		Returns:
		        None
		"""
		file_url = self.__upload("pan.png", b"just some text")
		with patch(CLIENT_POST) as post:
			self.assertRaises(frappe.ValidationError, self.service.read_card, file_url)
		post.assert_not_called()

	def test_card_flow_reuses_recent_valid_result(self):
		"""
		After reading a card, a recent valid result for that PAN is reused:
		only the card read (1 credit) is paid.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, return_value=verify_reply()):
			self.service.verify_number(VALID_PAN)
		file_url = self.__upload("pan.png", b"\x89PNG fake image")
		with patch(CLIENT_POST, side_effect=[ocr_reply()]) as post:
			log = PanVerificationService(self.order.doctype, make_order(300000).name).read_card_and_verify(
				file_url
			)
		self.assertEqual(post.call_count, 1)
		self.assertEqual((log.status, log.credits_used, bool(log.reused_from)), ("Valid", 1, True))

	def test_hourly_call_quota(self):
		"""
		Past the per-user hourly limit further paid calls are refused.

		Returns:
		        None
		"""
		frappe.db.set_single_value("Verifico Settings", "max_calls_per_user_per_hour", 1)
		frappe.clear_cache(doctype="Verifico Settings")
		try:
			with patch(CLIENT_POST, return_value=verify_reply(status="invalid")):
				self.service.verify_number(VALID_PAN)
				self.assertRaises(frappe.RateLimitExceededError, self.service.verify_number, "ZZZZZ9999Z")
		finally:
			frappe.db.set_single_value("Verifico Settings", "max_calls_per_user_per_hour", 0)
			frappe.clear_cache(doctype="Verifico Settings")

	def test_newer_valid_result_wins_over_older_invalid(self):
		"""
		A document linked to an old Invalid result shows Valid once the same PAN
		is verified as valid later.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, return_value=verify_reply(status="invalid")):
			self.service.verify_number(VALID_PAN)
		with patch(CLIENT_POST, return_value=verify_reply()):
			PanVerificationService(self.order.doctype, make_order(300000).name).verify_number(VALID_PAN)
		self.order.reload()
		self.order.save()
		self.assertEqual(self.order.verifico_pan_status, "Valid")

	def test_verifico_invalid_pan_answer_is_invalid_not_failed(self):
		"""
		Verifico answers an unknown PAN with success=false "Verification failed:
		Invalid PAN" (seen live); that is an Invalid result and free.

		Returns:
		        None
		"""
		answer = reply(200, {"success": False, "error": "Verification failed: Invalid PAN"})
		with patch(CLIENT_POST, return_value=answer):
			log = self.service.verify_number(VALID_PAN)
		self.assertEqual((log.status, log.credits_used), ("Invalid", 0))
		self.assertIn("Invalid PAN", log.response)

	def test_failure_is_reported_as_424_with_reason(self):
		"""
		A Verifico failure is answered with 424 (not 5xx) and Verifico's reason,
		so the desk shows the reason instead of "Internal Server Error".

		Returns:
		        None
		"""
		with patch(CLIENT_POST, return_value=reply(401, {"message": "API key is missing or too short"})):
			payload = result_payload(self.service.verify_number(VALID_PAN))
		self.assertEqual((payload["status"], payload["code"]), (False, 424))
		self.assertIn("too short", payload["message"])

	def __upload(self, name: str, content: bytes) -> str:
		"""
		Save a private test file.

		Parameters:
		        name (str, required): File name.
		        content (bytes, required): File bytes.

		Returns:
		        str: File URL.
		"""
		return (
			frappe.get_doc({"doctype": "File", "file_name": name, "content": content, "is_private": 1})
			.insert()
			.file_url
		)
