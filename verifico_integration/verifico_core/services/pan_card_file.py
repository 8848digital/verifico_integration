# Copyright (c) 2026 8848 Digital LLP. All rights reserved.
# Proprietary and confidential. Unauthorized copying, distribution, or use
# of this file, via any medium, is strictly prohibited without prior
# written permission from 8848 Digital LLP.

"""Load and check an uploaded PAN card file before sending it to Verifico OCR."""

import mimetypes

import frappe
from frappe import _

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "application/pdf"}
# Leading bytes of real JPG / PNG / PDF files; a renamed file is refused before any credit is spent.
FILE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG", b"%PDF")


def load_pan_card(file_url: str) -> tuple[str, bytes, str]:
	"""
	Read an uploaded File the user may access, and check type and size so no
	credit is spent on files Verifico cannot read.

	Parameters:
	        file_url (str, required): URL of a Frappe File, e.g. "/private/files/pan.jpg".

	Returns:
	        tuple[str, bytes, str]: (file name, content, MIME type)
	"""
	if not file_url:
		frappe.throw(_("Attach the PAN card (JPG, PNG or PDF)"))

	name = frappe.db.get_value("File", {"file_url": file_url})
	if not name:
		frappe.throw(_("File {0} not found").format(file_url))
	file_doc = frappe.get_doc("File", name)
	file_doc.check_permission("read")

	content_type = mimetypes.guess_type(file_doc.file_name or file_url)[0] or ""
	if content_type not in ALLOWED_TYPES:
		frappe.throw(
			_("Unsupported file type {0}. Allowed: JPG, PNG, PDF").format(content_type or "unknown")
		)

	# Read the raw bytes: File.get_content() may decode binary files as text
	# (Frappe v16 tries windows-125x encodings), which corrupts images and PDFs.
	with open(file_doc.get_full_path(), "rb") as file:
		content = file.read()
	if not content.startswith(FILE_SIGNATURES):
		frappe.throw(
			_("The file is not a real JPG, PNG or PDF (its content does not match the extension)")
		)
	max_mb = frappe.db.get_single_value("Verifico Settings", "max_file_size_mb") or 20
	if len(content) > max_mb * 1024 * 1024:
		frappe.throw(_("PAN card file is larger than {0} MB").format(max_mb))
	return file_doc.file_name, content, content_type
