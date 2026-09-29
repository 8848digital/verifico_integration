<!--
Copyright (c) 2026 8848 Digital LLP. All rights reserved.
Proprietary and confidential. Unauthorized copying, distribution, or use
of this file, via any medium, is strictly prohibited without prior
written permission from 8848 Digital LLP.
-->

# Verifico Integration

## Overview
Generic Frappe/ERPNext app by 8848 Digital LLP that verifies customers' PAN
(Indian Permanent Account Number) through the Verifico API. Any client can
require a verified PAN on any document above an amount (e.g. sales of
₹2,00,000 or more) — configured with rules, no code changes.

## Key DocTypes

| DocType | Owned by this app? | Purpose |
| ------- | ------------------ | ------- |
| Verifico Settings | Yes | Verifico API URL and key, timeout, result-reuse window, file size limit. |
| PAN Verification Rule | Yes | Which DocType needs a PAN, above what amount, Block or Warn, on Save or Submit. |
| PAN Verification | Yes | Audit record of every check: PAN, result, name on PAN, credits used, document and party. |
| Any DocType with a rule | No (customized) | Gets a "PAN Verification" tab/section (PAN, status, link) and a Verify PAN button. |

## Features
- Verify a PAN by number, or upload the PAN card (image/PDF) to read and verify it.
- Block (or warn) saving/submitting a document above the threshold until its PAN is verified as valid.
- Reuse a recent valid result for the same PAN — no second charge.
- Returning customers: their last verified PAN is pre-filled on new documents, and a
  warning appears if a different PAN is entered for them.
- Credit protection: PAN format and real file type checked before calling, no retry of timed-out calls,
  per-user hourly call limit, only draft documents can be verified.
- Every check is recorded (success, invalid or failure) with credits used.
- Status always follows the PAN on the document; changing the PAN resets it.
- APIs for custom front ends (e.g. POS) to verify and read PAN status.

## Integrations
- **Verifico (PAN verification & PAN card OCR)** — see [SETUP.md](./SETUP.md#verifico-pan-verification)

## Installation

    bench get-app verifico_integration https://github.com/8848digital/verifico_integration --branch develop
    bench --site <site_name> install-app verifico_integration

## App Structure
See [CLAUDE.md](./CLAUDE.md) for internal module/folder layout and coding conventions.

## Contributing
This app uses `pre-commit` for formatting and linting (black, isort, flake8,
prettier, eslint, max-lines check) and Conventional Commits:

    cd apps/verifico_integration
    pre-commit install

Run the tests on a separate test site (never a working site — tests change settings):

    bench --site <test-site> set-config allow_tests true
    bench --site <test-site> run-tests --app verifico_integration

## Maintainers
8848 Digital LLP — mahak@8848digital.com

## License
Proprietary — Copyright (c) 2026 8848 Digital LLP. All rights reserved.
See [license.txt](license.txt) for details.
