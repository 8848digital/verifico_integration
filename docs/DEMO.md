<!--
Copyright (c) 2026 8848 Digital LLP. All rights reserved.
Proprietary and confidential. Unauthorized copying, distribution, or use
of this file, via any medium, is strictly prohibited without prior
written permission from 8848 Digital LLP.
-->

# Verifico Customer Demo Script

This is a click-by-click script for demonstrating PAN verification with the
Verifico Integration app on any site where the app is installed. The
preparation section creates everything the demo needs, so nothing depends on a
particular environment or existing records.

The demo tells a single story: a retailer must collect a verified PAN for
high-value sales. A small order goes through untouched, a large order is
blocked until the customer's PAN is verified, and every check is recorded.

**Login:** your demo site, `Administrator` / (ask your contact for the current
demo password).

**Total runtime:** ~15–20 minutes. Steps 3–6 are the core "rule + enforcement
+ verification" pitch; trim steps 7–9 if you're short on time.

**Credits:** Verifico charges per real check (verification ≈ 3 credits, card
read ≈ 1). Steps marked *(free)* never call Verifico; step 6 needs an account
with purchased credits — skip it and use the talking points if none are
available.

---

## 0. Preparation (~10 min, before the demo)

- **App installed** on the site from the `verifico_integration` repository and
  migrated.
- **Verifico Settings** (`/app/verifico-settings`): Enabled, Base URL
  `https://api.theverifico.com`, API Key = the account's key, Save.
- **Master data** (any names): a Customer (e.g. *Demo Customer*) and an Item
  (e.g. *Demo Jewellery*, non-stock is fine).
- **Two draft Sales Orders** for that customer — do not submit them:
  - **Order A — above the limit:** ₹2,50,000
  - **Order B — below the limit:** ₹1,50,000
- **Test PANs** (don't show real customers' data on screen):
  - Bad format: `ABC12` *(free)*
  - Valid PAN: one you are allowed to show, e.g. a colleague's with consent
  - Invalid PAN: correct format that doesn't exist, e.g. `ABCDE1234Z`
- Pre-open tabs: Verifico Settings, PAN Verification Rule list, Order A,
  Order B, PAN Verification list.

## 1. The problem (1 min)

- High-value sales (e.g. ₹2 lakh and above) require the customer's PAN.
- Today a cashier can type any PAN — nobody checks it is real.
- **Verifico** is a verification API: send a PAN, it answers whether it is
  valid and whose it is.

Frame it: "This app makes the PAN check automatic and enforced — for any
client and any document, with no custom code."

## 2. One-time setup: Verifico Settings (1 min) *(free)*

Open **Verifico Settings** and point out:

- **Enabled** — master switch; when off, nothing is ever blocked.
- **Base URL** and **API Key** — the key is stored encrypted and never shown
  again (don't click into it).
- **Reuse Valid Result For (Days)** — a PAN already verified as valid is
  reused for free.
- **Max Verifico Calls per User per Hour** — protects paid credits from
  overuse.

## 3. Create the rule live (3 min) *(free)*

Open **PAN Verification Rule → New** and fill in:

- **Rule Name:** High Value Sales Order
- **Reference DocType:** Sales Order — could be Sales Invoice, POS Invoice or
  any custom document.
- **Amount Field:** `grand_total`
- **Threshold Amount:** 2,00,000
- **Action:** Block (or **Warn** — message only)
- **Check On:** Submit (or Save)
- **Party Field:** `customer`

Save, then open **Order A** (reload if it was already open) and point out the
new **PAN Verification** tab, the **Verify PAN** button and the orange
**PAN: Not Verified** indicator — all added automatically by saving the rule.

Talking point: each client sets its own document and limit — no code changes.

## 4. Below the limit — no PAN needed (1 min) *(free)*

Open **Order B** (₹1,50,000) and **Submit** — it goes through normally.

Talking point: small sales are never slowed down.

## 5. Above the limit — blocked (2 min) *(free)*

- Open **Order A** (₹2,50,000) and **Submit** — it is refused with *"PAN
  verification is required for Sales Order of ₹2,00,000 or more. Click Verify
  PAN at the top of the form …"*
- Click **Verify PAN**, type `ABC12`, **Verify** — *"ABC12 is not a valid PAN
  format …"*

Talking point: wrong formats are rejected before calling Verifico, so no
money is spent.

## 6. Verify a real PAN (3 min) *(uses credits)*

- **Verify PAN** with `ABCDE1234Z` — reported **Invalid** (red) with
  Verifico's message; the order stays blocked.
- **Verify PAN** with the valid test PAN — **PAN Valid** with the name on the
  PAN, category and credits used; the status turns green.
- **Submit** Order A — it now goes through.
- Create another draft order above the limit for the same customer and
  **Verify PAN** with the same valid PAN — *Credits Used: 0 (recent result
  reused)*.

Talking point: repeat customers aren't charged twice.

## 7. The status follows the PAN (optional, 1 min) *(free)*

On a verified draft order, change the **PAN Number** to a different PAN and
**Save** — the status goes back to **Not Verified**.

Talking point: if someone edits the PAN after verification, the verification
no longer counts.

## 8. Audit trail (2 min) *(free)*

Open the **PAN Verification** list. Every check is recorded — valid, invalid
or failed — with the status, name on PAN, credits used, *Reused From* on free
repeats, the document and customer it belongs to, and Verifico's own message
on any failed check.

## 9. Other capabilities (1 min)

- **PAN card upload:** attach a photo/PDF of the card instead of typing; the
  app reads and verifies it (uses credits).
- **APIs** for custom screens such as a POS: verify a PAN, read a card, check
  whether an order still needs a PAN.
- **Safeguards:** no double charge on time-outs, per-user hourly limit, only
  draft documents can be verified, real file-type checks.
- **Works on plain Frappe** (not only ERPNext); covered by automated tests.

---

## Notes for whoever runs this demo

- **Cost per check:** Verifico charges per call (≈ ₹2 per verification, ₹0.50
  per card read; failed checks are free). Reuse keeps repeat customers free.
- **Other documents:** create a rule for Sales Invoice (or any document) with
  its own limit — same behaviour.
- **Warn instead of block:** set **Action = Warn**.
- **Verifico down or out of credits:** the user sees Verifico's exact reason;
  switching the integration off stops all blocking.
- **API key:** encrypted in Verifico Settings, visible only to administrators.
- **Running it again:** steps 4–6 submit the demo orders — create fresh draft
  orders A and B (step 0) before the next run. The rule and settings can stay.
