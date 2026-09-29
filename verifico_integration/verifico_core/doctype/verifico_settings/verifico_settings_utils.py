# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Validation for Verifico Settings."""

from urllib.parse import urlparse

import frappe
from frappe import _


def validate_settings(doc) -> None:
	"""
	Validate the API URL, key and numeric limits.

	Parameters:
	        doc (Document, required): Verifico Settings.

	Returns:
	        None
	"""
	if doc.base_url:
		parsed = urlparse(doc.base_url.strip())
		if parsed.scheme != "https" or not parsed.hostname:
			frappe.throw(_("Base URL must be an https URL, e.g. https://api.theverifico.com"))
		doc.base_url = doc.base_url.strip().rstrip("/")
	if doc.enabled and not (doc.base_url and doc.api_key):
		frappe.throw(_("Base URL and API Key are required to enable Verifico"))

	if not 5 <= (doc.timeout_seconds or 0) <= 60:
		frappe.throw(_("Timeout must be between 5 and 60 seconds"))
	if (doc.reuse_valid_days or 0) < 0:
		frappe.throw(_("Reuse Valid Result For (Days) cannot be negative"))
	if (doc.max_calls_per_user_per_hour or 0) < 0:
		frappe.throw(_("Max Verifico Calls per User per Hour cannot be negative"))
	if not 1 <= (doc.max_file_size_mb or 0) <= 50:
		frappe.throw(_("Max PAN Card File Size must be between 1 and 50 MB"))
