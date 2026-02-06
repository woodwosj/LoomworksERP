## Context

Loomworks ERP is a fork of Odoo Community v18 (LGPL v3). The product must present itself as "Loomworks ERP" to all users. Currently, the `loomworks_core` module handles approximately 15% of visible branding through QWeb template inheritance and JS service overrides:

**Already handled by loomworks_core:**
- Login page logo and "Powered by" text (QWeb inheritance of `web.login_layout`)
- Page `<title>` fallback to "Loomworks ERP" (QWeb inheritance of `web.layout`)
- Favicon (QWeb inheritance of `web.layout`)
- Brand promotion message (QWeb inheritance of `web.brand_promotion_message`)
- Apple touch icon (QWeb inheritance of `web.webclient_bootstrap`)
- Browser tab title service (JS `title` service override)
- Dialog default title (JS `Dialog` component patch)
- Navbar brand icon (Owl NavBar extension template)
- OdooBot documentation links (Python `mail.bot` method override)
- Color palette and SCSS variables
- Custom images: logo, icon, favicon (PNG and ICO)

**Not handled (~85% of user-visible references):**
- Error dialog titles (8 occurrences in JS)
- Session expired notifications (2 occurrences in JS)
- Report title fallback (2 occurrences in XML)
- Database manager page (4 occurrences in HTML)
- Settings page edition info (2 occurrences in XML)
- All email templates (~25 "Powered by Odoo" links, signup flows, etc.)
- POS titles and branding (5+ occurrences)
- Calendar "Odoo meeting" and "Odoo Discuss" labels (6 occurrences)
- Website CTA snippets, meta generator, version info (~25 occurrences)
- Mass mailing themes social links (~30 facebook.com/Odoo etc.)
- Digest emails and tips (~8 occurrences)
- Portal footer (1 occurrence)
- Livechat branding (1 occurrence)
- All OdooBot references in mail_bot module (~20 occurrences)
- Image assets (17 files with "odoo" in filename)
- PWA webmanifest (8 references)
- IoT Box pages (5 references)
- EDI software identifiers (11 references in l10n_* modules)

## Goals / Non-Goals

### Goals
1. Replace ALL user-visible "Odoo" text with "Loomworks ERP" (or appropriate variant)
2. Replace ALL Odoo logos/icons with Loomworks equivalents
3. Replace ALL "Powered by Odoo" links with Loomworks links
4. Rebrand OdooBot to LoomBot in all user-visible contexts
5. Replace email template branding consistently
6. Update PWA manifest with Loomworks branding
7. Update database manager page
8. Preserve LGPL v3 attribution to Odoo S.A. as original author
9. Maintain all existing functionality without breakage

### Non-Goals
1. **DO NOT** rename CSS class prefixes (`o_`, `o-`) — not branding, just a convention, and changing would break thousands of selectors with no user benefit
2. **DO NOT** change `fonts.odoocdn.com` CDN references — external service hostname we don't control (self-host in future)
3. **DO NOT** change `odoo_ui_icons` font family name — internal CSS font name, no user visibility
4. **DO NOT** change Google Calendar `odoo_id` sync property — stored in external Google events, would break existing calendar sync

## Decisions

### Decision 1: Full Fork — Direct Core Edits Everywhere

**What:** Edit ALL core files directly. No overlay/override approach. This is a permanent fork from Odoo with no intention of merging upstream changes.

**Why:** The user has decided to permanently fork from Odoo. There is no need to maintain compatibility with upstream Odoo or minimize core edits for merge tracking. Direct edits are simpler, more maintainable, and eliminate the complexity of the override layer.

**Implementation breakdown:**
- **Phase 1: User-visible branding** (~200 files): Direct string replacements in JS, XML, HTML, Python across all core addons. Replace all "Odoo" → "Loomworks ERP" in user-facing contexts.
- **Phase 2: Structural rename** (~14,000+ files): Rename Python package `odoo` → `loomworks`, XML root tags `<odoo>` → `<loomworks>`, JS directives `@odoo-module` → `@loomworks-module`, binary `odoo-bin` → `loomworks-bin`, config files.
- **Phase 3: Email templates**: Direct edits to all XML data files containing email templates.
- **Phase 4: Image assets**: Replace all `odoo-*.png/svg` files with Loomworks equivalents.
- **Phase 5: Config/service**: Rename `.odoorc` → `.loomworksrc`, `odoo.conf` → `loomworks.conf`, systemd service.

### Decision 2: Email Template Strategy

**What:** Direct edits to ALL XML data files containing email templates across all modules. Additionally, a one-time migration script updates existing database records for already-installed instances.

**Why:** Since this is a permanent fork, we edit the source XML files directly. This ensures any fresh install gets Loomworks branding from the start. For existing installs, a migration script handles the database records.

### Decision 3: Image Replacement Strategy

**What:** Place Loomworks-branded images (logo SVG, icons PNG/ICO, OdooBot replacement) in `loomworks_core/static/src/img/` and use Odoo's asset override mechanism where possible. For images that cannot be overridden, replace the file content in the original paths.

**Why:** Some images are referenced by hardcoded paths in JS/CSS that cannot be overridden via module inheritance (e.g., `odoo_logo.svg` referenced in website configurator SCSS). The safest approach is to replace the original file contents with Loomworks equivalents while keeping the original filenames, and add Loomworks-named copies for new references.

### Decision 4: OdooBot to LoomBot Rebranding

**What:** Create an override in loomworks_core that:
1. Overrides the `partner_root` (OdooBot) partner name to "LoomBot" via data XML
2. Overrides all mail_bot Python methods via inheritance (partially done already)
3. Patches the CSS class `.o_odoobot_command` to also apply as `.o_loombot_command` (alias)
4. Replaces OdooBot avatar images

**Why:** OdooBot is user-facing and appears in chat, onboarding flows, and digest tips. The existing loomworks_core already overrides some mail_bot behavior but does not rename the bot or replace its avatar.

### Decision 5: EDI/Government Software Identifiers

**What:** DO NOT change government-registered software identifiers in l10n_es_edi_tbai, l10n_hu_edi, l10n_pl_edi, l10n_hr_edi modules for the initial release. Flag for per-country evaluation.

**Why:** These identifiers (e.g., "Odoo SA" software name for Spanish TicketBAI, Hungarian NAV) are registered with government tax authorities. Changing them could cause invoice rejections. Each country's requirements need separate legal/technical evaluation before any change. Loomworks must register its own software identity with each authority before replacing these values.

**Future work:** As Loomworks registers with each tax authority, update the corresponding l10n_* module with Loomworks-specific identifiers.

### Decision 6: Payment Provider Descriptions

**What:** Change `'name': 'Odoo'` in Adyen and Stripe transaction metadata to `'name': 'Loomworks ERP'`. Change `'description': 'Odoo Partner: ...'` in Stripe to `'Loomworks Partner: ...'`.

**Why:** These appear in payment processor dashboards and customer bank statements. They should reflect the actual product name.

### Decision 7: Translation Files (po/pot)

**What:** DO NOT modify the ~18,700 translation files. The "Odoo" references in these files are metadata headers ("Translation of Odoo Server") and translator credits, not user-visible strings.

**Why:** Modifying 18,700 files would create massive git diffs with no user-visible benefit. The translatable strings that appear in the UI are already covered by Categories 1-3 above. When Odoo translates a string like `_t("Odoo Error")` and we change the source string, the translation system will naturally handle the update.

## Risks / Trade-offs

### Risk 1: Upstream Merge Conflicts
- **Impact**: Medium
- **Mitigation**: Minimize direct core edits. Track all edited files in a manifest. When merging upstream Odoo updates, check the manifest for conflicts. The hybrid approach limits direct edits to ~50 files rather than ~200.

### Risk 2: EDI Identifier Changes Breaking Tax Compliance
- **Impact**: Critical
- **Mitigation**: Decision 5 explicitly defers EDI changes. No risk in initial release.

### Risk 3: Missed "Odoo" References
- **Impact**: Low (cosmetic only)
- **Mitigation**: After implementation, run a full-codebase grep for remaining user-visible "Odoo" strings. Create a CI check that flags new "Odoo" references in user-visible contexts (XML string=, title=, help=, JS _t() calls).

### Risk 4: Post-Init Hook Overwriting User Customizations
- **Impact**: Medium
- **Mitigation**: The post_init_hook for email templates should only modify records that still contain the original Odoo text. If a user has already customized a template, skip it. Use `LIKE '%odoo.com%'` as the detection criterion.

### Risk 5: Breaking OdooBot Onboarding Flow
- **Impact**: Low
- **Mitigation**: The onboarding state machine uses `odoobot_state` field name internally (not changed). Only the display name, avatar, and documentation links change. Test the full onboarding flow after implementation.

## Migration Plan

### Phase Order (implement in this sequence)

1. **Image assets first** -- Create all required Loomworks images (LoomBot avatar, PWA icons, logos). These are prerequisites for all other changes.
2. **JS patches in loomworks_core** -- Error dialogs, session expired notifications, spreadsheet titles. These are self-contained and easily testable.
3. **QWeb template overrides in loomworks_core** -- Settings edition, POS titles, report titles, calendar labels, portal footer, livechat. Each override is independent and testable.
4. **Email template post_init_hook** -- Single Python function to update all email template records.
5. **Direct core edits** -- Database manager HTML, webmanifest controller, image file replacements. Do these last as they touch the Odoo core.
6. **OdooBot to LoomBot** -- Partner name override, avatar replacement, CSS alias. Test onboarding flow.
7. **Digest and website content** -- CTA snippets, digest tips, meta generator. Lower priority as these are less frequently seen.

### Rollback Strategy

- **loomworks_core changes**: Uninstalling the module (or removing specific template/JS files) instantly reverts all override-based changes.
- **Direct core edits**: Tracked in git. `git checkout odoo/` reverts all core changes.
- **Email template hook**: A reverse hook can restore original "Odoo" text, or templates can be reset from XML data files.
- **Image replacements**: Original images preserved in git history.

### Testing Plan

1. **Visual audit**: Navigate every major screen (login, backend, POS, website, settings, database manager) and verify no "Odoo" text is visible
2. **Email verification**: Trigger each email template type and verify branding
3. **OdooBot test**: Run the full onboarding conversation flow
4. **POS test**: Open POS, customer display, self-order
5. **Report test**: Print a sample invoice/SO/PO and verify title
6. **PWA test**: Install as PWA from browser, verify icon and name
7. **Regression**: Run Odoo's standard test suite to confirm no breakage
8. **CI grep check**: Automated scan for remaining "Odoo" in user-visible contexts

## Open Questions

1. **LoomBot avatar**: Do we have a designed LoomBot character/avatar image, or should we create one?
2. **Mass mailing themes**: The social media links point to facebook.com/Odoo and twitter.com/Odoo. Should these be removed entirely, pointed to Loomworks social accounts, or left as generic placeholders?
3. **IoT Box**: The IoT Box/PosBox HTML pages reference "Odoo's IoT Box". Since Loomworks may not ship IoT hardware, should these be left as-is or rebranded to "Loomworks IoT Box"?
4. **Odoo CDN (fonts.odoocdn.com)**: This is an external service. We cannot change the hostname. Should we self-host fonts instead?
5. **Website configurator**: The website builder configurator shows the Odoo logo during setup. The SCSS references `odoo_logo.svg` -- should we replace the file content or add a CSS override?
6. **EDI registration timeline**: When will Loomworks register as a software provider with Spanish TicketBAI, Hungarian NAV, Polish KSeF, etc.?
