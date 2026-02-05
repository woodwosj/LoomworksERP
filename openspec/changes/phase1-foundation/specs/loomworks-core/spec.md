# Capability: Loomworks Core Branding

## ADDED Requirements

### Requirement: Module Installation

The `loomworks_core` module SHALL be installable on a fresh Odoo Community v18 instance without errors.

#### Scenario: Fresh installation succeeds
- **WHEN** Odoo is started with `loomworks_addons` in the addons path
- **AND** the module list is updated
- **AND** `loomworks_core` is installed via the Apps menu
- **THEN** the installation completes without errors
- **AND** the module appears as installed in Apps

#### Scenario: Dependencies are satisfied
- **WHEN** `loomworks_core` is installed
- **THEN** the `base`, `web`, and `mail` modules are already installed or auto-installed
- **AND** no missing dependency errors occur

### Requirement: Logo Replacement

The system SHALL display Loomworks logos in place of Odoo logos throughout the user interface.

#### Scenario: Login page displays Loomworks logo
- **WHEN** a user navigates to the login page
- **THEN** the Loomworks logo is displayed above the login form
- **AND** the Odoo logo is not visible

#### Scenario: Navbar displays Loomworks icon
- **WHEN** a logged-in user views any backend page
- **THEN** the Loomworks icon is displayed in the top-left navbar area
- **AND** the icon links to the home/apps page

#### Scenario: Browser tab displays Loomworks favicon
- **WHEN** any page is loaded in the browser
- **THEN** the browser tab shows the Loomworks favicon
- **AND** the favicon is visible at both 16x16 and 32x32 sizes

### Requirement: Page Title Branding

The system SHALL display "Loomworks ERP" in page titles instead of "Odoo".

#### Scenario: Default page title
- **WHEN** a page without a specific title is loaded
- **THEN** the browser tab title shows "Loomworks ERP"

#### Scenario: Page-specific title
- **WHEN** a page with a specific title (e.g., "Sales Orders") is loaded
- **THEN** the browser tab title includes both the page title and "Loomworks ERP"

### Requirement: Custom Color Palette

The system SHALL apply the Loomworks color palette to the backend interface.

#### Scenario: Primary color applied
- **WHEN** a user views the backend interface
- **THEN** primary action buttons use the Loomworks primary color (#1e3a5f)
- **AND** links use the primary color
- **AND** the navbar background uses the primary color

#### Scenario: Secondary color applied
- **WHEN** a user views secondary actions or accents
- **THEN** secondary buttons and badges use the Loomworks secondary color (#2dd4bf)

#### Scenario: Consistent color application
- **WHEN** a user navigates between different Odoo apps (Sales, Inventory, etc.)
- **THEN** the color palette remains consistent across all apps

### Requirement: SCSS Variable System

The module SHALL provide SCSS variables that can be overridden by other modules.

#### Scenario: Primary variables bundle loaded
- **WHEN** the module is installed
- **THEN** `primary_variables.scss` is prepended to `web._assets_primary_variables`
- **AND** the Loomworks color palette variables are available to other SCSS files

#### Scenario: Variables use !default
- **WHEN** another module defines the same variable
- **THEN** the other module's value takes precedence
- **AND** the Loomworks default is only used if no override exists

### Requirement: LGPL v3 Compliance

The module SHALL comply with LGPL v3 licensing requirements.

#### Scenario: License file present
- **WHEN** the repository is examined
- **THEN** a LICENSE file containing the full LGPL v3 text is present at the root

#### Scenario: Copyright headers in Python files
- **WHEN** any Python file in `loomworks_core` is examined
- **THEN** it contains a copyright header referencing LGPL-3
- **AND** it attributes original Odoo code where applicable

#### Scenario: Copyright headers in XML files
- **WHEN** any XML file in `loomworks_core` is examined
- **THEN** it contains a copyright comment referencing LGPL-3

#### Scenario: Manifest declares license
- **WHEN** `__manifest__.py` is examined
- **THEN** the `license` field is set to `'LGPL-3'`

### Requirement: Asset Bundling Integration

The module SHALL integrate correctly with Odoo's asset bundling system.

#### Scenario: No JavaScript console errors
- **WHEN** the module is installed and any page is loaded
- **THEN** no JavaScript errors related to asset loading appear in the browser console

#### Scenario: SCSS compiles successfully
- **WHEN** the Odoo server starts with the module installed
- **THEN** no SCSS compilation errors are logged
- **AND** the compiled CSS is served correctly

#### Scenario: Assets cached appropriately
- **WHEN** a page is loaded multiple times
- **THEN** static assets are served with appropriate cache headers
- **AND** asset bundle versioning works correctly

### Requirement: Default Company Configuration

The module SHALL provide default Loomworks branding for the main company record.

#### Scenario: Company logo set on install
- **WHEN** `loomworks_core` is installed on a database with the default company
- **THEN** the company's logo field contains the Loomworks logo
- **AND** the company name can optionally be set to "Loomworks" (configurable)

#### Scenario: Report header branding
- **WHEN** a report (invoice, quotation, etc.) is generated
- **THEN** the report header displays the Loomworks company logo
- **AND** the report footer can display "Powered by Loomworks ERP"

### Requirement: Module Metadata

The module SHALL have complete and accurate metadata for the Odoo Apps interface.

#### Scenario: Module icon displayed
- **WHEN** the Apps list is viewed
- **THEN** `loomworks_core` displays a 128x128 icon
- **AND** the icon is visually consistent with Loomworks branding

#### Scenario: Module description available
- **WHEN** the module details are viewed in Apps
- **THEN** a description explaining the module purpose is displayed
- **AND** the description mentions LGPL-3 licensing and Odoo attribution

### Requirement: Uninstallation

The module SHALL be uninstallable without leaving orphaned data.

#### Scenario: Clean uninstall
- **WHEN** `loomworks_core` is uninstalled via Apps
- **THEN** the uninstallation completes without errors
- **AND** the standard Odoo branding is restored
- **AND** no Loomworks-specific data remains in the database

## Testing Criteria

### Automated Tests
1. Module installation test passes
2. Module uninstallation test passes
3. Template inheritance selectors are valid
4. SCSS compilation produces no errors

### Manual Tests
1. Visual verification of login page branding
2. Visual verification of navbar branding
3. Favicon visible in browser tabs
4. Color palette applied to buttons, links, and UI elements
5. Reports show company logo
6. No JavaScript console errors during normal operation
7. Dark mode compatibility (if applicable)

### Browser Compatibility
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

### Performance
- Page load time not significantly impacted by branding module
- Asset bundle size increase is reasonable (<50KB additional)
