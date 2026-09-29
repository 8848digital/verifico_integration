<!--
Copyright (c) 2026 8848 Digital LLP. All rights reserved.
Proprietary and confidential. Unauthorized copying, distribution, or use
of this file, via any medium, is strictly prohibited without prior
written permission from 8848 Digital LLP.
-->

# SETUP.md

## Verifico (PAN verification)

### Overview
Verifies PAN numbers and reads PAN cards (OCR) through the Verifico API
(https://api.theverifico.com). Each call costs Verifico credits: verify = 3,
card read = 1, card read + verify = 4.

### Required Credentials
| Credential | Where it's stored | Required? |
| ---------- | ------------------ | --------- |
| API Key | Verifico Settings → `api_key` (encrypted) | Yes |

### Settings DocType Fields
**Verifico Settings**

| Field | Type | Mandatory | Notes |
| ----- | ---- | --------- | ----- |
| Enabled | Check | — | Master switch. |
| Base URL | Data | Yes (when enabled) | `https://api.theverifico.com` |
| API Key | Password | Yes (when enabled) | Sent as `X-API-Key`. |
| Timeout (Seconds) | Int | — | 5–60, default 30. Only Verifico 5xx answers are retried; timeouts are not (a timed-out call may already be charged). |
| Reuse Valid Result For (Days) | Int | — | Default 365; 0 = always call Verifico. |
| Max PAN Card File Size (MB) | Int | — | 1–50, default 20. |
| Max Verifico Calls per User per Hour | Int | — | Default 60; 0 = no limit. Counts only paid calls (reused results are free). |

**PAN Verification Rule** (one per DocType / condition)

| Field | Type | Mandatory | Notes |
| ----- | ---- | --------- | ----- |
| Rule Name | Data | Yes | |
| Reference DocType | Link | Yes | Any normal DocType (e.g. Sales Order, Sales Invoice, POS Invoice). |
| Amount Field | Data | Yes | Currency/Float/Int field, e.g. `grand_total`. |
| Threshold Amount | Currency | Yes | Default 2,00,000. |
| Action | Select | Yes | Block or Warn. |
| Check On | Select | Yes | Submit (submittable DocTypes) or Save. |
| Condition | Code | — | Optional Python expression, e.g. `doc.customer_group == "Retail"`. |
| Party Field | Data | — | Link field of the PAN holder, e.g. `customer`. |

### Site Config / Environment Variables
None.

### Webhooks (if applicable)
None.

### How to Test
1. Verifico Settings → Enabled, API Key → Save.
2. Create a PAN Verification Rule (e.g. Sales Order, `grand_total`, 200000, Block, Submit).
3. Create a Sales Order above 2,00,000 → Submit is refused.
4. **Verify PAN** → enter a PAN (or attach the card) → status becomes Valid → Submit works.
5. Check the **PAN Verification** list for the record and credits used.
