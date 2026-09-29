# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""HTTP client for the Verifico API (PAN verification and PAN card OCR)."""

import time

import requests

import frappe
from frappe import _

VERIFY_PAN_PATH = "/api/v1/verify/pan"
EXTRACT_PAN_PATH = "/api/v1/documents/extract/pan"
# Only transient server errors are retried: 400/401/402/429 never self-heal
# and every call costs credits.
RETRY_STATUSES = (500, 502, 503, 504)
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2
TOTAL_BUDGET_SECONDS = 90  # stay under the web server timeout, retries included
FRIENDLY_ERRORS = {
	400: "Verifico rejected the request",
	401: "Verifico API key is invalid",
	402: "Verifico account has insufficient credits",
	429: "Too many Verifico requests; try again shortly",
}


class VerificoError(Exception):
	"""Raised when Verifico returns an error or cannot be reached."""

	def __init__(
		self, status_code: int, message: str, payload: dict | None = None, answered: bool = False
	):
		"""
		Build the error with the HTTP status, a readable message and Verifico's reply.

		Parameters:
		        status_code (int, required): HTTP status (0 when Verifico was unreachable).
		        message (str, required): Error message.
		        payload (dict, optional): Verifico's JSON reply, kept for the audit record.
		        answered (bool, optional): True when Verifico answered normally with
		                success=false (e.g. "Verification failed: Invalid PAN").

		Returns:
		        None
		"""
		super().__init__(message)
		self.status_code = status_code
		self.payload = payload or {}
		self.answered = answered


class VerificoClient:
	"""
	Thin Verifico API wrapper. Retries only transient 5xx/network failures;
	`verification_data.status == "invalid"` is a normal answer, not an error.
	"""

	def __init__(self):
		"""
		Load base URL, API key and timeout from Verifico Settings.

		Returns:
		        None
		"""
		settings = frappe.get_cached_doc("Verifico Settings")
		if not settings.enabled:
			frappe.throw(_("Verifico Integration is disabled in Verifico Settings"))

		self.base_url = (settings.base_url or "").rstrip("/")
		self.api_key = settings.get_password("api_key", raise_exception=False)
		self.timeout = settings.timeout_seconds or 30
		if not (self.base_url and self.api_key):
			frappe.throw(_("Set Base URL and API Key in Verifico Settings"))

	def verify_pan(self, pan_number: str) -> dict:
		"""
		Verify a PAN number (Verifico charges 3 credits).

		Parameters:
		        pan_number (str, required): Normalized PAN, e.g. "ABCDE1234F".

		Returns:
		        dict: Verifico JSON (`verification_data`, `credits_used`, ...).
		"""
		return self.__post(VERIFY_PAN_PATH, json={"pan_number": pan_number})

	def extract_pan(self, filename: str, content: bytes, content_type: str) -> dict:
		"""
		Read PAN details from a card image/PDF (Verifico charges 1 credit).

		Parameters:
		        filename (str, required): Original file name.
		        content (bytes, required): File bytes.
		        content_type (str, required): MIME type, e.g. "image/jpeg".

		Returns:
		        dict: Verifico JSON (`data.pan_number`, `data.name`, ...).
		"""
		return self.__post(EXTRACT_PAN_PATH, files={"file": (filename, content, content_type)})

	def __post(self, path: str, json: dict | None = None, files: dict | None = None) -> dict:
		"""
		POST with the API key. Only 5xx answers are retried (within the time
		budget); timeouts/network errors are not, to avoid paying twice.

		Parameters:
		        path (str, required): Endpoint path.
		        json (dict, optional): JSON body.
		        files (dict, optional): Multipart files.

		Returns:
		        dict: Parsed success body.

		Raises:
		        VerificoError: On any failure after retries.
		"""
		deadline = time.monotonic() + TOTAL_BUDGET_SECONDS
		for attempt in range(1, MAX_ATTEMPTS + 1):
			try:
				response = requests.post(
					f"{self.base_url}{path}",
					headers={"X-API-Key": self.api_key, "Accept": "application/json"},
					json=json,
					files=files,
					timeout=self.timeout,
				)
			except requests.RequestException as error:
				# Not retried: a timed-out call may already have been charged.
				raise VerificoError(0, _("Could not reach Verifico: {0}").format(str(error))) from error

			retry_fits = time.monotonic() + RETRY_DELAY_SECONDS + self.timeout < deadline
			if response.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS and retry_fits:
				time.sleep(RETRY_DELAY_SECONDS)
				continue
			return self.__parse(response)

	def __parse(self, response) -> dict:
		"""
		Turn an HTTP response into a success body or a VerificoError.

		Parameters:
		        response (Response, required): Verifico HTTP response.

		Returns:
		        dict: Success body.
		"""
		try:
			body = response.json() or {}
		except ValueError:
			body = {}

		if response.status_code >= 400:
			detail = body.get("message") or body.get("error") or response.text[:300]
			base = FRIENDLY_ERRORS.get(response.status_code, "Verifico request failed")
			raise VerificoError(response.status_code, f"{_(base)} ({response.status_code}): {detail}", body)
		if body.get("success") is False:
			message = body.get("error") or body.get("message") or "Verifico request failed"
			raise VerificoError(body.get("status_code") or 502, message, body, answered=True)
		return body
