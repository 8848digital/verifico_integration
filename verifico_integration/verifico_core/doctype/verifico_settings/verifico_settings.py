# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

from frappe.model.document import Document

from verifico_integration.verifico_core.doctype.verifico_settings.verifico_settings_utils import (
	validate_settings,
)


class VerificoSettings(Document):
	"""Verifico API connection settings and PAN verification defaults."""

	def validate(self):
		"""
		Validate URL, key and limits.

		Returns:
		        None
		"""
		validate_settings(self)
