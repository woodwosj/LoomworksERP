# Change: Rebuild Upwork Integration Module

## Why

The `upwork_integration` module is registered as `installed` (v18.0.1.0.0) in the Odoo database but its entire source code directory is missing from the filesystem. All six database tables (`upwork_account`, `upwork_contract`, `upwork_timelog`, `upwork_earning`, `upwork_milestone`, `upwork_proposal`) exist with correct schemas, indexes, and foreign-key constraints, but contain no data. All metadata -- menus, window actions, server actions, cron jobs, views, security groups, and access rights -- are present in `ir_model_data`. The module must be rebuilt from scratch to restore the integration between Loomworks ERP and the Upwork freelancing platform. The existing database schemas serve as the definitive blueprint for the rebuild.

## What Changes

### New Module: `loomworks_addons/upwork_integration/`

- **Module skeleton**: `__manifest__.py`, `__init__.py`, all sub-package `__init__.py` files
- **Security**: `security/upwork_security.xml` (groups: `group_upwork_user`, `group_upwork_manager`), `security/ir.model.access.csv` (21 ACL rows for 7 models x 3 roles: user, manager, system)
- **Core models** (6 stored + 1 abstract):
  - `upwork.account` -- OAuth2 connection management, token storage, sync state (inherits `mail.thread`, `mail.activity.mixin`)
  - `upwork.contract` -- Upwork contract tracking, linked to partner and project (inherits `mail.thread`, `mail.activity.mixin`)
  - `upwork.timelog` -- Daily time log entries, linked to Odoo timesheets (`account.analytic.line`)
  - `upwork.earning` -- Earnings/payment records with Upwork fee tracking, linked to invoices (`account.move`)
  - `upwork.milestone` -- Fixed-price contract milestones
  - `upwork.proposal` -- Proposal pipeline management (inherits `mail.thread`, `mail.activity.mixin`)
  - `upwork.api.service` -- Abstract model for Upwork API communication (OAuth2 + GraphQL)
- **Settings extension**: `res.config.settings` inheriting class with 5 Upwork-specific fields (3 account references + 2 boolean toggles)
- **Controllers**: OAuth2 callback controller for handling Upwork authorization redirects
- **Views**: 17 XML views (form, list, search, pivot for each model + settings + partner extension + QWeb template)
- **Menus**: Root menu + 5 sub-menus (Contracts, Time Logs, Earnings, Proposals, Accounts)
- **Actions**: 10 window actions + 6 server actions (cron handlers + create timesheets/invoices)
- **Cron jobs**: 4 scheduled actions (sync contracts every 4h, sync time logs daily, sync earnings weekly, refresh OAuth tokens daily)
- **AI tool provider**: `upwork.tool.provider` inheriting `loomworks.ai.tool.provider` for AI-driven Upwork queries
- **Data files**: Default account mappings, cron job definitions, security group hierarchy
- **External dependency**: `python-upwork-oauth2` (PyPI package for Upwork API bindings)

### Extended Models (in other modules)

- `res.config.settings` -- Add 5 Upwork configuration fields
- `res.partner` -- Form view extension showing Upwork contract link

## Impact

- **Affected specs**: `upwork-integration` (new capability spec)
- **Affected code**:
  - `loomworks_addons/upwork_integration/` (entire new module, ~25 files)
  - No changes to existing modules (self-contained integration)
- **Database**: All 6 tables already exist; ORM will reconcile column definitions on module upgrade. No manual migration needed.
- **Dependencies**: Requires `base`, `mail`, `project`, `hr_timesheet`, `account`, `loomworks_core`, `loomworks_ai`
- **External**: Requires Upwork API developer application credentials (client_id + client_secret) obtained from https://www.upwork.com/developer
