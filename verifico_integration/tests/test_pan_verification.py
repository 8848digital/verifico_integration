# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""PAN verification flows against fake Verifico replies (no credits spent)."""

from unittest.mock import patch

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


class TestPanVerification(FrappeTestCase):
	"""Verify by number, by card, reuse, and Verifico error handling."""

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
		Fresh order and no earlier results, so reuse never leaks between tests.

		Returns:
		        None
		"""
		clear_test_results()
		self.order = make_order(250000)
		self.service = PanVerificationService(self.order.doctype, self.order.name)

	def test_bad_format_rejected_before_any_call(self):
		"""
		A malformed PAN never reaches Verifico (no credits spent).

		Returns:
		        None
		"""
		with patch(CLIENT_POST) as post:
			self.assertRaises(frappe.ValidationError, self.service.verify_number, "ABC123")
		post.assert_not_called()

	def test_valid_pan_is_logged_and_linked(self):
		"""
		A valid answer is recorded with its credits and linked to the document.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, return_value=verify_reply()):
			log = self.service.verify_number(" abcde1234f ")

		self.assertEqual(
			(log.status, log.pan_number, log.credits_used, log.party),
			("Valid", VALID_PAN, 3, "Administrator"),
		)
		self.order.reload()
		self.assertEqual(
			(self.order.verifico_pan_status, self.order.verifico_pan_verification), ("Valid", log.name)
		)

	def test_invalid_answer_is_a_result_not_an_error(self):
		"""
		status "invalid" from Verifico is stored as Invalid, not Failed.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, return_value=verify_reply(status="invalid")):
			log = self.service.verify_number(VALID_PAN)
		self.assertEqual(log.status, "Invalid")

	def test_recent_valid_result_is_reused_for_free(self):
		"""
		A second check of the same PAN reuses the result without calling Verifico.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, return_value=verify_reply()):
			first = self.service.verify_number(VALID_PAN)
		with patch(CLIENT_POST) as post:
			second = PanVerificationService(self.order.doctype, make_order(300000).name).verify_number(
				VALID_PAN
			)
		post.assert_not_called()
		self.assertEqual(
			(second.status, second.reused_from, second.credits_used), ("Valid", first.name, 0)
		)

	def test_insufficient_credits_is_not_retried(self):
		"""
		402 fails at once (retrying cannot help) and is kept as a Failed record.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, return_value=reply(402, {"message": "Insufficient credits"})) as post:
			log = self.service.verify_number(VALID_PAN)
		self.assertEqual(post.call_count, 1)
		self.assertEqual(log.status, "Failed")
		self.assertIn("insufficient credits", log.error.lower())

	def test_server_error_is_retried(self):
		"""
		A transient 503 is retried and the next success is used.

		Returns:
		        None
		"""
		with patch(CLIENT_POST, side_effect=[reply(503), verify_reply()]) as post, patch("time.sleep"):
			log = self.service.verify_number(VALID_PAN)
		self.assertEqual((post.call_count, log.status), (2, "Valid"))

	def test_card_is_read_then_verified(self):
		"""
		Card upload: OCR then verify; credits of both calls are recorded.

		Returns:
		        None
		"""
		file_url = self.__upload("pan.png", b"\x89PNG fake image")
		with patch(CLIENT_POST, side_effect=[ocr_reply(), verify_reply()]) as post:
			log = self.service.read_card_and_verify(file_url)
		self.assertEqual(post.call_count, 2)
		self.assertEqual(
			(log.status, log.source, log.ocr_name, log.credits_used), ("Valid", "PAN Card", "JOHN DOE", 4)
		)

	def test_unsupported_file_type_is_rejected_before_any_call(self):
		"""
		Only JPG/PNG/PDF are sent to Verifico.

		Returns:
		        None
		"""
		file_url = self.__upload("pan.txt", b"not an image")
		with patch(CLIENT_POST) as post:
			self.assertRaises(frappe.ValidationError, self.service.read_card, file_url)
		post.assert_not_called()

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
