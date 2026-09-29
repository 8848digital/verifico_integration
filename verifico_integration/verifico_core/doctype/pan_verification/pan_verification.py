# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

from frappe.model.document import Document

from verifico_integration.verifico_core.doctype.pan_verification.pan_verification_utils import (
	validate_pan_verification,
)


class PANVerification(Document):
	"""Audit record of one PAN check: result, credits used, and what it was for."""

	def validate(self):
		"""
		Allow only system-created records.

		Returns:
		        None
		"""
		validate_pan_verification(self)
