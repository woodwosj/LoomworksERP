# Tasks: Phase 1 Foundation and Branding

## 1. Repository Setup
- [ ] 1.1 Fork Odoo Community v18 to `/home/loomworks/Desktop/LoomworksERP/odoo`
- [ ] 1.2 Create `loomworks_addons/` directory structure
- [ ] 1.3 Add LICENSE file (LGPL v3 full text) to repository root
- [ ] 1.4 Create `.gitignore` for Python/Odoo project
- [ ] 1.5 Create initial README.md with project overview and attribution

## 2. Module Scaffolding
- [ ] 2.1 Create `loomworks_addons/loomworks_core/` directory
- [ ] 2.2 Create `__init__.py` with models import
- [ ] 2.3 Create `__manifest__.py` with complete metadata
- [ ] 2.4 Create `models/__init__.py`
- [ ] 2.5 Create `models/res_company.py` (empty extension for now)
- [ ] 2.6 Create `security/ir.model.access.csv` (minimal access rules)

## 3. Logo Assets
- [ ] 3.1 Create `static/src/img/` directory
- [ ] 3.2 Add `loomworks_logo.png` (200x50px, horizontal logo)
- [ ] 3.3 Add `loomworks_logo_white.png` (200x50px, white variant)
- [ ] 3.4 Add `loomworks_icon.png` (256x256px, square icon)
- [ ] 3.5 Add `loomworks_favicon.ico` (32x32 and 16x16px)
- [ ] 3.6 Add `loomworks_favicon.png` (192x192px)
- [ ] 3.7 Create `static/description/` directory
- [ ] 3.8 Add `static/description/icon.png` (128x128px module icon)
- [ ] 3.9 Add `static/description/index.html` (module description)

## 4. SCSS Theme Implementation
- [ ] 4.1 Create `static/src/scss/` directory
- [ ] 4.2 Create `primary_variables.scss` with color palette
- [ ] 4.3 Create `loomworks_backend.scss` with custom styles
- [ ] 4.4 Create `loomworks_login.scss` for login page styling
- [ ] 4.5 Update `__manifest__.py` assets section

## 5. Template Overrides
- [ ] 5.1 Create `views/` directory
- [ ] 5.2 Create `views/webclient_templates.xml` with favicon and login overrides
- [ ] 5.3 Create `static/src/xml/` directory
- [ ] 5.4 Create `static/src/xml/webclient_templates.xml` with Owl NavBar override
- [ ] 5.5 Create `views/res_company_views.xml` (company form customization)
- [ ] 5.6 Update `__manifest__.py` data section

## 6. Default Data
- [ ] 6.1 Create `data/` directory
- [ ] 6.2 Create `data/res_company_data.xml` with default company branding
- [ ] 6.3 Update `__manifest__.py` data section

## 7. Testing
- [ ] 7.1 Create `tests/__init__.py`
- [ ] 7.2 Create `tests/test_branding.py` with installation test
- [ ] 7.3 Manual test: Fresh Odoo installation with module
- [ ] 7.4 Manual test: Login page shows Loomworks branding
- [ ] 7.5 Manual test: Navbar shows Loomworks logo
- [ ] 7.6 Manual test: Browser tab shows Loomworks favicon
- [ ] 7.7 Manual test: Color palette applied to buttons and links

## 8. Documentation
- [ ] 8.1 Add copyright headers to all Python files
- [ ] 8.2 Add copyright headers to all XML files
- [ ] 8.3 Update module description in `__manifest__.py`
- [ ] 8.4 Document installation procedure in docs/

## 9. Validation
- [ ] 9.1 Run Odoo linter on module (`pylint --load-plugins=pylint_odoo`)
- [ ] 9.2 Verify no Enterprise module dependencies
- [ ] 9.3 Confirm LGPL headers present in all files
- [ ] 9.4 Test module install/uninstall cycle
- [ ] 9.5 Verify asset bundling works (no console errors)
