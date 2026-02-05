# Change: Phase 1 Foundation and Branding

## Why

Loomworks ERP requires a distinct brand identity separate from Odoo to establish market presence and avoid user confusion. The foundation phase establishes the custom module structure, replaces all Odoo branding with Loomworks assets, and configures a cohesive color scheme. This is the essential first step before any feature development can begin.

## What Changes

- **NEW** `loomworks_core` module with complete manifest and branding assets
- **NEW** Custom SCSS theme with Loomworks color palette for backend and frontend
- **NEW** Logo assets (favicon, navbar logo, login page logo, company logo)
- **NEW** QWeb template overrides for webclient branding
- **NEW** Default company data with Loomworks information
- **MODIFIED** Asset bundles to include custom SCSS variables

## Impact

- Affected specs: `loomworks-core` (new capability)
- Affected code:
  - `/loomworks_addons/loomworks_core/` (new module)
  - Asset bundles: `web._assets_primary_variables`, `web.assets_backend`, `web.assets_frontend`
- Dependencies: Requires Odoo Community v18 base installation

## Scope

This proposal covers **Phase 1 (Weeks 1-4)** of the implementation plan:
1. Fork Odoo Community v18 repository
2. Create `loomworks_core` branding module
3. Replace logos, favicon, and brand colors
4. Configure default company settings
5. Test branding across all major views

## Success Criteria

1. All Odoo logos replaced with Loomworks logos
2. Custom color palette applied consistently
3. Module installs without errors on fresh Odoo v18
4. Branding visible on login page, navbar, and system emails
5. LGPL v3 compliance maintained with proper attribution
