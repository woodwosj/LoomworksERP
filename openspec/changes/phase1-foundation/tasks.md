# Tasks: Phase 1 Foundation and Branding

## 0. Odoo Fork and Setup (CRITICAL - Do First)

### 0.1 Repository Fork
- [ ] 0.1.1 Clone Odoo Community v18: `git clone --branch 18.0 --depth 1 https://github.com/odoo/odoo.git odoo`
- [ ] 0.1.2 Remove git history from fork: `rm -rf odoo/.git`
- [ ] 0.1.3 Verify fork structure: `ls odoo/` should show `addons/`, `odoo/`, `odoo-bin`, etc.
- [ ] 0.1.4 Create scripts directory: `mkdir -p scripts`
- [ ] 0.1.5 Create assets directory for Loomworks logos: `mkdir -p assets`
- [ ] 0.1.6 Create docs directory: `mkdir -p docs`

### 0.2 Loomworks Logo Assets (Prerequisite for Rebrand)
- [ ] 0.2.1 Create/obtain `assets/loomworks_favicon.ico` (16x16, 32x32 multi-res)
- [ ] 0.2.2 Create/obtain `assets/loomworks_favicon.png` (192x192)
- [ ] 0.2.3 Create/obtain `assets/loomworks_logo.png` (200x50, horizontal)
- [ ] 0.2.4 Create/obtain `assets/loomworks_logo_white.png` (200x50, white on transparent)
- [ ] 0.2.5 Create/obtain `assets/loomworks_logo.svg` (vector, horizontal)
- [ ] 0.2.6 Create/obtain `assets/loomworks_logo_dark.svg` (for dark mode)
- [ ] 0.2.7 Create/obtain `assets/loomworks_logo_tiny.png` (62x20)
- [ ] 0.2.8 Create/obtain `assets/loomworks_logo_alt.png` (alternative logo)
- [ ] 0.2.9 Create/obtain `assets/loomworks_icon.svg` (square icon, vector)
- [ ] 0.2.10 Create/obtain `assets/loomworks_icon_192.png` (192x192)
- [ ] 0.2.11 Create/obtain `assets/loomworks_icon_512.png` (512x512)
- [ ] 0.2.12 Create/obtain `assets/loomworks_icon_ios.png` (iOS format)

### 0.3 Rebrand Script Development
- [ ] 0.3.1 Create `scripts/rebrand.py` with configuration constants
- [ ] 0.3.2 Implement string replacement function for text files
- [ ] 0.3.3 Implement file replacement function for images
- [ ] 0.3.4 Implement copyright header updater for Python files
- [ ] 0.3.5 Implement `--check` mode (dry run, report only)
- [ ] 0.3.6 Implement `--apply` mode (make changes)
- [ ] 0.3.7 Implement `--verify` mode (check for missed branding)
- [ ] 0.3.8 Implement `--report` mode (generate detailed CSV/JSON)
- [ ] 0.3.9 Add skip patterns for LICENSE, .po files, etc.
- [ ] 0.3.10 Test script on sample files

### 0.4 Core Framework Rebrand (`odoo/odoo/`)
- [ ] 0.4.1 Modify `release.py`: Change product name "Odoo" -> "Loomworks ERP"
- [ ] 0.4.2 Modify `release.py`: Change description "Odoo Server" -> "Loomworks ERP Server"
- [ ] 0.4.3 Modify `release.py`: Change author to include Loomworks attribution
- [ ] 0.4.4 Modify `release.py`: Change URL to loomworks.app
- [ ] 0.4.5 Update copyright headers in modified Python files
- [ ] 0.4.6 Search and replace "odoo.com" URLs in `http.py`, `service/server.py`
- [ ] 0.4.7 Update CLI help text in `cli/command.py`

### 0.5 Web Addon Rebrand (`odoo/addons/web/`)
- [ ] 0.5.1 Replace `static/img/favicon.ico` with Loomworks favicon
- [ ] 0.5.2 Replace `static/img/logo.png` with Loomworks logo
- [ ] 0.5.3 Replace `static/img/logo2.png` with Loomworks alt logo
- [ ] 0.5.4 Replace `static/img/logo_inverse_white_206px.png` with white logo
- [ ] 0.5.5 Replace `static/img/odoo-icon-192x192.png` with Loomworks icon
- [ ] 0.5.6 Replace `static/img/odoo-icon-512x512.png` with Loomworks icon
- [ ] 0.5.7 Replace `static/img/odoo-icon-ios.png` with Loomworks icon
- [ ] 0.5.8 Replace `static/img/odoo-icon.svg` with Loomworks icon
- [ ] 0.5.9 Replace `static/img/odoo_logo.svg` with Loomworks logo
- [ ] 0.5.10 Replace `static/img/odoo_logo_dark.svg` with Loomworks dark logo
- [ ] 0.5.11 Replace `static/img/odoo_logo_tiny.png` with Loomworks tiny logo
- [ ] 0.5.12 DELETE `static/img/enterprise_upgrade.jpg`
- [ ] 0.5.13 Modify `views/webclient_templates.xml`: Update page titles
- [ ] 0.5.14 Modify `views/webclient_templates.xml`: Update favicon paths
- [ ] 0.5.15 Modify `views/webclient_templates.xml`: Update logo paths
- [ ] 0.5.16 Modify `views/webclient_templates.xml`: Remove/update "Powered by Odoo" links
- [ ] 0.5.17 Modify `views/webclient_templates.xml`: Update odoo.com URLs
- [ ] 0.5.18 Modify `views/webclient_templates.xml`: Update theme color from `#71639e`
- [ ] 0.5.19 Update `static/src/scss/primary_variables.scss`: Change `$o-brand-odoo` color
- [ ] 0.5.20 Search JS files for "Odoo" strings and replace in user-visible contexts
- [ ] 0.5.21 Update PWA manifest (`manifest.webmanifest.mako` or similar)

### 0.6 Mail Addon Rebrand (`odoo/addons/mail/`)
- [ ] 0.6.1 Modify `data/mail_templates_email_layouts.xml`: Update footer branding
- [ ] 0.6.2 Modify `data/mail_templates_email_layouts.xml`: Remove "Powered by Odoo"
- [ ] 0.6.3 Review `data/mail_templates_chatter.xml` for branding
- [ ] 0.6.4 Review `data/mail_templates_invite.xml` for branding

### 0.7 Base Addon Rebrand (`odoo/odoo/addons/base/`)
- [ ] 0.7.1 Modify `data/res_company_data.xml`: Update default company name
- [ ] 0.7.2 Review `data/res_partner_data.xml` for branding
- [ ] 0.7.3 Update Python file copyright headers

### 0.8 Portal Addon Rebrand (`odoo/addons/portal/`)
- [ ] 0.8.1 Modify `data/mail_templates.xml`: Update portal email branding
- [ ] 0.8.2 Review `views/` for "Powered by Odoo" references

### 0.9 Website Addon Rebrand (`odoo/addons/website/`)
- [ ] 0.9.1 Review `static/` for branding assets
- [ ] 0.9.2 Review `views/` for public website branding
- [ ] 0.9.3 Review `data/` for default website content with Odoo branding

### 0.10 Other Addons Quick Scan
- [ ] 0.10.1 DELETE or replace `account/static/src/img/Odoo_logo_O.svg`
- [ ] 0.10.2 Search all addons for "odoo.com" URLs
- [ ] 0.10.3 Search all addons for "Powered by Odoo" strings
- [ ] 0.10.4 Search all addons for "Odoo S.A." (preserve in copyright, remove from UI)

## 1. Repository Setup (Post-Fork)
- [ ] 1.1 Create `loomworks_addons/` directory structure
- [ ] 1.2 Copy LICENSE file from odoo/ to repository root
- [ ] 1.3 Create `.gitignore` for Python/Odoo project
- [ ] 1.4 Create initial README.md with project overview and Odoo attribution
- [ ] 1.5 Create CONTRIBUTING.md with license requirements
- [ ] 1.6 Initialize git repository (if not already done)
- [ ] 1.7 Create initial commit with fork and rebrand

## 2. Module Scaffolding (`loomworks_addons/loomworks_core/`)
- [ ] 2.1 Create `loomworks_addons/loomworks_core/` directory
- [ ] 2.2 Create `__init__.py` with models import
- [ ] 2.3 Create `__manifest__.py` with complete metadata and LGPL-3 license
- [ ] 2.4 Create `models/__init__.py`
- [ ] 2.5 Create `models/res_company.py` (empty extension for now)
- [ ] 2.6 Create `security/ir.model.access.csv` (minimal access rules)

## 3. Logo Assets (Module Level)
- [ ] 3.1 Create `static/src/img/` directory
- [ ] 3.2 Copy `loomworks_logo.png` from assets/
- [ ] 3.3 Copy `loomworks_logo_white.png` from assets/
- [ ] 3.4 Copy `loomworks_icon.png` from assets/ (256x256 if not created yet)
- [ ] 3.5 Copy `loomworks_favicon.ico` from assets/
- [ ] 3.6 Copy `loomworks_favicon.png` from assets/
- [ ] 3.7 Create `static/description/` directory
- [ ] 3.8 Create `static/description/icon.png` (128x128px module icon)
- [ ] 3.9 Create `static/description/index.html` (module description)

## 4. SCSS Theme Implementation
- [ ] 4.1 Create `static/src/scss/` directory
- [ ] 4.2 Create `primary_variables.scss` with Loomworks color palette
- [ ] 4.3 Create `loomworks_backend.scss` with custom styles
- [ ] 4.4 Create `loomworks_login.scss` for login page styling
- [ ] 4.5 Update `__manifest__.py` assets section

## 5. Template Overrides (Runtime)
- [ ] 5.1 Create `views/` directory
- [ ] 5.2 Create `views/webclient_templates.xml` with favicon and login overrides
- [ ] 5.3 Create `static/src/xml/` directory
- [ ] 5.4 Create `static/src/xml/webclient_templates.xml` with Owl NavBar override
- [ ] 5.5 Create `views/res_company_views.xml` (company form customization)
- [ ] 5.6 Update `__manifest__.py` data section

## 6. Default Data
- [ ] 6.1 Create `data/` directory
- [ ] 6.2 Create `data/res_company_data.xml` with default Loomworks company branding
- [ ] 6.3 Update `__manifest__.py` data section

## 7. Testing
- [ ] 7.1 Create `tests/__init__.py`
- [ ] 7.2 Create `tests/test_branding.py` with installation test
- [ ] 7.3 Manual test: Run rebrand verification script
- [ ] 7.4 Manual test: Fresh installation with rebranded Odoo + module
- [ ] 7.5 Manual test: Login page shows Loomworks branding
- [ ] 7.6 Manual test: Navbar shows Loomworks logo
- [ ] 7.7 Manual test: Browser tab shows Loomworks favicon and title
- [ ] 7.8 Manual test: Color palette applied to buttons and links
- [ ] 7.9 Manual test: Email templates show Loomworks branding
- [ ] 7.10 Manual test: Database manager page shows Loomworks branding
- [ ] 7.11 Manual test: About dialog includes Odoo attribution
- [ ] 7.12 Manual test: No "Odoo" strings visible in main UI flows

## 8. Documentation
- [ ] 8.1 Add Loomworks copyright headers to all new Python files
- [ ] 8.2 Add Loomworks copyright headers to all new XML files
- [ ] 8.3 Update module description in `__manifest__.py`
- [ ] 8.4 Create `docs/installation.md` with installation procedure
- [ ] 8.5 Create `docs/branding.md` documenting rebrand process
- [ ] 8.6 Create `docs/upstream-sync.md` documenting how to sync with Odoo updates

## 9. Validation
- [ ] 9.1 Run Odoo linter on loomworks_core module
- [ ] 9.2 Verify no Enterprise module dependencies
- [ ] 9.3 Confirm LGPL headers present in all new files
- [ ] 9.4 Confirm Odoo S.A. attribution preserved in modified files
- [ ] 9.5 Test module install/uninstall cycle
- [ ] 9.6 Verify asset bundling works (no console errors)
- [ ] 9.7 Run `python scripts/rebrand.py --verify` to check for missed branding
- [ ] 9.8 grep codebase for remaining "odoo.com" URLs (should be 0 in UI paths)
- [ ] 9.9 grep codebase for remaining "Powered by Odoo" (should be 0)
- [ ] 9.10 Verify all logo files are Loomworks assets

## 10. Git Commit Structure
- [ ] 10.1 Commit 1: "Fork Odoo Community v18" (initial clone)
- [ ] 10.2 Commit 2: "Add Loomworks logo assets"
- [ ] 10.3 Commit 3: "Add rebrand script"
- [ ] 10.4 Commit 4: "Apply complete branding replacement"
- [ ] 10.5 Commit 5: "Create loomworks_core module"
- [ ] 10.6 Commit 6: "Add documentation and tests"
- [ ] 10.7 Tag: `v18.0.1.0.0` first Loomworks release
