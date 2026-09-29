# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Validation for PAN Verification (system-created audit records)."""

import frappe
from frappe import _


def validate_pan_verification(doc) -> None:
	"""
	Records are written only by the integration, never typed in by users.

	Parameters:
	        doc (Document, required): PAN Verification.

	Returns:
	        None
	"""
	if not doc.flags.ignore_permissions:
		frappe.throw(_("PAN Verifications are created by the Verify PAN action, not manually"))
