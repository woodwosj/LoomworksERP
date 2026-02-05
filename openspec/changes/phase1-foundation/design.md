# Design: Phase 1 Foundation and Branding

## Context

Loomworks ERP is a **complete fork** of Odoo Community v18 licensed under LGPL v3. This phase establishes:
- Full repository fork with complete branding removal
- Automated rebranding infrastructure for ongoing maintenance
- `loomworks_core` module for runtime branding overrides
- LGPL v3 compliance with proper attribution

### Stakeholders
- End users (see Loomworks branding throughout UI)
- Developers (clean module structure to build upon)
- Legal (LGPL v3 compliance with Odoo S.A. attribution)
- DevOps (automated rebrand tooling for updates)

## Goals / Non-Goals

### Goals
- Fork Odoo Community v18 as a full copy (not submodule) into `/odoo/`
- Perform complete branding scrub of all Odoo references
- Create automated rebrand script for future Odoo updates
- Create reusable `loomworks_core` module as foundation for all other modules
- Establish Loomworks visual identity (colors, logos, typography)
- Maintain LGPL v3 compliance with proper Odoo S.A. attribution
- Document patterns for future module development

### Non-Goals
- Custom functionality (handled in later phases)
- Multi-tenant configuration (Phase 5)
- AI integration (Phase 2)
- Website/e-commerce theming (separate module if needed)
- Odoo Enterprise features (must be independently developed)

### Phase 2 Dependencies

> **Important**: The navbar design must accommodate the **Contextual AI Navbar** feature from Phase 2. When implementing navbar branding overrides, ensure the systray area has sufficient space for the AI dropdown component that will be added in Phase 2.7.
>
> See: `/openspec/FEATURE_CONTEXTUAL_AI_NAVBAR.md` for full specification.
>
> Key considerations:
> - Reserve systray space for AI button with badge indicator
> - Ensure navbar colors work with AI dropdown styling
> - Navbar logo positioning should not conflict with AI dropdown width (320-420px)

## Technical Decisions

### Decision 0: Fork Strategy (CRITICAL - Do First)

**Approach:** Full repository copy, NOT a git submodule.

**Rationale:**
- Submodules create complexity with tracking modifications
- Full copy allows direct file modifications for branding
- Enables clear separation of upstream vs. our changes
- Simplifies CI/CD and deployment

**Fork Source:**
```bash
# Clone Odoo Community v18
git clone --branch 18.0 --depth 1 https://github.com/odoo/odoo.git odoo

# Remove .git to make it a plain directory (not submodule)
rm -rf odoo/.git

# Initialize as part of our repository
git add odoo/
```

**Directory Structure After Fork:**
```
LoomworksERP/
├── odoo/                           # FORKED Odoo core (modified)
│   ├── odoo/                       # Core framework
│   │   ├── addons/
│   │   │   └── base/               # Base addon (in core)
│   │   ├── release.py              # Version info (MODIFY)
│   │   └── ...
│   └── addons/                     # Community addons (modified branding)
│       ├── web/                    # Web client (HEAVY MODIFICATION)
│       ├── mail/                   # Email templates (MODIFY)
│       ├── website/                # Website addon (MODIFY)
│       └── ...
├── loomworks_addons/               # Our custom modules (NEW)
│   └── loomworks_core/             # Branding module
├── scripts/
│   └── rebrand.py                  # Automated rebranding script
├── docs/
├── infrastructure/
├── LICENSE                         # LGPL v3
└── README.md
```

**Upstream Update Strategy:**
1. Create `upstream-18.0` branch tracking original Odoo
2. Periodically fetch upstream changes
3. Run rebrand script on new files
4. Merge into main with conflict resolution
5. Re-test branding completeness

### Decision 0.1: Complete Branding Scrub Checklist

Based on research of Odoo v18 repository structure, the following files contain branding that MUST be modified:

#### Core Framework (`odoo/odoo/`)

| File | Branding Elements | Action |
|------|-------------------|--------|
| `release.py` | Product name "Odoo", description "Odoo Server", author "OpenERP S.A.", URL "odoo.com" | Replace with Loomworks |
| `service/server.py` | Log messages with "Odoo" | Replace strings |
| `http.py` | Error pages mentioning Odoo | Replace strings |
| `cli/command.py` | CLI help text | Replace strings |

#### Web Addon (`odoo/addons/web/`)

**Static Images (`static/img/`)** - Replace entirely:
| File | Purpose | Loomworks Replacement |
|------|---------|----------------------|
| `favicon.ico` | Browser tab icon | `loomworks_favicon.ico` |
| `logo.png` | Primary logo | `loomworks_logo.png` |
| `logo2.png` | Secondary logo | `loomworks_logo_alt.png` |
| `logo_inverse_white_206px.png` | White logo | `loomworks_logo_white.png` |
| `odoo-icon-192x192.png` | PWA icon 192px | `loomworks_icon_192.png` |
| `odoo-icon-512x512.png` | PWA icon 512px | `loomworks_icon_512.png` |
| `odoo-icon-ios.png` | iOS icon | `loomworks_icon_ios.png` |
| `odoo-icon.svg` | SVG icon | `loomworks_icon.svg` |
| `odoo_logo.svg` | SVG logo | `loomworks_logo.svg` |
| `odoo_logo_dark.svg` | Dark mode logo | `loomworks_logo_dark.svg` |
| `odoo_logo_tiny.png` | Tiny logo (62x20) | `loomworks_logo_tiny.png` |
| `nologo.png` | Placeholder | Keep or replace |
| `enterprise_upgrade.jpg` | Enterprise upsell | REMOVE (delete file) |

**Views (`views/`):**
| File | Branding Elements |
|------|-------------------|
| `webclient_templates.xml` | Page titles "Odoo", favicon paths, logo paths, "Powered by Odoo" links, odoo.com URLs, theme color `#71639e` |

**SCSS (`static/src/scss/`):**
| File | Branding Elements |
|------|-------------------|
| `primary_variables.scss` | `$o-brand-odoo` color variable |
| Various component SCSS | References to brand colors |

**JavaScript (`static/src/`):**
| Pattern | Files | Action |
|---------|-------|--------|
| `odoo.com` URLs | Multiple JS files | Replace with loomworks.app |
| "Odoo" string literals | user_menu, navbar | Replace with "Loomworks" |
| Enterprise upgrade prompts | Multiple locations | Remove or replace |

#### Mail Addon (`odoo/addons/mail/`)

| File | Branding Elements |
|------|-------------------|
| `data/mail_templates_email_layouts.xml` | Email footer branding, "Powered by Odoo" |
| `data/mail_templates_chatter.xml` | Notification templates |
| `static/src/` | Discuss branding elements |

#### Base Addon (`odoo/odoo/addons/base/`)

| File | Branding Elements |
|------|-------------------|
| `data/res_company_data.xml` | Default company name/data |
| `data/res_partner_data.xml` | Default partner data |
| Various Python files | Docstrings mentioning Odoo |

#### Website Addon (`odoo/addons/website/`)

| File | Branding Elements |
|------|-------------------|
| `static/` | Website builder assets |
| `views/` | Public website templates |
| `data/` | Default website content |

#### Other Addons with Branding

| Addon | Files | Elements |
|-------|-------|----------|
| `account/static/src/img/` | `Odoo_logo_O.svg` | Odoo logo in accounting |
| `portal/` | Templates | "Powered by Odoo" in portal |
| `im_livechat/` | Templates | Live chat branding |

### Decision 0.2: LGPL v3 Attribution Requirements

**Research Sources:**
- [GNU LGPL v3 Full Text](https://www.gnu.org/licenses/lgpl-3.0.en.html)
- [FOSSA LGPL Guide](https://fossa.com/blog/open-source-software-licenses-101-lgpl-license/)
- [TLDRLegal LGPL Summary](https://www.tldrlegal.com/license/gnu-lesser-general-public-license-v3-lgpl-3)

**MUST Retain:**
1. **Original Copyright Notices** - Cannot remove Odoo S.A. copyright from modified files
2. **License References** - Must include LGPL v3 license text
3. **Source Availability** - Must provide source code or offer to provide it
4. **Modification Notices** - Must clearly indicate files that were modified

**CAN Change:**
1. **Product Name** - "Odoo" -> "Loomworks ERP" in UI
2. **Logos and Visual Assets** - Full replacement allowed
3. **URLs** - odoo.com -> loomworks.app
4. **Default Data** - Company names, email domains

**Required Attribution Format:**

In modified source files:
```python
# -*- coding: utf-8 -*-
# Loomworks ERP - An AI-first ERP system
# Copyright (C) 2024 Loomworks
#
# This program is based on Odoo Community Edition
# Copyright (C) 2004-2024 Odoo S.A. <https://www.odoo.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

In README.md:
```markdown
## Attribution

Loomworks ERP is based on [Odoo Community Edition](https://github.com/odoo/odoo),
originally developed by Odoo S.A. and released under the LGPL v3 license.

This fork includes modifications for branding and AI-first functionality.
All modifications are also released under LGPL v3.
```

In About Dialog (UI):
```
Loomworks ERP v18.0
Based on Odoo Community Edition
Original software (C) Odoo S.A.
Licensed under LGPL v3
```

### Decision 0.3: Automated Rebrand Script Design

**Script Location:** `/scripts/rebrand.py`

**Functionality:**
```python
#!/usr/bin/env python3
"""
Loomworks Rebrand Script

Automates the replacement of Odoo branding with Loomworks branding.
Designed to be run after fetching upstream Odoo updates.

Usage:
    python scripts/rebrand.py --check      # Report branding found
    python scripts/rebrand.py --apply      # Apply replacements
    python scripts/rebrand.py --report     # Generate detailed report
"""

# Configuration
BRAND_REPLACEMENTS = {
    # Text replacements (case-sensitive patterns)
    'strings': {
        'Odoo': 'Loomworks',
        'odoo': 'loomworks',
        'ODOO': 'LOOMWORKS',
        'Odoo S.A.': 'Loomworks (based on Odoo by Odoo S.A.)',
        'info@odoo.com': 'support@loomworks.app',
        'www.odoo.com': 'www.loomworks.app',
        'odoo.com': 'loomworks.app',
        'https://www.odoo.com': 'https://www.loomworks.app',
    },

    # File replacements (copy new file over old)
    'files': {
        'addons/web/static/img/favicon.ico': 'assets/loomworks_favicon.ico',
        'addons/web/static/img/logo.png': 'assets/loomworks_logo.png',
        # ... all logo files
    },

    # Patterns to remove entirely
    'remove_patterns': [
        r'enterprise_upgrade',  # Enterprise upsell references
        r'utm_source=db&utm_medium=',  # Tracking parameters
    ],

    # Files to skip (preserve original copyright)
    'skip_files': [
        'LICENSE',
        'COPYRIGHT',
        '*.po',  # Translation files
        '*.pot',
    ],

    # Directories to skip
    'skip_dirs': [
        '.git',
        'node_modules',
        '__pycache__',
    ],
}

# File type handlers
FILE_HANDLERS = {
    '.py': 'python',      # Add/update copyright header
    '.js': 'javascript',  # String replacements
    '.xml': 'xml',        # Template replacements
    '.scss': 'scss',      # Variable replacements
    '.css': 'css',        # String replacements
    '.html': 'html',      # Template replacements
    '.rst': 'text',       # Documentation
    '.md': 'text',        # Documentation
}
```

**Script Features:**
1. **Dry-run mode** - Report what would change without modifying
2. **Incremental mode** - Only process files changed since last run
3. **Verification mode** - Check for missed branding after rebrand
4. **Report generation** - Output CSV/JSON of all changes made
5. **Rollback support** - Keep backup of original files

**Branding Detection Patterns:**
```python
DETECTION_PATTERNS = [
    # URLs
    r'https?://[^\s]*odoo\.com[^\s]*',
    r'mailto:[^\s]*@odoo\.com',

    # Product names
    r'\bOdoo\b',
    r'\bodoo\b',
    r'\bODOO\b',

    # File references
    r'odoo[_-]logo',
    r'odoo[_-]icon',
    r'favicon\.ico',  # Check if it's the Odoo favicon

    # CSS/SCSS variables
    r'\$o-brand-odoo',

    # Meta tags
    r'content=["\']Odoo',
    r'name=["\']odoo',
]
```

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
    <!--
    NOTE: Phase 2.7 will add the AINavbarDropdown component to the systray area.
    Ensure the systray has sufficient space and that these branding overrides
    do not conflict with the AI dropdown (320-420px width).
    See: /openspec/FEATURE_CONTEXTUAL_AI_NAVBAR.md
    -->
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

### Risk 1: Fork Maintenance Burden
**Risk:** Keeping fork synchronized with upstream Odoo updates is labor-intensive
**Mitigation:**
- Automated rebrand script reduces manual work
- Track upstream 18.0 branch separately
- Quarterly sync schedule (security patches immediate)
- Document merge conflict resolution procedures
**Trade-off:** Full fork gives complete control but requires ongoing maintenance

### Risk 2: Incomplete Branding Removal
**Risk:** Odoo branding may remain in obscure locations
**Mitigation:**
- Comprehensive file-by-file audit checklist
- Automated detection script with regex patterns
- Manual QA testing of all UI paths
- Community/user bug reports for missed items
**Detection Patterns:** Search for `odoo`, `Odoo`, `ODOO`, `odoo.com`, `o-brand`

### Risk 3: LGPL Attribution Violations
**Risk:** Improper removal of required copyright notices
**Mitigation:**
- Legal review of LGPL v3 requirements
- Preserve all copyright headers (add Loomworks, don't remove Odoo)
- Maintain COPYING/LICENSE files
- About dialog includes Odoo attribution
**Reference:** [GNU LGPL v3](https://www.gnu.org/licenses/lgpl-3.0.html)

### Risk 4: Asset Bundling Conflicts
**Risk:** SCSS prepend order could conflict with other modules
**Mitigation:**
- Use `('prepend', ...)` only for primary_variables
- Test with common Odoo modules installed
- Document asset loading order

### Risk 5: Template Inheritance Fragility
**Risk:** Odoo core template changes could break overrides
**Mitigation:**
- Direct file modification in fork (not just inheritance)
- XPath overrides in loomworks_core as backup
- Include template tests that verify selectors exist

### Risk 6: Logo Display Issues
**Risk:** Logos may display incorrectly at various sizes
**Mitigation:**
- Provide multiple resolution variants (16px to 512px)
- Use SVG for scalability where supported
- Test across browsers and devices

### Risk 7: Enterprise Code Contamination
**Risk:** Accidental inclusion of Enterprise code violates license
**Mitigation:**
- Never reference Enterprise repository in code
- Code review checklist includes license check
- Automated scanning for Enterprise module names
- grep for `odoo/enterprise` references

### Risk 8: Translation File Complexity
**Risk:** 100+ .po/.pot files contain Odoo branding strings
**Mitigation:**
- Phase 1 focuses on English only
- Translation rebrand deferred to later phase
- Mark .po files as "skip" in rebrand script initially

## Migration Plan

### Phase 1a: Fork Creation (Day 1-2)

```bash
# 1. Clone Odoo Community v18
git clone --branch 18.0 --depth 1 https://github.com/odoo/odoo.git odoo
rm -rf odoo/.git

# 2. Create directory structure
mkdir -p loomworks_addons/loomworks_core
mkdir -p scripts
mkdir -p assets
mkdir -p docs

# 3. Copy LICENSE file
cp odoo/LICENSE ./LICENSE

# 4. Initialize git
git init
git add .
git commit -m "[init] Fork Odoo Community v18 for Loomworks ERP"
```

### Phase 1b: Branding Asset Preparation (Day 2-3)

Create Loomworks logo assets in `/assets/`:
- `loomworks_favicon.ico` (16x16, 32x32 multi-resolution)
- `loomworks_favicon.png` (192x192)
- `loomworks_logo.png` (200x50)
- `loomworks_logo_white.png` (200x50)
- `loomworks_logo.svg` (vector)
- `loomworks_logo_dark.svg` (for dark mode)
- `loomworks_logo_tiny.png` (62x20)
- `loomworks_icon.svg` (square)
- `loomworks_icon_192.png` (192x192)
- `loomworks_icon_512.png` (512x512)
- `loomworks_icon_ios.png` (iOS format)

### Phase 1c: Automated Rebrand (Day 3-5)

```bash
# 1. Run rebrand script in check mode
python scripts/rebrand.py --check > rebrand_report.txt

# 2. Review report, adjust patterns if needed

# 3. Run rebrand script in apply mode
python scripts/rebrand.py --apply

# 4. Verify no remaining Odoo branding
python scripts/rebrand.py --verify

# 5. Commit changes
git add -A
git commit -m "[rebrand] Complete Odoo to Loomworks branding replacement"
```

### Phase 1d: Module Development (Day 5-7)

1. Create `loomworks_addons/loomworks_core/` module
2. Add runtime branding overrides (for dynamic content)
3. Test module installation
4. Verify branding in all major views

### Installation Steps (Fresh Install)

```bash
# 1. Clone Loomworks ERP repository
git clone https://github.com/loomworks/LoomworksERP.git
cd LoomworksERP

# 2. Install Python dependencies
pip install -r odoo/requirements.txt

# 3. Create PostgreSQL database
createdb loomworks

# 4. Initialize database with Loomworks modules
./odoo/odoo-bin -d loomworks \
    --addons-path=odoo/addons,odoo/odoo/addons,loomworks_addons \
    -i base,web,loomworks_core \
    --stop-after-init

# 5. Start server
./odoo/odoo-bin -d loomworks \
    --addons-path=odoo/addons,odoo/odoo/addons,loomworks_addons
```

### Upgrade Path (Upstream Sync)

```bash
# 1. Fetch upstream changes
git remote add upstream https://github.com/odoo/odoo.git
git fetch upstream 18.0

# 2. Create diff of upstream changes
git diff upstream/18.0 -- odoo/ > upstream_changes.patch

# 3. Apply upstream changes carefully
# (Manual review required for conflicts)

# 4. Re-run rebrand script
python scripts/rebrand.py --apply

# 5. Test thoroughly
python -m pytest loomworks_addons/*/tests/

# 6. Commit
git add -A
git commit -m "[upstream] Sync with Odoo 18.0 (date)"
```

### Rollback

Full rollback requires re-cloning from pre-rebrand state or Odoo upstream.
Module-level rollback: Uninstall `loomworks_core` restores default Odoo behavior for runtime overrides only.

## Open Questions

1. **Logo Design:** Final logo assets need to be created. Current proposal uses placeholder specifications. Who will create the Loomworks logo?

2. **Dark Mode:** Should we provide dark mode color variants? (Odoo 18 supports dark mode) - Recommendation: Yes, include `loomworks_logo_dark.svg`

3. **Email Templates:** Extent of email branding customization needed? - Recommendation: Full rebrand of `mail_templates_email_layouts.xml`

4. **Website Theme:** Separate `loomworks_website` module or include basic website branding here? - Recommendation: Basic rebrand in fork, advanced theming in separate module

5. **Translation Files:** 100+ .po files contain "Odoo" strings. Should we rebrand translations in Phase 1? - Recommendation: Defer to Phase 1.1, focus on English first

6. **Upstream Sync Frequency:** How often should we sync with Odoo 18.0 upstream? - Recommendation: Monthly for features, immediate for security patches

7. **Enterprise Upgrade Prompts:** Should we completely remove or replace with Loomworks hosting upsell? - Recommendation: Remove in Phase 1, add Loomworks-specific prompts in Phase 5

8. **Database Manager Branding:** The `/web/database/manager` page has Odoo branding. Include in scope? - Recommendation: Yes, include in Phase 1

9. **PWA Manifest:** The `manifest.webmanifest` contains Odoo branding. Include? - Recommendation: Yes, critical for mobile experience

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

## Complete Branding File Inventory

### Files to REPLACE (copy Loomworks asset over Odoo asset)

```
odoo/addons/web/static/img/
├── favicon.ico                    -> loomworks_favicon.ico
├── logo.png                       -> loomworks_logo.png
├── logo2.png                      -> loomworks_logo_alt.png
├── logo_inverse_white_206px.png   -> loomworks_logo_white.png
├── odoo-icon-192x192.png          -> loomworks_icon_192.png
├── odoo-icon-512x512.png          -> loomworks_icon_512.png
├── odoo-icon-ios.png              -> loomworks_icon_ios.png
├── odoo-icon.svg                  -> loomworks_icon.svg
├── odoo_logo.svg                  -> loomworks_logo.svg
├── odoo_logo_dark.svg             -> loomworks_logo_dark.svg
└── odoo_logo_tiny.png             -> loomworks_logo_tiny.png
```

### Files to DELETE

```
odoo/addons/web/static/img/
└── enterprise_upgrade.jpg         # Enterprise upsell image

odoo/addons/account/static/src/img/
└── Odoo_logo_O.svg                # Odoo logo in accounting (or replace)
```

### Files to MODIFY (string replacement)

**High Priority (visible to all users):**
```
odoo/odoo/release.py                           # Product name, author, URL
odoo/addons/web/views/webclient_templates.xml  # Page titles, favicon, logos, powered-by
odoo/addons/mail/data/mail_templates_email_layouts.xml  # Email footer
odoo/addons/portal/data/mail_templates.xml     # Portal email templates
```

**Medium Priority (visible in specific contexts):**
```
odoo/addons/web/static/src/webclient/          # Multiple JS files with "Odoo" strings
odoo/addons/web/static/src/core/               # Core JS components
odoo/addons/website/views/                     # Website templates
odoo/odoo/addons/base/data/res_company_data.xml  # Default company
```

**Lower Priority (developer-facing):**
```
odoo/odoo/http.py                              # Error pages
odoo/odoo/service/server.py                    # Log messages
odoo/README.md                                 # Repository readme
odoo/doc/                                      # Documentation
```

### PWA Manifest Location

```
odoo/addons/web/static/src/public/manifest.webmanifest.mako
```
Contains: app name, short_name, icons array - all need rebranding.

## Research References

### Odoo Repository Structure
- [GitHub: odoo/odoo](https://github.com/odoo/odoo)
- [Odoo 18 Developer Documentation](https://www.odoo.com/documentation/18.0/developer.html)
- [Odoo 18 Assets Documentation](https://www.odoo.com/documentation/18.0/developer/reference/frontend/assets.html)
- [Odoo 18 SCSS Inheritance](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/scss_inheritance.html)

### LGPL v3 Compliance
- [GNU LGPL v3 Full Text](https://www.gnu.org/licenses/lgpl-3.0.en.html)
- [FOSSA LGPL Guide](https://fossa.com/blog/open-source-software-licenses-101-lgpl-license/)
- [TLDRLegal LGPL v3](https://www.tldrlegal.com/license/gnu-lesser-general-public-license-v3-lgpl-3)

### Odoo Fork Examples
- [Flectra ERP](https://github.com/flectra-hq/flectra) - Odoo fork (note: had legal issues)
- [OCA OCB](https://github.com/OCA/OCB) - Odoo Community Backports
- [Debrand Odoo Gist](https://gist.github.com/lambone/2d7a0418b810a4cc8694) - Reference for branding locations

### OCA Debranding Modules (Reference Only)
- [OCA web_favicon](https://github.com/OCA/web/tree/18.0/web_favicon) - Favicon customization approach
- [OCA portal_odoo_debranding](https://pypi.org/project/odoo-addon-portal-odoo-debranding/) - Portal debranding
