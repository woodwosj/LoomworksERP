## Context

The `upwork_integration` module was previously installed in the Loomworks ERP Odoo v18 database (version 18.0.1.0.0, installed December 2025) but the source code directory was lost. The database retains:

- **6 tables**: `upwork_account`, `upwork_contract`, `upwork_timelog`, `upwork_earning`, `upwork_milestone`, `upwork_proposal`
- **151 `ir_model_data` records**: views, menus, actions, cron jobs, security groups, access rights, accounting data
- **7 registered models** in `ir_model`: including the abstract `upwork.api.service`
- **4 cron jobs**: contract sync (4h), time log sync (daily), earnings sync (weekly), token refresh (daily)
- **2 security groups**: `group_upwork_user` (read-only) and `group_upwork_manager` (full CRUD)
- **21 access control records**: 7 models x 3 permission tiers (user, manager, system)

The Upwork API has transitioned to a GraphQL-first approach, though REST endpoints remain available. The official Python SDK (`python-upwork-oauth2` v3.1.0) supports both via a generic HTTP client that wraps OAuth2 authentication.

### Stakeholders

- **Loomworks freelancers/contractors** who use Upwork and want automated time/earnings tracking
- **Loomworks project managers** who need visibility into Upwork contracts and proposals
- **AI agents** that need to query Upwork data (contracts, earnings, proposals) on behalf of users

## Goals / Non-Goals

### Goals

- Rebuild the module source code so that it matches the existing database schema exactly (no migrations)
- Implement OAuth2 authorization code flow for connecting Upwork accounts
- Sync Upwork contracts, time logs, and earnings into Odoo models via scheduled cron jobs
- Create Odoo timesheets (`account.analytic.line`) from synced time logs
- Create draft invoices (`account.move`) from synced earnings with proper fee accounting
- Track fixed-price milestones
- Manage proposal pipeline with status tracking
- Provide AI tool integration so Claude agents can query Upwork data
- Reproduce all 17 views, 6 menus, 10 window actions, and 4 cron jobs registered in the database

### Non-Goals

- Sending proposals or bidding on jobs via the API (Upwork prohibits automated job applications)
- Real-time webhooks (Upwork API does not provide webhook support; polling via cron is the only option)
- Multi-organization support within a single Upwork account (one Upwork account per Odoo company)
- Encrypting OAuth tokens at the application level (Odoo stores credentials in plain text by convention; database-level encryption is the mitigation)
- Building a custom Upwork dashboard (standard Odoo list/form/pivot views are sufficient for MVP)

## Decisions

### Decision 1: Use `python-upwork-oauth2` SDK for API Communication

**What**: Use the official Upwork Python SDK (`python-upwork-oauth2` v3.1.0, Apache 2.0) as the HTTP client layer.

**Why**: The SDK handles OAuth2 token management (auto-refresh), provides a clean `client.get()/post()` interface, and is maintained by Upwork. It supports both REST and GraphQL endpoints via generic HTTP methods.

**Alternatives considered**:
- **Raw `requests` + `requests-oauthlib`**: More control but duplicates OAuth2 token refresh logic that the SDK already handles. More code to maintain.
- **Custom GraphQL client (`gql`)**: Would require building OAuth2 integration from scratch. Overkill when the SDK already wraps HTTP methods.

**Trade-off**: The SDK is a thin wrapper (last release June 2023) and may lag behind API changes. Mitigated by the fact that GraphQL queries are string-based and can be updated independently of the SDK version.

### Decision 2: GraphQL for Data Queries, REST for OAuth2

**What**: Use Upwork's GraphQL endpoint (`https://api.upwork.com/graphql`) for fetching contracts, time reports, and earnings. Use REST endpoints for OAuth2 token exchange.

**Why**: Upwork is migrating to GraphQL as the primary API interface. GraphQL allows fetching exactly the fields needed in a single request, reducing API calls and staying within rate limits (300 req/min/IP).

**OAuth2 endpoints** (REST, no GraphQL alternative):
- Authorization: `GET https://www.upwork.com/ab/account-security/oauth2/authorize`
- Token exchange: `POST https://www.upwork.com/api/v3/oauth2/token`

**GraphQL endpoint**: `POST https://api.upwork.com/graphql`

**Alternatives considered**:
- **REST-only**: Upwork still supports REST but it is deprecated for data queries. GraphQL is the recommended path forward.
- **GraphQL-only**: Not possible; OAuth2 token endpoints are REST-only.

### Decision 3: Store OAuth Tokens in Plain Text Database Fields

**What**: Store `access_token`, `refresh_token`, and `client_secret` as `Char` fields in `upwork.account`, displayed with `password="True"` widget in the form view. Visible only to `base.group_system` users.

**Why**: This matches Odoo's standard convention for credential storage (see `payment.provider`, `social.account`, `google.gmail.mixin`). The form view already uses `password="True"` and `groups="base.group_system"` to restrict visibility.

**Alternatives considered**:
- **Encrypted fields via `cryptography` library**: Would add complexity and a key management burden. Odoo does not encrypt any credentials at the application layer; database-level encryption (PostgreSQL TDE or disk encryption) is the standard mitigation.
- **External secrets manager (Vault, AWS Secrets Manager)**: Out of scope for an open-source community module.

**Risk**: Tokens are readable by database administrators. Mitigated by: (1) database-level access controls, (2) token expiry (access tokens are short-lived), (3) refresh tokens can be revoked via Upwork developer portal.

### Decision 4: Cron-Based Synchronization with Idempotent Upserts

**What**: Use 4 scheduled cron jobs for data synchronization:
- `cron_sync_contracts()` -- every 4 hours
- `cron_sync_timelogs()` -- daily
- `cron_sync_earnings()` -- weekly
- `cron_refresh_tokens()` -- daily

Each sync method fetches data from Upwork API and performs idempotent upserts using unique external IDs (`upwork_contract_id`, `upwork_timelog_id`, `upwork_earning_id`).

**Why**: Upwork does not support webhooks. Polling is the only option. The intervals balance API rate limits (300 req/min) against data freshness needs. The existing database has these exact cron configurations.

**Alternatives considered**:
- **Event-driven sync**: Not possible without webhooks.
- **Manual sync only**: Would miss time-sensitive data (daily time logs).
- **More frequent polling**: Would consume API quota unnecessarily.

### Decision 5: Timesheet and Invoice Creation as Explicit Actions

**What**: Provide two server actions -- `action_create_timesheets` (on `upwork.timelog`) and `action_create_invoices` (on `upwork.earning`) -- that can be triggered manually or automatically via settings toggles (`upwork_auto_create_timesheets`, `upwork_auto_create_invoices`).

**Why**: Creating financial records (invoices, timesheets) should be deliberate. The dual-mode approach (manual button + auto toggle) gives users control. The settings view already has both toggles defined in the database.

**Implementation**:
- Timesheets: Create `account.analytic.line` records linked via `timesheet_id` FK (unique constraint enforced)
- Invoices: Create `account.move` records with proper line items (gross amount, Upwork fee deduction, net amount). Fee recorded as a separate journal entry if `upwork_fee_expense_account_id` is configured.

### Decision 6: AI Tool Provider for Upwork Data Access

**What**: Create `upwork.tool.provider` inheriting from `loomworks.ai.tool.provider` with tools for querying contracts, time logs, earnings, and proposals.

**Why**: Follows the established pattern from `sign.tool.provider` (see `loomworks_addons/loomworks_sign/models/sign_tool_provider.py`). Enables Claude AI agents to answer questions like "What are my active Upwork contracts?" or "How much did we earn last month on Upwork?"

**Tools to register**:
- `upwork_list_contracts` (category: data, risk: safe)
- `upwork_get_earnings_summary` (category: data, risk: safe)
- `upwork_list_timelogs` (category: data, risk: safe)
- `upwork_list_proposals` (category: data, risk: safe)
- `upwork_sync_now` (category: action, risk: moderate, requires_confirmation: True)

## Architecture

### Module Structure

```
loomworks_addons/upwork_integration/
+-- __init__.py
+-- __manifest__.py
+-- controllers/
|   +-- __init__.py
|   +-- upwork_oauth.py          # OAuth2 callback handler
+-- models/
|   +-- __init__.py
|   +-- upwork_account.py        # upwork.account (mail.thread, mail.activity.mixin)
|   +-- upwork_contract.py       # upwork.contract (mail.thread, mail.activity.mixin)
|   +-- upwork_timelog.py        # upwork.timelog
|   +-- upwork_earning.py        # upwork.earning
|   +-- upwork_milestone.py      # upwork.milestone
|   +-- upwork_proposal.py       # upwork.proposal (mail.thread, mail.activity.mixin)
|   +-- upwork_api_service.py    # upwork.api.service (AbstractModel)
|   +-- upwork_tool_provider.py  # upwork.tool.provider (AbstractModel)
|   +-- res_config_settings.py   # res.config.settings extension
+-- views/
|   +-- upwork_account_views.xml
|   +-- upwork_contract_views.xml
|   +-- upwork_timelog_views.xml
|   +-- upwork_earning_views.xml
|   +-- upwork_proposal_views.xml
|   +-- upwork_menus.xml
|   +-- res_config_settings_views.xml
|   +-- res_partner_views.xml
+-- security/
|   +-- upwork_security.xml      # Groups + record rules
|   +-- ir.model.access.csv      # 21 ACL entries
+-- data/
|   +-- ir_cron_data.xml         # 4 cron jobs
+-- static/
|   +-- description/
|       +-- icon.png
+-- tests/
    +-- __init__.py
    +-- test_upwork_account.py
    +-- test_upwork_sync.py
```

### Model Relationships

```
upwork.account (1) ---< (N) upwork.contract
upwork.contract (1) ---< (N) upwork.timelog
upwork.contract (1) ---< (N) upwork.earning
upwork.contract (1) ---< (N) upwork.milestone
upwork.contract (1) ---< (N) upwork.proposal (via contract_id, optional)
upwork.account (1) ---< (N) upwork.proposal (via upwork_account_id)
upwork.account (1) ---< (N) upwork.timelog (via upwork_account_id, denormalized)
upwork.account (1) ---< (N) upwork.earning (via upwork_account_id, denormalized)

upwork.contract (N) >--- (1) res.partner (client)
upwork.contract (N) >--- (1) project.project (Odoo project)
upwork.timelog (N) >--- (1) account.analytic.line (timesheet)
upwork.earning (N) >--- (1) account.move (invoice)
upwork.earning (N) >--- (1) account.move (fee journal entry)
upwork.earning (N) >--- (1) res.partner
```

### API Service Layer

`upwork.api.service` is an AbstractModel (no database table) that centralizes all Upwork API communication:

```python
class UpworkApiService(models.AbstractModel):
    _name = 'upwork.api.service'

    def _get_client(self, account):
        """Build authenticated Upwork SDK client from account tokens."""

    def _graphql_query(self, account, query, variables=None):
        """Execute a GraphQL query against Upwork API."""

    def _refresh_token(self, account):
        """Refresh OAuth2 access token using refresh token."""

    def fetch_contracts(self, account):
        """Fetch contracts from Upwork GraphQL API."""

    def fetch_timelogs(self, account, date_from, date_to):
        """Fetch time reports for a date range."""

    def fetch_earnings(self, account, date_from, date_to):
        """Fetch earnings/financial reports."""

    def cron_sync_contracts(self):
        """Cron entry point: sync contracts for all active accounts."""

    def cron_sync_timelogs(self):
        """Cron entry point: sync time logs for all active accounts."""

    def cron_sync_earnings(self):
        """Cron entry point: sync earnings for all active accounts."""

    def cron_refresh_tokens(self):
        """Cron entry point: refresh tokens for all connected accounts."""
```

### OAuth2 Flow

1. User enters `client_id` and `client_secret` in the account form
2. User clicks "Connect to Upwork" button
3. `action_authorize()` generates a state token, stores it in `oauth_state`, sets state to `connecting`
4. User is redirected to: `https://www.upwork.com/ab/account-security/oauth2/authorize?client_id=...&response_type=code&redirect_uri=...&state=...`
5. User authorizes on Upwork
6. Upwork redirects to callback URL: `/upwork/oauth/callback?code=...&state=...`
7. Controller validates state token, exchanges code for access/refresh tokens via `POST https://www.upwork.com/api/v3/oauth2/token`
8. Tokens stored in `upwork.account`, state set to `connected`

## Database Schema

All tables already exist in the database. The ORM model definitions MUST match exactly to avoid migration errors.

### upwork_account

| Column | Odoo Type | DB Type | Required | Notes |
|--------|-----------|---------|----------|-------|
| name | Char | varchar | Yes | Account name, unique per company |
| client_id | Char | varchar | Yes | OAuth2 client ID |
| client_secret | Char | varchar | Yes | OAuth2 client secret |
| access_token | Char | varchar | No | OAuth2 access token |
| refresh_token | Char | varchar | No | OAuth2 refresh token |
| state | Selection | varchar | Yes | draft/connecting/connected/error |
| oauth_state | Char | varchar | No | CSRF token for OAuth flow |
| last_error | Text | text | No | Last error message |
| is_connected | Boolean | boolean | No | Connection status flag |
| sync_enabled | Boolean | boolean | No | Enable/disable sync |
| active | Boolean | boolean | No | Archive flag |
| token_expiry | Datetime | timestamp | No | Token expiration time |
| last_sync | Datetime | timestamp | No | Last successful sync |
| company_id | Many2one(res.company) | int FK | Yes | Multi-company support |

**Constraints**: `UNIQUE(name, company_id)`
**Inherits**: `mail.thread`, `mail.activity.mixin`

### upwork_contract

| Column | Odoo Type | DB Type | Required | Notes |
|--------|-----------|---------|----------|-------|
| name | Char | varchar | Yes | Contract title |
| upwork_contract_id | Char | varchar | Yes | External Upwork contract ID |
| contract_type | Selection | varchar | Yes | hourly/fixed |
| state | Selection | varchar | No | active/paused/ended |
| start_date | Date | date | No | Contract start |
| end_date | Date | date | No | Contract end |
| hourly_rate | Monetary | numeric | No | Rate for hourly contracts |
| upwork_account_id | Many2one(upwork.account) | int FK | Yes | Parent account (CASCADE delete) |
| partner_id | Many2one(res.partner) | int FK | No | Upwork client |
| project_id | Many2one(project.project) | int FK | No | Linked Odoo project |
| currency_id | Many2one(res.currency) | int FK | Yes | Currency |
| company_id | Many2one(res.company) | int FK | Yes | Company |

**Constraints**: `UNIQUE(upwork_contract_id, upwork_account_id)`
**Indexes**: `upwork_contract_id`
**Inherits**: `mail.thread`, `mail.activity.mixin`
**One2many**: `earning_ids` -> `upwork.earning`, `timelog_ids` -> `upwork.timelog`

### upwork_timelog

| Column | Odoo Type | DB Type | Required | Notes |
|--------|-----------|---------|----------|-------|
| upwork_timelog_id | Char | varchar | No | External Upwork time log ID |
| date | Date | date | Yes | Work date |
| memo | Text | text | No | Work description |
| tracked_hours | Float | numeric | No | Auto-tracked hours |
| manual_hours | Float | numeric | No | Manually logged hours |
| total_hours | Float | numeric | No | Sum of tracked + manual |
| contract_id | Many2one(upwork.contract) | int FK | Yes | Parent contract (CASCADE) |
| upwork_account_id | Many2one(upwork.account) | int FK | No | Denormalized account ref |
| timesheet_id | Many2one(account.analytic.line) | int FK | No | Linked Odoo timesheet |
| company_id | Many2one(res.company) | int FK | Yes | Company |

**Constraints**: `UNIQUE(upwork_timelog_id, contract_id)`, `UNIQUE(contract_id, date)`, `UNIQUE(timesheet_id)`
**Indexes**: `contract_id`, `date`, `timesheet_id`, `upwork_timelog_id`

### upwork_earning

| Column | Odoo Type | DB Type | Required | Notes |
|--------|-----------|---------|----------|-------|
| name | Char | varchar | Yes | Earning description |
| upwork_earning_id | Char | varchar | No | External Upwork earning ID |
| date | Date | date | Yes | Payment date |
| period_start | Date | date | No | Billing period start |
| period_end | Date | date | No | Billing period end |
| gross_amount | Monetary | numeric | Yes | Total before fees |
| upwork_fee | Monetary | numeric | No | Upwork service fee amount |
| upwork_fee_percent | Float | numeric | No | Fee percentage |
| net_amount | Monetary | numeric | No | Amount after fees |
| total_hours | Float | numeric | No | Hours in this earning period |
| contract_id | Many2one(upwork.contract) | int FK | Yes | Parent contract (CASCADE) |
| upwork_account_id | Many2one(upwork.account) | int FK | No | Denormalized account ref |
| partner_id | Many2one(res.partner) | int FK | No | Client partner |
| currency_id | Many2one(res.currency) | int FK | Yes | Currency |
| invoice_id | Many2one(account.move) | int FK | No | Generated invoice |
| journal_entry_id | Many2one(account.move) | int FK | No | Fee journal entry |
| company_id | Many2one(res.company) | int FK | Yes | Company |

**Constraints**: `UNIQUE(upwork_earning_id, contract_id)`, `UNIQUE(invoice_id)`
**Indexes**: `contract_id`, `date`, `invoice_id`, `upwork_earning_id`

### upwork_milestone

| Column | Odoo Type | DB Type | Required | Notes |
|--------|-----------|---------|----------|-------|
| name | Char | varchar | Yes | Milestone name |
| state | Selection | varchar | No | pending/active/completed/paid |
| due_date | Date | date | No | Due date |
| amount | Monetary | numeric | No | Milestone amount |
| contract_id | Many2one(upwork.contract) | int FK | Yes | Parent contract (CASCADE) |
| currency_id | Many2one(res.currency) | int FK | Yes | Currency |
| company_id | Many2one(res.company) | int FK | Yes | Company |

### upwork_proposal

| Column | Odoo Type | DB Type | Required | Notes |
|--------|-----------|---------|----------|-------|
| name | Char | varchar | Yes | Proposal reference/name |
| state | Selection | varchar | No | draft/submitted/hired/declined |
| title | Char | varchar | No | Job title |
| module_list | Char | varchar | No | Relevant Odoo modules |
| client_industry | Char | varchar | No | Client's industry |
| submitted_date | Date | date | No | When proposal was submitted |
| job_requirements | Text | text | No | Job posting requirements |
| html_content | Html | text | No | Proposal content (rich text) |
| hourly_rate | Float | numeric(dp) | No | Proposed rate |
| estimated_hours | Float | float8 | No | Estimated project hours |
| upwork_account_id | Many2one(upwork.account) | int FK | Yes | Parent account (CASCADE) |
| contract_id | Many2one(upwork.contract) | int FK | No | Resulting contract if hired |
| company_id | Many2one(res.company) | int FK | Yes | Company |

**Inherits**: `mail.thread`, `mail.activity.mixin`

## API Integration

### Upwork OAuth2 Endpoints

| Endpoint | Method | URL |
|----------|--------|-----|
| Authorization | GET | `https://www.upwork.com/ab/account-security/oauth2/authorize` |
| Token Exchange | POST | `https://www.upwork.com/api/v3/oauth2/token` |
| GraphQL | POST | `https://api.upwork.com/graphql` |

### Authorization URL Parameters

```
client_id={client_id}
response_type=code
redirect_uri={base_url}/upwork/oauth/callback
state={csrf_token}
```

### Token Exchange Request

```
POST https://www.upwork.com/api/v3/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
code={authorization_code}
redirect_uri={redirect_uri}
client_id={client_id}
client_secret={client_secret}
```

### Token Refresh Request

```
POST https://www.upwork.com/api/v3/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
refresh_token={refresh_token}
client_id={client_id}
client_secret={client_secret}
```

### Rate Limits

- 300 requests per minute per IP address
- Token rotation recommended every 12 months for API credentials
- Access tokens should be refreshed before expiry (biweekly recommended)

### Example GraphQL Queries

**Fetch Contracts**:
```graphql
query {
  contracts {
    edges {
      node {
        id
        title
        contractType
        status
        startDate
        endDate
        hourlyChargeRate
        client {
          companyName
        }
      }
    }
  }
}
```

**Fetch Time Reports** (REST fallback if needed):
```
GET /api/v3/companies/{company_id}/time_reports
    ?start_date={YYYY-MM-DD}
    &end_date={YYYY-MM-DD}
```

## Risks / Trade-offs

### Risk 1: Upwork API Changes

**Risk**: Upwork may deprecate REST endpoints or change GraphQL schema without notice.
**Likelihood**: Medium (GraphQL API changelog shows periodic changes).
**Mitigation**: Isolate all API calls in `upwork.api.service`. Log API responses. Pin GraphQL query versions. Monitor the [Upwork API Changelog](https://www.upwork.com/developer/documentation/graphql/api/docs/api-changelog.html).

### Risk 2: OAuth Token Storage Security

**Risk**: Tokens stored in plain text are readable by database administrators.
**Likelihood**: Low (standard Odoo practice).
**Mitigation**: Form view uses `password="True"` widget. Fields restricted to `base.group_system`. Database-level encryption recommended for production deployments. Tokens can be revoked from Upwork developer portal.

### Risk 3: Schema Mismatch on Module Upgrade

**Risk**: If ORM field definitions do not exactly match existing database columns, Odoo may attempt a migration that fails.
**Likelihood**: Medium (critical to get right).
**Mitigation**: Database schemas have been captured precisely from `\d` output. All field types, constraints, and indexes are documented above. Implementation MUST cross-reference this document.

### Risk 4: Rate Limiting During Initial Sync

**Risk**: First sync after connecting an account with many contracts could exceed 300 req/min.
**Likelihood**: Low (unlikely to have >300 contracts).
**Mitigation**: Implement pagination and rate-limit-aware retry with exponential backoff in `upwork.api.service`.

### Risk 5: `python-upwork-oauth2` SDK Staleness

**Risk**: Last release was June 2023 (v3.1.0). May not track latest API changes.
**Likelihood**: Medium.
**Mitigation**: The SDK is a thin HTTP wrapper; we use it for OAuth2 only. GraphQL queries are string-based and independent of SDK version. If SDK becomes incompatible, we can replace it with `requests-oauthlib` with minimal changes.

## Migration Plan

No database migration is needed. All 6 tables exist with correct schemas. The ORM will reconcile field definitions when the module is loaded. The `ir_module_module` state is already `installed`.

**Steps**:
1. Place rebuilt module source in `loomworks_addons/upwork_integration/`
2. Restart Odoo server (module will be loaded from new path)
3. Run `odoo -u upwork_integration` to reconcile ORM definitions with existing tables
4. Verify all views, menus, and cron jobs are functional

**Rollback**: Remove the module directory and restart. The `installed` state remains but the module simply will not load (same as current broken state).

## Open Questions

1. **Upwork GraphQL schema details**: The Upwork GraphQL documentation requires authentication to access the full schema explorer. Exact query field names will need to be verified against the API explorer during implementation. The SDK and API documentation pages return 403 for unauthenticated access.

2. **Existing `ir_model_data` for non-Upwork models**: The `upwork_integration` module also owns data migration and EEM ticket models (`data_migration_source`, `data_migration_job`, `eem_ticket`, etc.). These appear to be unrelated features bundled in the same module. Decision: rebuild only the Upwork-specific functionality. The data migration and EEM ticket features should be split into separate modules in a follow-up change.

3. **`estimated_hours` column type**: The `upwork_proposal.estimated_hours` column uses `double precision` (float8) in PostgreSQL rather than the standard `numeric` type used by Odoo's `Float` field. This suggests the original code used `fields.Float` without specifying digits precision, which maps to `float8` in PostgreSQL. The rebuild should match this behavior.

4. **Partner view extension**: The existing `res_partner_view_form_upwork` view extends partner forms. The exact content needs to be reconstructed; the database stores the compiled arch but the original source intent should show Upwork contract links on partner records.
