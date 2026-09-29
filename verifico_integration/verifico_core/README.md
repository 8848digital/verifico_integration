<!--
Copyright (c) 2026 8848 Digital LLP. All rights reserved.
Proprietary and confidential. Unauthorized copying, distribution, or use
of this file, via any medium, is strictly prohibited without prior
written permission from 8848 Digital LLP.
-->

# Verifico Core

## Purpose
PAN verification through the Verifico API: settings, per-DocType rules,
verification records, enforcement on save/submit, and the PAN APIs.

## DocTypes

| DocType | Purpose |
| ------- | ------- |
| Verifico Settings | Single: API URL/key, timeout, reuse window, max card file size. |
| PAN Verification Rule | DocType, amount field, threshold, condition, Block/Warn, Save/Submit, party field. |
| PAN Verification | One record per check (Valid / Invalid / Extracted / Failed). |

## Customizations

| DocType | Owned by | What's customized |
| ------- | -------- | ------------------ |
| Every rule's Reference DocType | Any app | Custom fields `verifico_section`, `verifico_pan_number`, `verifico_pan_status`, `verifico_pan_verification` (added when a rule is saved). |

## Code layout
- `services/` — Verifico client, PAN flows, verification records, rule matching, enforcement, card file checks.
- `document_events.py` — `doc_events["*"]` validate / before_submit (cached early exit).
- `api/v1/pan.py` — verify_pan, read_pan_card, read_and_verify_pan_card, get_pan_status.
