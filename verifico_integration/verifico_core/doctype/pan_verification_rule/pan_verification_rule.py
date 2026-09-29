# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

from frappe.model.document import Document

from verifico_integration.verifico_core.doctype.pan_verification_rule.pan_verification_rule_utils import (
	validate_rule,
)
from verifico_integration.verifico_core.services.custom_fields import ensure_pan_fields
from verifico_integration.verifico_core.services.rule_matcher import clear_rule_cache


class PANVerificationRule(Document):
	"""When a DocType needs a verified PAN (amount threshold, Block/Warn, Save/Submit)."""

	def validate(self):
		"""
		Validate DocType, fields, threshold, trigger and condition.

		Returns:
		        None
		"""
		validate_rule(self)

	def on_update(self):
		"""
		Add PAN fields to the reference DocType and refresh the rule cache.

		Returns:
		        None
		"""
		ensure_pan_fields(self.reference_doctype)
		clear_rule_cache(self.reference_doctype)
		before = self.get_doc_before_save()
		if before and before.reference_doctype != self.reference_doctype:
			clear_rule_cache(before.reference_doctype)

	def on_trash(self):
		"""
		Refresh the rule cache after deletion.

		Returns:
		        None
		"""
		clear_rule_cache(self.reference_doctype)
