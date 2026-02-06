# Change: Scrub all Odoo branding and replace with Loomworks

## Why

Loomworks ERP is a fork of Odoo Community v18 (LGPL v3). Users and customers interact with this product as "Loomworks ERP" -- not Odoo. Every user-visible reference to "Odoo" undermines the brand identity, creates confusion about what product customers are using, and gives the impression the product is a white-labeled resale rather than an independent fork. The existing `loomworks_core` module addresses roughly 15% of visible branding (login page, page title, favicon, navbar icon, dialog defaults, brand promotion). The remaining ~85% of user-visible Odoo references in error dialogs, email templates, report headers, POS screens, settings pages, database manager, digest emails, and more are untouched.

## What Changes

### Category 1: UI-Visible Strings (highest priority -- no breakage risk)
- **Error dialogs** (8 references): "Odoo Error", "Odoo Warning", "Odoo Session Expired", "Odoo Server Error", "Odoo Client Error", "Odoo Network Error" in `web/static/src/core/errors/error_dialogs.js` and `error_dialogs.xml`
- **Session expired notification** (2 references): `web/static/src/public/error_notifications.js`
- **Report title fallback** (2 references): "Odoo Report" in `web/views/report_templates.xml`
- **Database manager** (4 references): Title and text in `web/static/src/public/database_manager.qweb.html`
- **Settings page edition** (2 references): "Odoo <version> (Community Edition)" and Odoo S.A. copyright in `res_config_edition.xml`
- **Upgrade dialog** (2 references): "Odoo Enterprise" title and body in `upgrade_dialog.xml`
- **Spreadsheet title** (2 references): "Odoo Spreadsheet" in `spreadsheet/static/src/hooks.js`
- **POS title** (1 reference): "Odoo POS" in `point_of_sale/views/pos_assets_index.xml`
- **POS self-order** (1 reference): "Odoo Self Order" in `pos_self_order/views/pos_self_order.index.xml`
- **POS error handler** (1 reference): "Odoo Server Error" in `point_of_sale/static/src/app/errors/error_handlers.js`
- **POS OdooLogo** (2 references): "Powered by <OdooLogo>" in customer display XML
- **Calendar view** (2 references): "Odoo meeting" button labels in `calendar/views/calendar_views.xml`
- **Calendar email templates** (4 references): "Join with Odoo Discuss" in `calendar/data/mail_template_data.xml`
- **Website templates** (~15 references): CTA snippets ("50,000+ companies run Odoo"), version info, meta generator, etc.
- **Website snippets** (~8 references): "Odoo Menu" label, CTA boxes, countdown placeholder
- **Mass mailing snippets** (~5 references): Text blocks referencing Odoo
- **Mass mailing themes** (~30+ references): Social media links to facebook.com/Odoo, twitter.com/Odoo, "Odoo Experience" event text
- **Portal footer** (1 reference): "Powered by ... Odoo Logo" in `portal/views/portal_templates.xml`
- **Livechat** (1 reference): "Powered by Odoo" in `im_livechat/views/im_livechat_channel_templates.xml`
- **Marketing card** (1 reference): "Powered By Odoo" in `marketing_card/views/card_frontend_templates.xml`
- **Various settings views** (~10 references): Help text in `base_setup`, `mass_mailing`, `hr_attendance`, `account`, etc.
- **Digest tips & emails** (~8 references): "Tip: A calculator in Odoo", "Odoo Mobile", Odoo link text
- **IAP credits** (1 reference): "Start a Trial at Odoo" in `iap/static/src/js/insufficient_credit_error_handler.js`
- **Web editor** (3 references): ChatGPT dialog "OdooBot" label, editor test title, URL placeholders

### Category 2: Email Templates (high priority -- customer-facing)
- **Auth signup** (~10 references): "Welcome to Odoo", "invites you to connect to Odoo", "Enjoy Odoo!", "Odoo Tour", "Powered by Odoo" across `auth_signup/data/mail_template_data.xml` and `auth_signup/views/auth_signup_templates_email.xml`
- **Auth signup password reset** (1 reference): "Odoo account linked to this email"
- **HR expense** (1 reference): "Powered by Odoo" in `hr_expense/data/mail_templates.xml`
- **Website slides** (1 reference): "Powered by Odoo" in `website_slides/data/mail_templates.xml`
- **Mass mailing demo** (1 reference): "Powered by Odoo" in `mass_mailing/demo/mailing_mailing.xml`
- **Mass mailing CRM demo** (1 reference): "Powered by Odoo"
- **Portal invite** (1 reference): "Powered by Odoo" in `portal/data/mail_template_data.xml`
- **Gamification** (1 reference): "Powered by Odoo" in `gamification/data/mail_template_data.xml`
- **Auth signup template** (2 references): "Powered by Odoo" in `auth_signup/data/mail_template_data.xml`
- **Website CRM partner assign** (1 reference): "Powered by Odoo"
- **Website profile** (1 reference): "Powered by Odoo"
- **IM livechat email** (1 reference): "Powered by Odoo"
- **Account Peppol** (1 reference): "uses Odoo to send invoices" in `account_peppol/data/mail_templates_email_layouts.xml`
- **Razorpay OAuth** (1 reference): "linking your Razorpay account with Odoo"
- **Purchase portal** (2 references): "import this document in Odoo", "Not using Odoo?"

### Category 3: OdooBot Rebranding to LoomBot
- **mail_bot module** (~20 references): Field names `odoobot_state`, `odoobot_failed`, variable names, comments. Module name "OdooBot" in manifest.
- **mail_bot_hr** (3 references): Manifest name "OdooBot - HR", view references
- **OdooBot images** (2 files): `mail/static/src/img/odoobot.png`, `odoobot_transparent.png`
- **CSS class** (1 reference): `.o_odoobot_command` in `mail_bot/static/src/scss/odoobot_style.scss`
- **Digest tip** (1 reference): "@OdooBot" in digest tips data
- **ChatGPT dialog** (1 reference): "OdooBot" label in `web_editor` XML

### Category 4: Configuration & Service Files (requires careful change)
- **release.py** (1 reference): `nt_service_name = "odoo-server-..."` -- partially done, needs NT service name update
- **Web manifest** (~8 references): PWA scope `/odoo`, icon paths `odoo-icon-*.png`, app name fallback 'Odoo'
- **Config.py** (~10 references): `.odoorc`, data directory references, log handler prefixes
- **IoT Box** (~5 references): "Odoo's IoT Box" titles in HTML pages
- **Server banner** (1 reference): `setproctitle('odoo: ...')` in server.py

### Category 5: Image Assets (visual branding)
- **17 image files** with "odoo" in filename across `web/static/img/`, `mail/static/src/img/`, and others
- These include `odoo_logo.svg`, `odoo_logo_dark.svg`, `odoo-icon-*.png`, `odoo_logo_tiny.png`, OdooBot avatars

### Category 6: EDI/Government Integration Identifiers (requires careful evaluation)
- **l10n_es_edi_tbai** (3 references): `'software_name': 'Odoo SA'` -- government-registered software identity
- **l10n_hu_edi** (2 references): `'softwareName': 'Odoo Enterprise'`, `'softwareDevName': 'Odoo SA'`
- **l10n_pl_edi** (1 reference): `<SystemInfo>Odoo</SystemInfo>` in FA3 template
- **account_edi_ubl_cii** (4 references): PDF metadata "Odoo" as Producer/Creator
- **l10n_hr_edi** (1 reference): `'Saodoo-001'` SoftwareID
- **Payment providers** (2 references): `'name': 'Odoo'` in Adyen and Stripe transactions

### Category 7: FULL FORK — Structural Rename (permanent fork, no upstream compatibility needed)
- **Python package rename**: ~7,300 files — `from odoo import` → `from loomworks import`, `import odoo` → `import loomworks`, rename `odoo/odoo/` directory to `odoo/loomworks/`
- **JS module directives**: ~3,200 files — `@odoo-module` → `@loomworks-module`
- **XML root tags**: ~3,600 files — `<odoo>` → `<loomworks>`, update XML parser in `convert.py`
- **URL routes**: `/odoo/...` → `/loomworks/...` (~20 references)
- **Binary/config**: `odoo-bin` → `loomworks-bin`, `.odoorc` → `.loomworksrc`, `odoo.conf` → `loomworks.conf`
- **Service files**: `odoo.service` → `loomworks.service`
- **ORM references**: Update all `odoo.models`, `odoo.fields`, `odoo.api` references to `loomworks.*`
- **CSS class prefix**: Keep `o_` prefix (not branding, just a naming convention — changing would be gratuitous risk with no user benefit)
- **Translation files (po/pot)**: ~18,700 files — update "Translation of Odoo Server" headers to "Translation of Loomworks ERP"
- **X-Odoo headers**: Rename to `X-Loomworks-*` (update email integration docs accordingly)
- **External dependencies**: `fonts.odoocdn.com` (self-host fonts), `odoo_ui_icons` font family (keep as-is, internal name)

## Impact

- **Affected specs**: None currently (no specs exist yet)
- **Affected code**: ~200 files across 40+ Odoo addon modules, plus core files
- **Affected modules**: web, mail, mail_bot, mail_bot_hr, calendar, portal, auth_signup, digest, mass_mailing, mass_mailing_themes, mass_mailing_crm, point_of_sale, pos_self_order, website, website_slides, im_livechat, iap, spreadsheet, base_setup, account, hr_expense, hr_attendance, marketing_card, crm, stock, purchase, gamification, website_crm_partner_assign, website_profile, web_editor, account_peppol, l10n_* localization modules
- **Strategy**: FULL FORK — direct core file edits everywhere. No overlay/override approach. All changes made directly in the base build. This is a permanent fork from Odoo with no need for upstream compatibility.
- **Breaking change risk**: LOW for Categories 1-5 (branding strings, images, config). MEDIUM for Category 6 (government EDI identifiers may be registered). Category 7 items (Python package, XML tags, JS modules, CSS, URL routes) are NOW IN SCOPE as part of the permanent fork — these carry HIGH risk but are mitigated by comprehensive testing.
- **Legal note**: LGPL v3 permits rebranding and forking. Original copyright notices must be preserved. "Based on Odoo Community" attribution is already present in release.py and module headers.
