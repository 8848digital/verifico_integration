# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""PAN verification flows: verify a number, read a card, or read then verify."""

import json

import frappe
from frappe import _

from verifico_integration.verifico_core.services.call_quota import consume_call_quota
from verifico_integration.verifico_core.services.client import VerificoClient, VerificoError
from verifico_integration.verifico_core.services.pan_card_file import load_pan_card
from verifico_integration.verifico_core.services.rule_matcher import party_of
from verifico_integration.verifico_core.services.verification_log import (
	PAN_PATTERN,
	create_log,
	failure_values,
	find_reusable,
	link_to_reference,
	normalize_pan,
)


class PanVerificationService:
	"""
	Runs one PAN request for a document (or standalone, e.g. a POS front end)
	and always leaves a PAN Verification record, success or failure.
	"""

	def __init__(self, reference_doctype: str | None = None, reference_name: str | None = None):
		"""
		Check permission and resolve the document and party the PAN is for.

		Parameters:
		        reference_doctype (str, optional): Document type the PAN is required for.
		        reference_name (str, optional): Document name.

		Returns:
		        None
		"""
		self._client = None
		self.context = {
			"reference_doctype": None,
			"reference_name": None,
			"party_doctype": None,
			"party": None,
		}
		if reference_doctype and not reference_name:
			# Unsaved document: the PAN is copied to its field and linked on save.
			frappe.has_permission(reference_doctype, "create", throw=True)
			self.context["reference_doctype"] = reference_doctype
			return
		if not reference_doctype:
			frappe.has_permission("PAN Verification", "create", throw=True)
			return

		doc = frappe.get_doc(reference_doctype, reference_name)
		doc.check_permission("write")
		if doc.docstatus != 0:
			frappe.throw(_("PAN can only be verified on a draft {0}").format(_(reference_doctype)))
		party_doctype, party = party_of(doc)
		self.context.update(
			{
				"reference_doctype": reference_doctype,
				"reference_name": reference_name,
				"party_doctype": party_doctype,
				"party": party,
			}
		)

	def verify_number(self, pan_number: str):
		"""
		Verify a PAN number, reusing a recent valid result when allowed.

		Parameters:
		        pan_number (str, required): PAN as typed.

		Returns:
		        Document: PAN Verification record (status Valid / Invalid / Failed).
		"""
		pan = normalize_pan(pan_number)
		reusable = find_reusable(pan)
		if reusable:
			return self.__save(self.__reuse(reusable))
		return self.__save(self.__call_verify(pan, {"source": "PAN Number"}))

	def read_card(self, file_url: str):
		"""
		Read PAN details from a card image/PDF without verifying them (1 credit).

		Parameters:
		        file_url (str, required): Uploaded File URL.

		Returns:
		        Document: PAN Verification record (status Extracted / Failed).
		"""
		return self.__save(self.__call_ocr(file_url))

	def read_card_and_verify(self, file_url: str):
		"""
		Read the card, then verify the PAN found on it. Verification is skipped
		(no extra credits) when no PAN could be read.

		Parameters:
		        file_url (str, required): Uploaded File URL.

		Returns:
		        Document: The verification record, or the OCR record if reading failed.
		"""
		ocr = self.__call_ocr(file_url)
		if ocr["status"] == "Failed" or not PAN_PATTERN.match(ocr.get("pan_number") or ""):
			# Keep the OCR record (its credit is already spent) instead of raising.
			reason = _("No valid PAN could be read from the card (read: {0})").format(
				ocr.get("pan_number") or "-"
			)
			ocr.update({"status": "Failed", "error": ocr.get("error") or reason})
			return self.__save(ocr)

		card_fields = {key: ocr[key] for key in ocr if key.startswith("ocr_") or key == "pan_card"}
		reusable = find_reusable(ocr["pan_number"])
		if reusable:
			verify = {**self.__reuse(reusable), "source": "PAN Card", **card_fields}
		else:
			verify = self.__call_verify(ocr["pan_number"], {"source": "PAN Card", **card_fields})
		verify["credits_used"] = (verify.get("credits_used") or 0) + (ocr.get("credits_used") or 0)
		return self.__save(verify)

	def __call_verify(self, pan: str, extra: dict) -> dict:
		"""
		Call Verifico verify and map the answer to PAN Verification fields.

		Parameters:
		        pan (str, required): Normalized PAN.
		        extra (dict, required): Fields to keep (source, card details).

		Returns:
		        dict: PAN Verification values.
		"""
		values = {"pan_number": pan, **extra}
		try:
			body = self.__client().verify_pan(pan)
		except VerificoError as error:
			return {**values, **failure_values(error)}

		data = body.get("verification_data") or {}
		return {
			**values,
			"status": "Valid" if str(data.get("status", "")).lower() == "valid" else "Invalid",
			"full_name": data.get("full_name"),
			"date_of_birth": data.get("dob"),
			"category": data.get("category"),
			"aadhaar_seeding_status": data.get("aadhaar_seeding_status"),
			"credits_used": body.get("credits_used"),
			"response": json.dumps(body, indent=1),
		}

	def __call_ocr(self, file_url: str) -> dict:
		"""
		Call Verifico OCR and map the answer to PAN Verification fields.

		Parameters:
		        file_url (str, required): Uploaded File URL.

		Returns:
		        dict: PAN Verification values (status Extracted / Failed).
		"""
		filename, content, content_type = load_pan_card(file_url)
		values = {"source": "PAN Card", "pan_card": file_url}
		try:
			body = self.__client().extract_pan(filename, content, content_type)
		except VerificoError as error:
			return {**values, **failure_values(error), "status": "Failed"}

		data = body.get("data") or {}
		return {
			**values,
			"status": "Extracted",
			"pan_number": (data.get("pan_number") or "").strip().upper() or None,
			"ocr_name": data.get("name"),
			"ocr_father_name": data.get("father_name"),
			"ocr_date_of_birth": data.get("dob"),
			"ocr_document_id": body.get("document_id"),
			"credits_used": body.get("credits_used"),
			"response": json.dumps(body, indent=1),
		}

	def __client(self) -> VerificoClient:
		"""
		Verifico client for one paid call: created once per request, and each
		use counts against the user's hourly quota.

		Returns:
		        VerificoClient: The client.
		"""
		if not self._client:
			self._client = VerificoClient()
		consume_call_quota()  # every use of the client is one paid call
		return self._client

	def __reuse(self, source: str) -> dict:
		"""
		Copy a recent valid result (no Verifico call, no credits).

		Parameters:
		        source (str, required): PAN Verification to reuse.

		Returns:
		        dict: PAN Verification values.
		"""
		fields = (
			"pan_number",
			"status",
			"full_name",
			"date_of_birth",
			"category",
			"aadhaar_seeding_status",
		)
		values = frappe.db.get_value("PAN Verification", source, fields, as_dict=True)
		return {**values, "source": "PAN Number", "reused_from": source, "credits_used": 0}

	def __save(self, values: dict):
		"""
		Store the record and link a verified result to the document.

		Parameters:
		        values (dict, required): PAN Verification values.

		Returns:
		        Document: Saved PAN Verification.
		"""
		log = create_log(self.context, values)
		link_to_reference(self.context, log)
		return log
