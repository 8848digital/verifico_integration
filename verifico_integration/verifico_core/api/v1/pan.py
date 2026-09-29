# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

import frappe

from verifico_integration.utils.api_handlers.response_formatter import api_response
from verifico_integration.verifico_core.services.pan_service import PanVerificationService
from verifico_integration.verifico_core.services.pan_status import (
	document_pan_status,
	result_payload,
)


@frappe.whitelist(methods=["POST"])
def verify_pan(
	pan_number: str, reference_doctype: str | None = None, reference_name: str | None = None
):
	"""
	        Verify a PAN number with Verifico (3 credits; a recent valid result for the
	        same PAN is reused for free). The result is stored as a PAN Verification and
	        linked to the document when one is given.

	        **Endpoint:** `/api/method/verifico_integration.verifico_core.api.v1.pan.verify_pan`
	        **HTTP Method:** POST
	        **Parameters:**
	                - pan_number (str, required): PAN, e.g. ABCDE1234F
	                - reference_doctype (str, optional): Document type the PAN is for (e.g. Sales Order)
	                - reference_name (str, optional): Document name; omit for an unsaved document
	        **Response:**
	```json
	                {
	                        "status": true,
	                        "status_code": 200,
	                        "message": "PAN verified as valid",
	                        "data": {"name": "PANV-00001", "pan_number": "ABCDE1234F", "status": "Valid", "full_name": "JOHN DOE",
	                                 "date_of_birth": "01-01-1990", "category": "Individual", "aadhaar_seeding_status": "Y",
	                                 "credits_used": 3, "reused": false, "ocr_name": null, "error": null},
	                        "errors": null
	                }
	```
	"""
	log = PanVerificationService(reference_doctype, reference_name).verify_number(pan_number)
	return api_response(**result_payload(log))


@frappe.whitelist(methods=["POST"])
def read_pan_card(
	file_url: str, reference_doctype: str | None = None, reference_name: str | None = None
):
	"""
	        Read PAN details from an uploaded PAN card image/PDF without verifying them
	        (1 credit). Use to pre-fill the PAN before calling verify_pan.

	        **Endpoint:** `/api/method/verifico_integration.verifico_core.api.v1.pan.read_pan_card`
	        **HTTP Method:** POST
	        **Parameters:**
	                - file_url (str, required): URL of the uploaded File (JPG, PNG or PDF)
	                - reference_doctype (str, optional): Document type the PAN is for
	                - reference_name (str, optional): Document name
	        **Response:**
	```json
	                {
	                        "status": true,
	                        "status_code": 200,
	                        "message": "PAN details read from the card",
	                        "data": {"name": "PANV-00002", "pan_number": "ABCDE1234F", "status": "Extracted", "ocr_name": "JOHN DOE",
	                                 "credits_used": 1, "error": null},
	                        "errors": null
	                }
	```
	"""
	log = PanVerificationService(reference_doctype, reference_name).read_card(file_url)
	return api_response(**result_payload(log))


@frappe.whitelist(methods=["POST"])
def read_and_verify_pan_card(
	file_url: str, reference_doctype: str | None = None, reference_name: str | None = None
):
	"""
	        Read the PAN card, then verify the PAN found on it (4 credits). If no valid
	        PAN can be read, verification is skipped and no further credits are spent.

	        **Endpoint:** `/api/method/verifico_integration.verifico_core.api.v1.pan.read_and_verify_pan_card`
	        **HTTP Method:** POST
	        **Parameters:**
	                - file_url (str, required): URL of the uploaded File (JPG, PNG or PDF)
	                - reference_doctype (str, optional): Document type the PAN is for
	                - reference_name (str, optional): Document name
	        **Response:**
	```json
	                {
	                        "status": true,
	                        "status_code": 200,
	                        "message": "PAN verified as valid",
	                        "data": {"name": "PANV-00003", "pan_number": "ABCDE1234F", "status": "Valid", "ocr_name": "JOHN DOE",
	                                 "credits_used": 4, "error": null},
	                        "errors": null
	                }
	```
	"""
	log = PanVerificationService(reference_doctype, reference_name).read_card_and_verify(file_url)
	return api_response(**result_payload(log))


@frappe.whitelist(methods=["GET"])
def get_pan_status(reference_doctype: str, reference_name: str):
	"""
	        Whether a document needs PAN verification (its rule and threshold) and its
	        current PAN status. Useful for custom front ends such as a POS.

	        **Endpoint:** `/api/method/verifico_integration.verifico_core.api.v1.pan.get_pan_status`
	        **HTTP Method:** GET
	        **Parameters:**
	                - reference_doctype (str, required): Document type
	                - reference_name (str, required): Document name
	        **Response:**
	```json
	                {
	                        "status": true,
	                        "status_code": 200,
	                        "message": "",
	                        "data": {"required": true, "action": "Block", "threshold_amount": 200000.0, "pan_number": "ABCDE1234F",
	                                 "status": "Valid", "verification": "PANV-00001"},
	                        "errors": null
	                }
	```
	"""
	return api_response(data=document_pan_status(reference_doctype, reference_name))
