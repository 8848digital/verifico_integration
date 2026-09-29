# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Per-user hourly quota on paid Verifico calls (protects credits)."""

import frappe
from frappe import _

WINDOW_SECONDS = 3600


def consume_call_quota() -> None:
	"""
	Count one paid Verifico call for the current user and refuse it once the
	hourly limit from Verifico Settings is reached. Keyed by user (not IP) so
	several POS counters behind one IP do not share a limit.

	Returns:
	        None
	"""
	limit = (
		frappe.db.get_single_value("Verifico Settings", "max_calls_per_user_per_hour", cache=True) or 0
	)
	if limit <= 0:
		return

	# Site-scoped key (make_key) so sites on one bench never share a counter.
	key = frappe.cache.make_key(f"verifico_integration:calls:{frappe.session.user}")
	count = frappe.cache.incrby(key, 1)
	if count == 1:
		frappe.cache.expire(key, WINDOW_SECONDS)
	if count > limit:
		frappe.throw(
			_(
				"Verifico call limit reached ({0} per hour). Try again later or ask an administrator."
			).format(limit),
			frappe.RateLimitExceededError,
		)
