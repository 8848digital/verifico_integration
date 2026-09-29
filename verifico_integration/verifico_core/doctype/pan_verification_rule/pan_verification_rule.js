// Copyright (c) 2026 8848 Digital LLP. All rights reserved.
// Proprietary and confidential. Unauthorized copying, distribution, or use
// of this file, via any medium, is strictly prohibited without prior
// written permission from 8848 Digital LLP.

frappe.ui.form.on("PAN Verification Rule", {
	/**
	 * Limit Reference DocType to normal, stored DocTypes.
	 *
	 * @param {object} frm - Current form.
	 * @returns {void}
	 */
	setup(frm) {
		frm.set_query("reference_doctype", () => ({
			filters: { istable: 0, issingle: 0, is_virtual: 0 },
		}));
	},
});
