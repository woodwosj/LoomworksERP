## 1. Image Assets (Prerequisites)
- [ ] 1.1 Create LoomBot avatar PNG (48x48, 128x128) to replace `mail/static/src/img/odoobot.png` and `odoobot_transparent.png`
- [ ] 1.2 Create Loomworks PWA icons: 192x192 and 512x512 PNG (to replace `web/static/img/odoo-icon-192x192.png` and `odoo-icon-512x512.png`)
- [ ] 1.3 Create Loomworks iOS icon PNG (to replace `web/static/img/odoo-icon-ios.png`)
- [ ] 1.4 Create Loomworks SVG logo (to replace `web/static/img/odoo_logo.svg` and `odoo_logo_dark.svg`)
- [ ] 1.5 Create Loomworks tiny logo PNG (to replace `web/static/img/odoo_logo_tiny.png`)
- [ ] 1.6 Create Loomworks icon SVG (to replace `web/static/img/odoo-icon.svg`)
- [ ] 1.7 Create Loomworks Win32 icon ICO (to replace `setup/win32/static/pixmaps/odoo-icon.ico`)
- [ ] 1.8 Place all new images in `loomworks_core/static/src/img/` AND replace originals in `web/static/img/`

## 2. JS Patches in loomworks_core
- [ ] 2.1 Create `loomworks_core/static/src/js/error_dialog_patch.js` -- patch `ErrorDialog.title`, `ClientErrorDialog.title`, `NetworkErrorDialog.title`, `RPCErrorDialog`, `WarningDialog`, `SessionExpiredDialog` to replace "Odoo" with "Loomworks ERP" (8 string replacements in `web/static/src/core/errors/error_dialogs.js`)
- [ ] 2.2 Create `loomworks_core/static/src/js/error_notification_patch.js` -- override session expired notification title/message in `web/static/src/public/error_notifications.js` (2 replacements)
- [ ] 2.3 Create `loomworks_core/static/src/js/spreadsheet_patch.js` -- patch "Odoo Spreadsheet" title in `spreadsheet/static/src/hooks.js` (2 replacements)
- [ ] 2.4 Create `loomworks_core/static/src/js/pos_error_patch.js` -- patch POS "Odoo Server Error" title (1 replacement)
- [ ] 2.5 Create `loomworks_core/static/src/js/iap_patch.js` -- patch "Start a Trial at Odoo" button message in `iap/static/src/js/insufficient_credit_error_handler.js` (1 replacement)
- [ ] 2.6 Register all new JS files in `loomworks_core/__manifest__.py` under `web.assets_backend`
- [ ] 2.7 Update `loomworks_core/__manifest__.py` `depends` to include `spreadsheet`, `iap`, `point_of_sale` if patching those modules

## 3. QWeb/XML Template Overrides in loomworks_core
- [ ] 3.1 Override `web.report_layout` -- change fallback title "Odoo Report" to "Loomworks Report" (2 templates in `web/views/report_templates.xml`)
- [ ] 3.2 Override `web.res_config_edition` -- replace "Odoo <version> (Community Edition)" with "Loomworks ERP <version>" and update copyright attribution
- [ ] 3.3 Override `web.upgrade_dialog` -- replace "Odoo Enterprise" title and body text
- [ ] 3.4 Override `web.error_dialogs` -- replace "Odoo Session Expired" title and body text in `error_dialogs.xml`
- [ ] 3.5 Override `point_of_sale.pos_assets_index` -- change `<title>Odoo POS</title>` to `<title>Loomworks POS</title>`
- [ ] 3.6 Override `pos_self_order.pos_self_order_index` -- change `<title>Odoo Self Order</title>`
- [ ] 3.7 Override POS customer display -- replace `<OdooLogo>` references with Loomworks branding
- [ ] 3.8 Override `calendar.calendar_views` -- change "Odoo meeting" button labels (2 references)
- [ ] 3.9 Override `calendar.mail_template_data` -- change "Join with Odoo Discuss" to "Join with Loomworks Discuss" (4 templates)
- [ ] 3.10 Override `portal.portal_templates` -- replace "Powered by ... Odoo Logo" footer with Loomworks
- [ ] 3.11 Override `im_livechat.im_livechat_channel_templates` -- replace "Powered by Odoo"
- [ ] 3.12 Override `marketing_card.card_frontend_templates` -- replace "Powered By Odoo"
- [ ] 3.13 Override `mass_mailing.mailing_templates_portal_layouts` -- change `<title>Odoo</title>`
- [ ] 3.14 Override `mass_mailing.mailing_templates_portal_management` -- change `<title>Odoo</title>`
- [ ] 3.15 Override `base_setup.res_config_settings_views` -- update help text referencing "Odoo" (3 settings)
- [ ] 3.16 Override `mass_mailing.res_config_settings_views` -- update help text referencing "Odoo"
- [ ] 3.17 Override `hr_attendance.res_config_settings_views` -- change "Check in/out from Odoo"
- [ ] 3.18 Override `account.res_config_settings_views` -- change auto-post bills help text
- [ ] 3.19 Override `account.account_move_views` -- change "computed by Odoo" text (2 references)
- [ ] 3.20 Override `iap.res_config_settings` -- change "Odoo IAP" setting string
- [ ] 3.21 Override `account_peppol.peppol_info` -- change "Free on Odoo" to "Free on Loomworks"
- [ ] 3.22 Override `hr_expense.qrcode_action` -- change "Scan this QR code to get the Odoo app"
- [ ] 3.23 Override `mail_plugin.mail_plugin_login` -- change "access your Odoo database"
- [ ] 3.24 Override `web_editor.chatgpt_prompt_dialog` -- change "OdooBot" to "LoomBot"
- [ ] 3.25 Override `purchase.portal_templates` -- change "import this document in Odoo" and "Not using Odoo"
- [ ] 3.26 Override `website.website_templates` -- change CTA text, meta generator, version info, "Odoo Apps" title (at least 8 references)
- [ ] 3.27 Override `website.snippets` -- change "Odoo Menu" label and "Odoo Information" checkbox
- [ ] 3.28 Override website CTA snippets (`s_call_to_action`, `s_cta_box`, `s_cta_card`, `s_cta_mockups`) -- change "run Odoo" text
- [ ] 3.29 Override `website.s_countdown` options -- change "Happy Odoo Anniversary" placeholder
- [ ] 3.30 Override `point_of_sale.report_saledetails` -- change "Odoo Report" fallback title
- [ ] 3.31 Override `crm.res_config_settings_views` -- change "Make and receive calls from Odoo"
- [ ] 3.32 Override `l10n_my_edi.res_config_settings_view` -- change "Odoo will send" and "Odoo will process"
- [ ] 3.33 Override `l10n_pl_edi.res_config_settings_views` -- change "authorize Odoo to process"
- [ ] 3.34 Override `l10n_it_edi.res_config_settings_views` -- change "Allow Odoo to process invoices"
- [ ] 3.35 Override `base_automation.base_automation_views` -- change "webhook coming from another Odoo instance"

## 4. Email Template Rebranding (post_init_hook)
- [ ] 4.1 Create `loomworks_core/hooks.py` with `post_init_hook` function
- [ ] 4.2 Implement `_rebrand_email_templates(env)`: search `mail.template` records with body containing "odoo.com" or "Odoo" and replace with Loomworks equivalents
- [ ] 4.3 Implement `_rebrand_mail_data(env)`: search `ir.model.data` email template-related records
- [ ] 4.4 Handle auth_signup templates: "Welcome to Odoo" -> "Welcome to Loomworks ERP", "invites you to connect to Odoo" -> "invites you to connect to Loomworks ERP", "Enjoy Odoo!" -> "Enjoy Loomworks!", etc. (10+ replacements)
- [ ] 4.5 Handle "Powered by Odoo" links across all email templates: replace href "odoo.com" with "loomworks.solutions" and text "Odoo" with "Loomworks" (~15 templates across auth_signup, portal, gamification, hr_expense, website_slides, im_livechat, mass_mailing, website_crm_partner_assign, website_profile)
- [ ] 4.6 Handle account_peppol template: "uses Odoo to send invoices"
- [ ] 4.7 Handle auth_signup subject line: "invites you to connect to Odoo"
- [ ] 4.8 Register `post_init_hook` in `loomworks_core/__manifest__.py`
- [ ] 4.9 Add upgrade hook (`post_load` or migration script) to run on module update for existing installs

## 5. Direct Core Edits (Minimal Set)
- [ ] 5.1 Edit `web/static/src/public/database_manager.qweb.html`: change `<title>Odoo</title>`, warning text, privacy policy text, database copy text (4 replacements)
- [ ] 5.2 Edit `web/controllers/webmanifest.py`: change `get_param('web.web_app_name', 'Odoo')` default to 'Loomworks ERP', update icon paths, update scope description comment (8 replacements)
- [ ] 5.3 Replace image file contents: copy Loomworks images over original `odoo-icon-*.png`, `odoo_logo*.svg`, `odoo_logo_tiny.png` files in `web/static/img/` (7 files)
- [ ] 5.4 Replace `mail/static/src/img/odoobot.png` and `odoobot_transparent.png` with LoomBot images (2 files)
- [ ] 5.5 Replace `web_editor/static/src/img/odoobot_transparent.png` with LoomBot image (1 file)
- [ ] 5.6 Edit `web/views/speedscope_template.xml`: change "Speedscope for odoo" title
- [ ] 5.7 Edit `odoo/odoo/release.py`: change `nt_service_name` from "odoo-server-" to "loomworks-server-" (1 replacement -- only on Windows)
- [ ] 5.8 Edit `web/static/src/core/errors/error_dialogs.js`: replace "Odoo" in error titles (8 replacements) -- ONLY if JS patch approach (task 2.1) proves infeasible
- [ ] 5.9 Edit `web/static/src/core/dialog/dialog.js`: change default title "Odoo" to "Loomworks ERP" -- ONLY if JS patch approach is already in place (may conflict with existing dialog_patch.js)

## 6. OdooBot to LoomBot
- [ ] 6.1 Add data XML in loomworks_core to override `base.partner_root` partner name from "OdooBot" to "LoomBot"
- [ ] 6.2 Override `mail_bot/__manifest__.py` module name display (via `ir.module.module` record if possible, or accept technical name remains)
- [ ] 6.3 Create LoomBot avatar images and place in `loomworks_core/static/src/img/loombot.png` and `loombot_transparent.png`
- [ ] 6.4 Add CSS in loomworks_core to alias `.o_odoobot_command` styles (keep original class for compatibility, add `.o_loombot_command`)
- [ ] 6.5 Override mail_bot onboarding messages if they reference "OdooBot" by name (check `mail_bot/data/` for user-visible strings)
- [ ] 6.6 Override digest tip data: change "@OdooBot" to "@LoomBot"
- [ ] 6.7 Test full OdooBot onboarding flow: emoji -> command -> ping -> attachment -> canned response

## 7. Digest and Website Content
- [ ] 7.1 Override digest tips data records: change "Tip: A calculator in Odoo", "Odoo Mobile", Odoo link text
- [ ] 7.2 Override digest email template: change Odoo branding in KPI email layout
- [ ] 7.3 Override mass_mailing theme templates: change social media links from facebook.com/Odoo and twitter.com/Odoo to Loomworks social accounts (or generic placeholders)
- [ ] 7.4 Override mass_mailing snippet text blocks: change "open source model of Odoo" and similar content text
- [ ] 7.5 Override website snippet placeholder content (s_table_of_content, CTA snippets, countdown)
- [ ] 7.6 Override `website.s_mega_menu_odoo_menu` template name
- [ ] 7.7 Override website digest tips data
- [ ] 7.8 Override CRM demo data: change "get the most out of Odoo" in demo email template
- [ ] 7.9 Override stock/purchase/mrp digest tips: change references to "Odoo barcode app", "Odoo work center", etc.

## 8. Payment Provider Descriptions
- [ ] 8.1 Override `payment_adyen` transaction metadata: change `'name': 'Odoo'` to `'name': 'Loomworks ERP'` (via Python inheritance in loomworks_core)
- [ ] 8.2 Override `payment_stripe` transaction description: change `'Odoo Partner: ...'` to `'Loomworks Partner: ...'`

## 9. Localization and EDI (Deferred -- per-country evaluation)
- [ ] 9.1 Document which l10n_* modules contain Odoo software identifiers (l10n_es_edi_tbai, l10n_hu_edi, l10n_pl_edi, l10n_hr_edi, account_edi_ubl_cii)
- [ ] 9.2 Research registration requirements for each tax authority
- [ ] 9.3 Register Loomworks as software provider where required
- [ ] 9.4 Update l10n_* identifiers only after registration is complete

## 10. Verification and CI
- [ ] 10.1 Run full visual audit: login, backend, POS, website, settings, database manager
- [ ] 10.2 Trigger all email template types and verify branding
- [ ] 10.3 Test OdooBot/LoomBot onboarding flow
- [ ] 10.4 Test PWA install from browser
- [ ] 10.5 Print sample report (invoice/SO) and verify title
- [ ] 10.6 Run Odoo test suite to confirm no breakage
- [ ] 10.7 Run full-codebase grep for remaining user-visible "Odoo" strings
- [ ] 10.8 Add CI check: grep for "Odoo" in new commits touching user-visible contexts (XML string=, JS _t(), etc.)
- [ ] 10.9 Create manifest file listing all directly edited core files for merge tracking

## 11. Documentation
- [ ] 11.1 Document all changes in loomworks_core module description
- [ ] 11.2 Add upgrade notes for existing Loomworks installs
- [ ] 11.3 Update LGPL attribution to confirm compliance (copyright preserved, fork attribution present)
