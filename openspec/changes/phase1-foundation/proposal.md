# Change: Phase 1 Foundation and Branding

## Why

Loomworks ERP requires a distinct brand identity separate from Odoo to establish market presence and avoid user confusion. Unlike a simple branding module overlay, this phase performs a **complete fork with full branding removal** from the Odoo Community v18 source code. This approach ensures:

1. No accidental Odoo branding leaks in edge cases or obscure UI paths
2. Complete control over the codebase for future modifications
3. Clean separation between upstream Odoo and Loomworks customizations
4. Proper LGPL v3 compliance with clear attribution

This is the essential first step before any feature development can begin.

## What Changes

### Fork Infrastructure
- **NEW** Complete copy of Odoo Community v18 in `/odoo/` directory (not submodule)
- **NEW** Automated rebrand script (`scripts/rebrand.py`) for ongoing maintenance
- **NEW** Asset directory (`/assets/`) for Loomworks logo source files

### Source Code Modifications (Fork Level)
- **MODIFIED** `odoo/odoo/release.py` - Product name, description, URLs
- **MODIFIED** `odoo/addons/web/views/webclient_templates.xml` - Page titles, logos, favicon
- **MODIFIED** `odoo/addons/web/static/img/` - Replace all logo/icon files
- **MODIFIED** `odoo/addons/mail/data/mail_templates_email_layouts.xml` - Email footer
- **MODIFIED** `odoo/addons/base/data/res_company_data.xml` - Default company
- **DELETED** `odoo/addons/web/static/img/enterprise_upgrade.jpg` - Remove Enterprise upsell
- **MODIFIED** Multiple JS/SCSS/XML files with "Odoo" string references

### Module Infrastructure
- **NEW** `loomworks_addons/loomworks_core/` module with complete manifest
- **NEW** Custom SCSS theme with Loomworks color palette
- **NEW** Logo assets in multiple resolutions (favicon, navbar, login, PWA icons)
- **NEW** QWeb template overrides for runtime branding (backup to fork changes)
- **NEW** Default company data with Loomworks information

### Documentation
- **NEW** `README.md` with Odoo S.A. attribution (LGPL v3 requirement)
- **NEW** `docs/installation.md` installation guide
- **NEW** `docs/branding.md` rebrand process documentation
- **NEW** `docs/upstream-sync.md` guide for syncing with Odoo updates

## Impact

- Affected specs: `loomworks-core` (new capability)
- Affected code:
  - `/odoo/` - Complete forked Odoo codebase with branding modifications
  - `/loomworks_addons/loomworks_core/` - Runtime branding module
  - `/scripts/rebrand.py` - Automated rebranding tool
  - Asset bundles: `web._assets_primary_variables`, `web.assets_backend`, `web.assets_frontend`
- Dependencies: None (self-contained with forked Odoo)
- Legal: LGPL v3 compliance with Odoo S.A. copyright attribution preserved

## Scope

This proposal covers **Phase 1 (Weeks 1-4)** of the implementation plan:

### Week 1: Fork and Asset Preparation
1. Fork Odoo Community v18 repository (full copy, not submodule)
2. Create directory structure (`scripts/`, `assets/`, `docs/`, `loomworks_addons/`)
3. Design and create Loomworks logo assets in all required formats

### Week 2: Rebrand Script and Core Modifications
4. Develop automated rebrand script with check/apply/verify modes
5. Modify `release.py` and core Python files
6. Replace all logo/icon files in web addon

### Week 3: Template and Email Branding
7. Modify `webclient_templates.xml` (titles, logos, "Powered by" links)
8. Update email templates in mail addon
9. Review and update portal, website, and other addons

### Week 4: Module Development and Testing
10. Create `loomworks_core` branding module
11. Implement SCSS color palette
12. Comprehensive testing across all UI paths
13. Documentation and validation

## Success Criteria

### Branding Completeness
1. Zero instances of "Odoo" visible in user-facing UI (excluding legal attribution)
2. All logo files replaced with Loomworks assets
3. Custom color palette applied consistently (theme color `#1e3a5f`)
4. Favicon and PWA icons show Loomworks branding
5. Email templates show Loomworks branding in footer

### Verification Tests
6. `python scripts/rebrand.py --verify` returns 0 issues
7. `grep -r "odoo.com" --include="*.xml" --include="*.js" odoo/addons/web/` returns 0 results (excluding LICENSE/copyright)
8. `grep -r "Powered by Odoo"` returns 0 results

### Compliance
9. LGPL v3 license file present at repository root
10. Odoo S.A. copyright preserved in modified file headers
11. README includes clear Odoo attribution
12. About dialog mentions "Based on Odoo Community Edition"

### Functionality
13. Fresh installation completes without errors
14. `loomworks_core` module installs without errors
15. Asset bundling works (no console errors)
16. All major UI views render correctly with branding

## Files Modified Summary

| Category | Estimated Files | Key Files |
|----------|-----------------|-----------|
| Core Python | 5-10 | `release.py`, `http.py`, `server.py` |
| Web Addon Images | 12 | All `odoo-*` and `odoo_*` files |
| Web Addon Templates | 1 | `webclient_templates.xml` |
| Mail Addon | 2-3 | `mail_templates_email_layouts.xml` |
| Other Addons | 10-20 | Various templates with branding |
| JavaScript | 5-10 | User-visible strings |
| New Loomworks Module | 10+ | Complete module structure |
| Documentation | 5 | README, docs/, LICENSE |

## Research References

- [Odoo 18 Repository Structure](https://github.com/odoo/odoo)
- [LGPL v3 License Requirements](https://www.gnu.org/licenses/lgpl-3.0.en.html)
- [Odoo 18 Asset Bundling](https://www.odoo.com/documentation/18.0/developer/reference/frontend/assets.html)
- [Odoo 18 SCSS Inheritance](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/scss_inheritance.html)
- [OCA Debranding Approaches](https://github.com/OCA/web/tree/18.0/web_favicon)
