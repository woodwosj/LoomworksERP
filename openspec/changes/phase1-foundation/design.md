# Design: Phase 1 Foundation and Branding

## Context

Loomworks ERP is a fork of Odoo Community v18 licensed under LGPL v3. The branding module must:
- Replace all visible Odoo branding with Loomworks identity
- Maintain full LGPL v3 compliance
- Work with Odoo's asset bundling system
- Not modify core Odoo files (use inheritance/override patterns)

### Stakeholders
- End users (see Loomworks branding throughout UI)
- Developers (clean module structure to build upon)
- Legal (LGPL v3 compliance)

## Goals / Non-Goals

### Goals
- Create reusable `loomworks_core` module as foundation for all other modules
- Establish Loomworks visual identity (colors, logos, typography)
- Provide clean separation between Odoo core and Loomworks customizations
- Document patterns for future module development

### Non-Goals
- Custom functionality (handled in later phases)
- Multi-tenant configuration (Phase 5)
- AI integration (Phase 2)
- Website/e-commerce theming (separate module if needed)

## Technical Decisions

### Decision 1: Module Structure

Use standard Odoo module structure with dedicated directories for assets.

**Directory Structure:**
```
loomworks_addons/
└── loomworks_core/
    ├── __init__.py
    ├── __manifest__.py
    ├── data/
    │   └── res_company_data.xml          # Default company branding
    ├── models/
    │   ├── __init__.py
    │   └── res_company.py                # Company model extensions
    ├── security/
    │   └── ir.model.access.csv
    ├── static/
    │   ├── description/
    │   │   ├── icon.png                  # Module icon (128x128)
    │   │   └── index.html                # Module description
    │   └── src/
    │       ├── img/
    │       │   ├── loomworks_logo.png         # Main logo (horizontal)
    │       │   ├── loomworks_logo_white.png   # White variant for dark bg
    │       │   ├── loomworks_icon.png         # Square icon (256x256)
    │       │   ├── loomworks_favicon.ico      # Favicon (32x32, 16x16)
    │       │   └── loomworks_favicon.png      # PNG favicon (192x192)
    │       ├── scss/
    │       │   ├── primary_variables.scss     # Color palette overrides
    │       │   ├── loomworks_backend.scss     # Backend custom styles
    │       │   └── loomworks_login.scss       # Login page styles
    │       └── xml/
    │           └── webclient_templates.xml    # QWeb template overrides
    ├── views/
    │   ├── webclient_templates.xml       # Login and layout overrides
    │   └── res_company_views.xml         # Company form customization
    └── tests/
        ├── __init__.py
        └── test_branding.py
```

**Rationale:** Follows Odoo coding guidelines. Separates concerns (data, views, static assets). Enables easy asset bundling via manifest.

### Decision 2: Manifest Configuration

**Complete `__manifest__.py`:**
```python
# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
# License: LGPL-3

{
    'name': 'Loomworks Core',
    'version': '18.0.1.0.0',
    'category': 'Hidden/Tools',
    'summary': 'Loomworks ERP Branding and Core Configuration',
    'description': """
Loomworks ERP Core Module
=========================

This module provides:
- Loomworks branding (logos, colors, favicon)
- Custom color palette for backend and frontend
- Default company configuration
- Base dependencies for all Loomworks modules

This is a fork of Odoo Community v18 (LGPL v3).
Original software: https://github.com/odoo/odoo
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',  # For email templates branding
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_company_data.xml',
        'views/webclient_templates.xml',
        'views/res_company_views.xml',
    ],
    'assets': {
        # Primary variables - loaded first, defines color palette
        'web._assets_primary_variables': [
            ('prepend', 'loomworks_core/static/src/scss/primary_variables.scss'),
        ],
        # Backend assets - custom styles for backend interface
        'web.assets_backend': [
            'loomworks_core/static/src/scss/loomworks_backend.scss',
            'loomworks_core/static/src/xml/webclient_templates.xml',
        ],
        # Frontend assets - for portal and website
        'web.assets_frontend': [
            'loomworks_core/static/src/scss/loomworks_backend.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 1,  # Load early
}
```

**Key manifest fields:**
| Field | Purpose |
|-------|---------|
| `version` | Semantic versioning: `18.0.MAJOR.MINOR.PATCH` |
| `category` | `Hidden/Tools` - not visible in Apps menu |
| `license` | Must be `LGPL-3` for compliance |
| `depends` | Base modules needed for branding |
| `assets` | SCSS/JS bundle declarations |
| `sequence` | Lower number = loaded earlier |

### Decision 3: Color Palette (SCSS Variables)

**Loomworks Brand Colors:**
```scss
// Primary Variables - primary_variables.scss

// ============================================
// LOOMWORKS COLOR PALETTE
// ============================================

// Primary brand color (deep blue - trust, professionalism)
$lw-primary: #1e3a5f;
$lw-primary-light: #2d5a8a;
$lw-primary-dark: #0f2840;

// Secondary/accent color (teal - innovation, growth)
$lw-secondary: #2dd4bf;
$lw-secondary-light: #5eead4;
$lw-secondary-dark: #14b8a6;

// Neutral palette
$lw-gray-50: #f8fafc;
$lw-gray-100: #f1f5f9;
$lw-gray-200: #e2e8f0;
$lw-gray-300: #cbd5e1;
$lw-gray-400: #94a3b8;
$lw-gray-500: #64748b;
$lw-gray-600: #475569;
$lw-gray-700: #334155;
$lw-gray-800: #1e293b;
$lw-gray-900: #0f172a;

// Semantic colors
$lw-success: #22c55e;
$lw-warning: #f59e0b;
$lw-danger: #ef4444;
$lw-info: #3b82f6;

// ============================================
// ODOO VARIABLE OVERRIDES
// ============================================

// Override Odoo's primary brand color
$o-brand-odoo: $lw-primary !default;
$o-brand-primary: $lw-primary !default;
$o-brand-secondary: $lw-secondary !default;

// Color palette for Website Builder compatibility
$o-color-palettes: map-merge($o-color-palettes,
    (
        'loomworks': (
            'o-color-1': $lw-primary,      // Primary
            'o-color-2': $lw-secondary,    // Secondary
            'o-color-3': $lw-gray-100,     // Light background
            'o-color-4': #ffffff,          // White
            'o-color-5': $lw-gray-900,     // Dark text
        ),
    )
);

// Set Loomworks as default palette
$o-selected-color-palettes-names: append($o-selected-color-palettes-names, 'loomworks');

// Navbar colors
$o-navbar-inverse-bg: $lw-primary !default;
$o-navbar-inverse-color: #ffffff !default;
$o-navbar-inverse-link-color: rgba(255, 255, 255, 0.85) !default;
$o-navbar-inverse-link-hover-color: #ffffff !default;

// Form and input styling
$o-form-lightsecondary: $lw-gray-100 !default;

// ============================================
// BOOTSTRAP VARIABLE OVERRIDES
// ============================================

$primary: $lw-primary !default;
$secondary: $lw-secondary !default;
$success: $lw-success !default;
$info: $lw-info !default;
$warning: $lw-warning !default;
$danger: $lw-danger !default;

$body-bg: $lw-gray-50 !default;
$body-color: $lw-gray-800 !default;

$link-color: $lw-primary !default;
$link-hover-color: $lw-primary-dark !default;
```

**Rationale:**
- Deep blue primary conveys trust/professionalism (enterprise software)
- Teal secondary provides modern, tech-forward accent
- Maintains WCAG AA contrast ratios
- Uses `!default` to allow further customization
- Prepend to `_assets_primary_variables` ensures early loading

### Decision 4: Logo Replacement Strategy

**Logo Files Required:**
| File | Size | Location | Usage |
|------|------|----------|-------|
| `loomworks_logo.png` | 200x50px | `static/src/img/` | Navbar, headers |
| `loomworks_logo_white.png` | 200x50px | `static/src/img/` | Dark backgrounds |
| `loomworks_icon.png` | 256x256px | `static/src/img/` | Square contexts |
| `loomworks_favicon.ico` | 32x32, 16x16px | `static/src/img/` | Browser favicon |
| `loomworks_favicon.png` | 192x192px | `static/src/img/` | PWA, mobile |
| `icon.png` | 128x128px | `static/description/` | Apps store icon |

**QWeb Template Overrides (`views/webclient_templates.xml`):**
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Override favicon -->
    <template id="loomworks_favicon" inherit_id="web.layout" name="Loomworks Favicon">
        <xpath expr="//link[@rel='shortcut icon']" position="replace">
            <link rel="shortcut icon" href="/loomworks_core/static/src/img/loomworks_favicon.ico" type="image/x-icon"/>
        </xpath>
        <xpath expr="//link[@rel='icon']" position="replace">
            <link rel="icon" href="/loomworks_core/static/src/img/loomworks_favicon.png" type="image/png"/>
        </xpath>
    </template>

    <!-- Override login page branding -->
    <template id="loomworks_login" inherit_id="web.login" name="Loomworks Login">
        <xpath expr="//div[hasclass('text-center')]//img" position="replace">
            <img src="/loomworks_core/static/src/img/loomworks_logo.png"
                 alt="Loomworks ERP"
                 style="max-height: 80px; width: auto;"/>
        </xpath>
    </template>

    <!-- Override page title -->
    <template id="loomworks_title" inherit_id="web.layout" name="Loomworks Page Title">
        <xpath expr="//title" position="replace">
            <title><t t-esc="title or 'Loomworks ERP'"/></title>
        </xpath>
    </template>
</odoo>
```

**Owl Component Override (`static/src/xml/webclient_templates.xml`):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">
    <!-- Override navbar logo -->
    <t t-inherit="web.NavBar" t-inherit-mode="extension">
        <xpath expr="//img[hasclass('o_menu_brand_icon')]" position="replace">
            <img class="o_menu_brand_icon"
                 src="/loomworks_core/static/src/img/loomworks_icon.png"
                 alt="Loomworks"
                 style="height: 30px; width: auto;"/>
        </xpath>
    </t>
</templates>
```

### Decision 5: LGPL v3 Compliance

**Required Actions:**
1. **LICENSE file** at repository root with full LGPL v3 text
2. **Copyright headers** in all source files:
   ```python
   # -*- coding: utf-8 -*-
   # Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
   #
   # This file is part of Loomworks ERP, a fork of Odoo Community.
   # Original software copyright: Odoo S.A.
   # Loomworks modifications copyright: Loomworks
   # License: LGPL-3
   ```
3. **Attribution** in README and about page acknowledging Odoo
4. **Source availability** - all modifications must be available under LGPL-3
5. **Mark modifications** - changed files must indicate they were modified

**LGPL v3 Key Requirements (per GNU.org):**
- Modifications to LGPL code must be released under LGPL
- Must provide source code or offer to provide it
- Must preserve copyright notices and license references
- Must mark modified files as changed
- Cannot impose additional restrictions

**References:**
- [LGPL v3 Full Text](https://www.gnu.org/licenses/lgpl-3.0.html)
- [FOSSA LGPL Guide](https://fossa.com/blog/open-source-software-licenses-101-lgpl-license/)

## Risks / Trade-offs

### Risk 1: Asset Bundling Conflicts
**Risk:** SCSS prepend order could conflict with other modules
**Mitigation:**
- Use `('prepend', ...)` only for primary_variables
- Test with common Odoo modules installed
- Document asset loading order

### Risk 2: Template Inheritance Fragility
**Risk:** Odoo core template changes could break overrides
**Mitigation:**
- Use specific XPath selectors
- Pin to Odoo v18.0 release branch
- Include template tests that verify selectors exist

### Risk 3: Logo Display Issues
**Risk:** Logos may display incorrectly at various sizes
**Mitigation:**
- Provide multiple resolution variants
- Use SVG where possible for scalability
- Test across browsers and devices

### Risk 4: LGPL Compliance Errors
**Risk:** Accidental inclusion of Enterprise code
**Mitigation:**
- Never reference `/home/loomworks/Desktop/OdooTestLauncher` in code
- Code review checklist includes license check
- Automated scanning for Enterprise module names

## Migration Plan

### Installation Steps (Fresh Install)
1. Clone Odoo Community v18
2. Add `loomworks_addons` to addons path
3. Update module list: `./odoo-bin -d dbname -u base --stop-after-init`
4. Install `loomworks_core`: `./odoo-bin -d dbname -i loomworks_core`

### Upgrade Path
Module follows Odoo's standard upgrade mechanism via `__manifest__.py` version.

### Rollback
1. Uninstall `loomworks_core` via Apps
2. Remove from addons path
3. Standard Odoo branding restored

## Open Questions

1. **Logo Design:** Final logo assets need to be created. Current proposal uses placeholder specifications.
2. **Dark Mode:** Should we provide dark mode color variants? (Odoo 18 supports dark mode)
3. **Email Templates:** Extent of email branding customization needed?
4. **Website Theme:** Separate `loomworks_website` module or include basic website branding here?

## Asset Bundle Reference

| Bundle | Purpose | When to Use |
|--------|---------|-------------|
| `web._assets_primary_variables` | SCSS variables | Color palette, spacing |
| `web._assets_secondary_variables` | Secondary SCSS vars | Component-specific vars |
| `web._assets_frontend_helpers` | Bootstrap overrides | Typography, forms |
| `web._assets_bootstrap` | Bootstrap core | Rarely override |
| `web.assets_backend` | Backend CSS/JS | Admin interface |
| `web.assets_frontend` | Frontend CSS/JS | Portal, website |

**Source:** [Odoo 18 SCSS Inheritance](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/scss_inheritance.html)
