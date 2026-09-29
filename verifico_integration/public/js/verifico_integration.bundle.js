// Copyright (c) 2026 8848 Digital LLP. All rights reserved.
// Proprietary and confidential. Unauthorized copying, distribution, or use
// of this file, via any medium, is strictly prohibited without prior
// written permission from 8848 Digital LLP.

const PAN_API = "verifico_integration.verifico_core.api.v1.pan";
const STATUS_COLORS = { Valid: "green", Invalid: "red", "Not Verified": "orange" };

/**
 * Add the PAN status indicator and "Verify PAN" button to any form whose
 * DocType has a PAN Verification Rule (detected by the verifico_pan_number field).
 *
 * @param {object} frm - The refreshed form.
 * @returns {void}
 */
function setupPanVerification(frm) {
	if (!frm.fields_dict.verifico_pan_number || frm.doc.docstatus !== 0) return;

	const status = frm.doc.verifico_pan_status || "Not Verified";
	frm.dashboard.add_indicator(__("PAN: {0}", [__(status)]), STATUS_COLORS[status] || "gray");
	frm.add_custom_button(__("Verify PAN"), () => openPanDialog(frm));
}

/**
 * Dialog to verify a PAN by number (3 credits) or from the PAN card (4 credits).
 *
 * @param {object} frm - The form the PAN is for.
 * @returns {void}
 */
function openPanDialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("Verify PAN"),
		fields: [
			{
				fieldname: "pan_number",
				fieldtype: "Data",
				label: __("PAN Number"),
				default: frm.doc.verifico_pan_number,
				description: __("5 letters, 4 digits, 1 letter, e.g. ABCDE1234F"),
			},
			{ fieldtype: "Section Break", label: __("Or use the PAN card") },
			{
				fieldname: "pan_card",
				fieldtype: "Attach",
				label: __("PAN Card (JPG, PNG or PDF)"),
			},
		],
		primary_action_label: __("Verify"),
		primary_action(values) {
			if (values.pan_card) {
				callPanApi(frm, dialog, "read_and_verify_pan_card", { file_url: values.pan_card });
			} else if (values.pan_number) {
				callPanApi(frm, dialog, "verify_pan", { pan_number: values.pan_number });
			} else {
				frappe.msgprint(__("Enter the PAN number or attach the PAN card."));
			}
		},
	});
	dialog.show();
}

/**
 * Call a PAN endpoint for this document and show the result.
 *
 * @param {object} frm - The form the PAN is for.
 * @param {object} dialog - The open dialog.
 * @param {string} method - Endpoint name in api/v1/pan.py.
 * @param {object} args - Endpoint arguments besides the reference.
 * @returns {void}
 */
function callPanApi(frm, dialog, method, args) {
	frappe.call({
		method: `${PAN_API}.${method}`,
		args: {
			...args,
			reference_doctype: frm.doctype,
			reference_name: frm.is_new() ? null : frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Checking PAN with Verifico..."),
		// Verifico failures come back as HTTP 424 with the standard envelope in the body.
		error: (xhr) => showPanFailure(xhr && (xhr.responseJSON || xhr)),
		callback: (r) => {
			const data = r.data || {};
			dialog.hide();
			showPanResult(data);
			if (frm.is_new() || frm.is_dirty()) {
				// Keep unsaved edits; the result is linked to this PAN on save.
				frm.set_value("verifico_pan_number", data.pan_number);
			} else {
				frm.reload_doc();
			}
		},
	});
}

/**
 * Show why a PAN check failed, using Verifico's own message when available.
 *
 * @param {object} body - Response envelope {message, data} or a raw error.
 * @returns {void}
 */
function showPanFailure(body) {
	const message = frappe.utils.escape_html(
		(body && body.message) || __("PAN verification failed. Please try again.")
	);
	const record = body && body.data && body.data.name;
	frappe.msgprint({
		title: __("PAN Verification Failed"),
		indicator: "red",
		message: record ? `${message}<br><br>${__("Record")}: ${record}` : message,
	});
}

/**
 * Show the verification outcome.
 *
 * @param {object} data - Summary returned by the API.
 * @returns {void}
 */
function showPanResult(data) {
	const rows = [
		[__("PAN"), data.pan_number],
		[__("Status"), data.status],
		[__("Name on PAN"), data.full_name || data.ocr_name],
		[__("Category"), data.category],
		[__("Credits Used"), data.reused ? __("0 (recent result reused)") : data.credits_used],
	].filter((row) => row[1] !== undefined && row[1] !== null && row[1] !== "");
	let message = rows
		.map(([label, value]) => `<b>${label}:</b> ${frappe.utils.escape_html(String(value))}`)
		.join("<br>");
	// The party was verified before with a different PAN: surface it, don't block.
	if (data.previous_party_pan) {
		message += `<br><br><span class="text-warning">⚠ ${frappe.utils.escape_html(
			data.previous_party_pan.message
		)}</span>`;
	}
	frappe.msgprint({
		title: __("PAN {0}", [__(data.status)]),
		indicator: STATUS_COLORS[data.status] || "blue",
		message: message,
	});
}

$(document).on("form-refresh", (event, frm) => setupPanVerification(frm));
