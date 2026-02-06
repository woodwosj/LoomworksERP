## ADDED Requirements

### Requirement: User-Visible Branding Consistency
All user-visible text, titles, labels, error messages, notifications, and help strings in the Loomworks ERP application MUST display "Loomworks ERP" (or contextually appropriate variants like "Loomworks", "Loomworks POS", "Loomworks Discuss") instead of "Odoo".

#### Scenario: Browser tab title shows Loomworks
- **WHEN** a user opens the Loomworks ERP backend in a browser
- **THEN** the browser tab title SHALL display "Loomworks ERP" as the default title (or a module-specific title like "Loomworks POS")

#### Scenario: Error dialog shows Loomworks branding
- **WHEN** an error occurs in the application (server error, client error, network error, or warning)
- **THEN** the error dialog title SHALL display "Loomworks ERP Error" (or variant like "Loomworks ERP Warning", "Loomworks ERP Network Error") instead of "Odoo Error"

#### Scenario: Session expired notification shows Loomworks branding
- **WHEN** the user's session expires
- **THEN** the notification title SHALL display "Loomworks ERP Session Expired" and the message SHALL reference "Loomworks" instead of "Odoo"

#### Scenario: Settings page shows Loomworks edition
- **WHEN** a user opens the Settings page
- **THEN** the edition information SHALL display "Loomworks ERP <version>" instead of "Odoo <version> (Community Edition)"

#### Scenario: Reports show Loomworks title
- **WHEN** a report (invoice, sales order, purchase order) is generated
- **THEN** the report page title SHALL default to "Loomworks Report" instead of "Odoo Report"

#### Scenario: Calendar meetings show Loomworks branding
- **WHEN** a user views the calendar view
- **THEN** the "New meeting" button SHALL display "Loomworks meeting" instead of "Odoo meeting"
- **AND** calendar email templates SHALL reference "Join with Loomworks Discuss" instead of "Join with Odoo Discuss"

### Requirement: Email Template Branding
All email templates sent by the system MUST display "Loomworks" branding instead of "Odoo" branding, including "Powered by" footers, invitation text, and signup flows.

#### Scenario: Signup invitation email shows Loomworks branding
- **WHEN** a user is invited to connect to the system via email
- **THEN** the email subject SHALL reference "Loomworks ERP" instead of "Odoo"
- **AND** the email body SHALL say "Welcome to Loomworks ERP" instead of "Welcome to Odoo"
- **AND** all "Powered by" links SHALL point to loomworks.solutions instead of odoo.com

#### Scenario: Password reset email shows Loomworks branding
- **WHEN** a password reset is requested
- **THEN** the email SHALL reference "Loomworks ERP account" instead of "Odoo account"

#### Scenario: Powered-by footer in all emails
- **WHEN** any system email is sent (portal invitations, expense reports, gamification, livechat transcripts, etc.)
- **THEN** the "Powered by" footer SHALL link to loomworks.solutions with "Loomworks" text instead of odoo.com with "Odoo" text

### Requirement: Logo and Icon Branding
All logo images, favicons, PWA icons, and avatar images MUST display Loomworks branding instead of Odoo branding.

#### Scenario: Login page displays Loomworks logo
- **WHEN** a user visits the login page
- **THEN** the logo displayed SHALL be the Loomworks logo

#### Scenario: PWA installation shows Loomworks branding
- **WHEN** a user installs the application as a Progressive Web App
- **THEN** the PWA name SHALL be "Loomworks ERP"
- **AND** the PWA icons (192x192, 512x512) SHALL display the Loomworks icon

#### Scenario: Database manager shows Loomworks branding
- **WHEN** a user accesses the database manager page
- **THEN** the page title SHALL be "Loomworks ERP"
- **AND** all text referencing "Odoo" SHALL be replaced with "Loomworks ERP"

### Requirement: Chat Bot Branding (LoomBot)
The system chat bot MUST be branded as "LoomBot" instead of "OdooBot" in all user-visible contexts.

#### Scenario: Bot name in chat
- **WHEN** LoomBot sends a message in a chat channel
- **THEN** the sender name SHALL display as "LoomBot" instead of "OdooBot"

#### Scenario: Bot avatar
- **WHEN** LoomBot appears in chat or notifications
- **THEN** the avatar image SHALL be a Loomworks-branded avatar instead of the OdooBot avatar

#### Scenario: Bot mention in digest tips
- **WHEN** a digest tip suggests mentioning the bot
- **THEN** the tip text SHALL reference "@LoomBot" instead of "@OdooBot"

### Requirement: Portal and Website Branding
All portal pages and website pages MUST display Loomworks branding instead of Odoo branding.

#### Scenario: Portal footer shows Loomworks
- **WHEN** a user views any portal page
- **THEN** the "Powered by" footer SHALL display the Loomworks logo and link to loomworks.solutions

#### Scenario: Website CTA snippets show Loomworks
- **WHEN** a website page displays a Call-to-Action snippet
- **THEN** the default text SHALL NOT reference "Odoo" (e.g., "50,000+ companies run Odoo" SHALL be changed to a Loomworks-appropriate message)

#### Scenario: Website meta generator
- **WHEN** a website page is rendered
- **THEN** the HTML meta generator tag SHALL reference "Loomworks" instead of "Odoo"

#### Scenario: Livechat branding
- **WHEN** the livechat widget is displayed on an external website
- **THEN** the "Powered by" text SHALL reference "Loomworks" instead of "Odoo"

### Requirement: POS Branding
All Point of Sale screens MUST display Loomworks branding instead of Odoo branding.

#### Scenario: POS page title
- **WHEN** a user opens the Point of Sale application
- **THEN** the browser tab title SHALL display "Loomworks POS" instead of "Odoo POS"

#### Scenario: POS self-order title
- **WHEN** a customer opens the self-order page
- **THEN** the page title SHALL display "Loomworks Self Order" instead of "Odoo Self Order"

#### Scenario: POS customer display
- **WHEN** the customer-facing display is shown
- **THEN** the "Powered by" branding SHALL show Loomworks logo instead of Odoo logo

### Requirement: LGPL Attribution Preservation
All changes MUST preserve proper LGPL v3 attribution to Odoo S.A. as the original author of the upstream codebase.

#### Scenario: Copyright headers preserved
- **WHEN** any source file is modified for rebranding
- **THEN** the original "Part of Odoo" copyright header MAY be updated to "Part of Loomworks ERP" but MUST retain attribution such as "Based on Odoo Community by Odoo S.A."

#### Scenario: Settings page attribution
- **WHEN** a user views the Settings page edition information
- **THEN** the copyright text SHALL include "Based on Odoo Community by Odoo S.A." alongside Loomworks branding

### Requirement: Internal References Preservation
Python package imports, XML namespace tags, CSS class prefixes, URL routes, module technical names, and other internal/structural references to "odoo" MUST NOT be changed, as they are part of the framework's API contract.

#### Scenario: Python imports remain unchanged
- **WHEN** a developer writes `from odoo import models`
- **THEN** the import SHALL work identically to upstream Odoo
- **AND** no import paths SHALL be renamed

#### Scenario: URL routes remain unchanged
- **WHEN** a user or integration accesses `/odoo/...` URL routes
- **THEN** the routes SHALL function identically to upstream Odoo
- **AND** no route paths SHALL be renamed

#### Scenario: CSS classes remain unchanged
- **WHEN** a theme or module references CSS classes with `o_` prefix
- **THEN** the classes SHALL function identically to upstream Odoo
- **AND** no class names SHALL be renamed
