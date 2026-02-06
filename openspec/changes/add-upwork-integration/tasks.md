## 1. Module Skeleton

- [ ] 1.1 Create `loomworks_addons/upwork_integration/__manifest__.py` with name, version (18.0.1.0.0), category, depends (`base`, `mail`, `project`, `hr_timesheet`, `account`, `loomworks_core`, `loomworks_ai`), external dependency on `python-upwork-oauth2`, data files, and assets
- [ ] 1.2 Create `loomworks_addons/upwork_integration/__init__.py` importing `models` and `controllers`
- [ ] 1.3 Create `loomworks_addons/upwork_integration/models/__init__.py` importing all model files
- [ ] 1.4 Create `loomworks_addons/upwork_integration/controllers/__init__.py` importing `upwork_oauth`
- [ ] 1.5 Create `loomworks_addons/upwork_integration/tests/__init__.py`
- [ ] 1.6 Create `loomworks_addons/upwork_integration/static/description/icon.png` placeholder

## 2. Security

- [ ] 2.1 Create `security/upwork_security.xml` defining `group_upwork_user` and `group_upwork_manager` with proper category and implied groups (manager implies user)
- [ ] 2.2 Create `security/ir.model.access.csv` with 21 ACL rows: 7 models (`upwork.account`, `upwork.contract`, `upwork.timelog`, `upwork.earning`, `upwork.milestone`, `upwork.proposal`, `upwork.api.service`) x 3 roles (user: read-only, manager: full CRUD, system: full CRUD)
- [ ] 2.3 Verify XML IDs match database `ir_model_data` names exactly: `group_upwork_user`, `group_upwork_manager`, `access_upwork_account_user`, `access_upwork_account_manager`, `access_upwork_account_system`, etc.

## 3. Core Models (dependency order)

- [ ] 3.1 Create `models/upwork_api_service.py` -- AbstractModel `upwork.api.service` with methods: `_get_client()`, `_graphql_query()`, `_refresh_token()`, `fetch_contracts()`, `fetch_timelogs()`, `fetch_earnings()`, `cron_sync_contracts()`, `cron_sync_timelogs()`, `cron_sync_earnings()`, `cron_refresh_tokens()`
- [ ] 3.2 Create `models/upwork_account.py` -- Model `upwork.account` inheriting `mail.thread`, `mail.activity.mixin` with all fields matching DB schema exactly (name, client_id, client_secret, access_token, refresh_token, state selection [draft/connecting/connected/error], oauth_state, last_error, is_connected, sync_enabled, active, token_expiry, last_sync, company_id). Include SQL constraint `upwork_account_name_company_uniq`. Include methods: `action_authorize()`, `action_test_connection()`, `action_disconnect()`
- [ ] 3.3 Create `models/upwork_contract.py` -- Model `upwork.contract` inheriting `mail.thread`, `mail.activity.mixin` with fields matching DB schema (name, upwork_contract_id, contract_type selection [hourly/fixed], state selection [active/paused/ended], start_date, end_date, hourly_rate monetary, upwork_account_id, partner_id, project_id, currency_id, company_id, earning_ids One2many, timelog_ids One2many). Include SQL constraints for unique contract per account and index on upwork_contract_id
- [ ] 3.4 Create `models/upwork_timelog.py` -- Model `upwork.timelog` with fields matching DB schema (upwork_timelog_id, date, memo, tracked_hours, manual_hours, total_hours, contract_id, upwork_account_id, timesheet_id, company_id). Include SQL constraints for unique timelog per contract, unique per contract+date, unique timesheet_id. Include method `action_create_timesheets()`
- [ ] 3.5 Create `models/upwork_earning.py` -- Model `upwork.earning` with fields matching DB schema (name, upwork_earning_id, date, period_start, period_end, gross_amount monetary, upwork_fee monetary, upwork_fee_percent float, net_amount monetary, total_hours, contract_id, upwork_account_id, partner_id, currency_id, invoice_id, journal_entry_id, company_id). Include SQL constraints and method `action_create_invoices()`
- [ ] 3.6 Create `models/upwork_milestone.py` -- Model `upwork.milestone` with fields matching DB schema (name, state selection [pending/active/completed/paid], due_date, amount monetary, contract_id, currency_id, company_id)
- [ ] 3.7 Create `models/upwork_proposal.py` -- Model `upwork.proposal` inheriting `mail.thread`, `mail.activity.mixin` with fields matching DB schema (name, state selection [draft/submitted/hired/declined], title, module_list, client_industry, submitted_date, job_requirements text, html_content html, hourly_rate float, estimated_hours float, upwork_account_id, contract_id, company_id)
- [ ] 3.8 Create `models/res_config_settings.py` -- Extend `res.config.settings` with 5 fields: `upwork_income_account_id` (Many2one account.account), `upwork_fee_expense_account_id`, `upwork_fee_payable_account_id`, `upwork_auto_create_timesheets` (Boolean), `upwork_auto_create_invoices` (Boolean). Include `action_check_upwork_financial_config()` method

## 4. API Service Layer

- [ ] 4.1 Implement `_get_client(account)` in `upwork_api_service.py` -- Build `python-upwork-oauth2` Client from account tokens with auto-refresh configuration
- [ ] 4.2 Implement `_graphql_query(account, query, variables)` -- Execute GraphQL POST to `https://api.upwork.com/graphql` with error handling and response parsing
- [ ] 4.3 Implement `_refresh_token(account)` -- POST to `https://www.upwork.com/api/v3/oauth2/token` with `grant_type=refresh_token`, update account tokens and expiry
- [ ] 4.4 Implement `fetch_contracts(account)` -- GraphQL query for contracts, return parsed list of contract dicts
- [ ] 4.5 Implement `fetch_timelogs(account, date_from, date_to)` -- Fetch time reports for date range, return parsed time log dicts
- [ ] 4.6 Implement `fetch_earnings(account, date_from, date_to)` -- Fetch earnings/financial reports, return parsed earning dicts
- [ ] 4.7 Implement cron entry points with error handling: iterate active accounts, call fetch methods, perform idempotent upserts using external IDs, handle rate limiting with exponential backoff
- [ ] 4.8 Add logging for all API calls and sync operations using `_logger`

## 5. Controllers (OAuth)

- [ ] 5.1 Create `controllers/upwork_oauth.py` with route `/upwork/oauth/callback` (type='http', auth='user', methods=['GET'])
- [ ] 5.2 Implement callback handler: validate `state` parameter against `oauth_state`, exchange `code` for tokens via POST to token endpoint, store tokens in `upwork.account`, redirect to account form
- [ ] 5.3 Handle error cases: missing state, invalid state, token exchange failure, user not authenticated

## 6. Views and Menus

- [ ] 6.1 Create `views/upwork_account_views.xml` with form view (matching existing `view_upwork_account_form` arch), list view (`view_upwork_account_list`), and search view (`view_upwork_account_search`). XML IDs MUST match `ir_model_data` names
- [ ] 6.2 Create `views/upwork_contract_views.xml` with form (`upwork_contract_view_form`), list (`upwork_contract_view_tree`), and search (`upwork_contract_view_search`) views
- [ ] 6.3 Create `views/upwork_timelog_views.xml` with form (`upwork_timelog_view_form`), list (`upwork_timelog_view_tree`), and pivot (`upwork_timelog_view_pivot`) views
- [ ] 6.4 Create `views/upwork_earning_views.xml` with form (`upwork_earning_view_form`) and list (`upwork_earning_view_tree`) views
- [ ] 6.5 Create `views/upwork_proposal_views.xml` with form (`upwork_proposal_view_form`), list (`upwork_proposal_view_tree`), search (`upwork_proposal_view_search`), and QWeb template (`upwork_proposal_template`) views
- [ ] 6.6 Create `views/upwork_menus.xml` with root menu (`menu_upwork_root`), and sub-menus: contracts (`menu_upwork_contracts`), time logs (`menu_upwork_timelogs`), earnings (`menu_upwork_earnings`), proposals (`menu_upwork_proposals`), accounts (`menu_upwork_accounts`). Include all 10 window actions with matching XML IDs
- [ ] 6.7 Create `views/res_config_settings_views.xml` with `xpath` extension matching existing settings arch (Upwork app with Financial Integration and Automation blocks)
- [ ] 6.8 Create `views/res_partner_views.xml` with `res_partner_view_form_upwork` extension

## 7. Data Files

- [ ] 7.1 Create `data/ir_cron_data.xml` with 4 cron jobs matching existing database records:
  - `ir_cron_upwork_sync_contracts`: model `upwork.api.service`, code `model.cron_sync_contracts()`, interval 4 hours
  - `ir_cron_upwork_sync_timelogs`: model `upwork.api.service`, code `model.cron_sync_timelogs()`, interval 1 day
  - `ir_cron_upwork_sync_earnings`: model `upwork.api.service`, code `model.cron_sync_earnings()`, interval 7 days
  - `ir_cron_upwork_refresh_tokens`: model `upwork.api.service`, code `model.cron_refresh_tokens()`, interval 1 day

## 8. AI Tool Provider

- [ ] 8.1 Create `models/upwork_tool_provider.py` with `upwork.tool.provider` inheriting `loomworks.ai.tool.provider`
- [ ] 8.2 Implement `_get_tool_definitions()` returning tools: `upwork_list_contracts` (data/safe), `upwork_get_earnings_summary` (data/safe), `upwork_list_timelogs` (data/safe), `upwork_list_proposals` (data/safe), `upwork_sync_now` (action/moderate with confirmation)
- [ ] 8.3 Implement tool execution methods: `_execute_list_contracts()`, `_execute_get_earnings_summary()`, `_execute_list_timelogs()`, `_execute_list_proposals()`, `_execute_sync_now()`

## 9. Server Actions

- [ ] 9.1 Define server action `upwork_timelog_action_create_timesheets` (XML ID must match) with code `action = records.action_create_timesheets()` on model `upwork.timelog`
- [ ] 9.2 Define server action `upwork_earning_action_create_invoices` (XML ID must match) with code `action = records.action_create_invoices()` on model `upwork.earning`

## 10. Verification and Testing

- [ ] 10.1 Write unit test `test_upwork_account.py`: test account creation, state transitions, field constraints (unique name per company)
- [ ] 10.2 Write unit test `test_upwork_sync.py`: test contract upsert logic, timelog creation, earning record creation with mocked API responses
- [ ] 10.3 Verify all XML IDs match `ir_model_data` records: cross-reference every view, menu, action, cron, and access record XML ID against the 151 database entries
- [ ] 10.4 Verify ORM field definitions produce identical PostgreSQL schemas (types, constraints, indexes, foreign keys) by comparing `\d` output before and after module upgrade
- [ ] 10.5 Test OAuth2 flow end-to-end (requires Upwork developer credentials): authorization redirect, callback handling, token storage
- [ ] 10.6 Test cron job execution with mocked API responses: verify idempotent upserts, error handling, rate limit backoff
- [ ] 10.7 Test timesheet creation from time logs: verify `account.analytic.line` records are created correctly with proper project/task linkage
- [ ] 10.8 Test invoice creation from earnings: verify `account.move` records with correct line items, fee journal entries, and account mappings
- [ ] 10.9 Install module on test database and verify all menus, views, and actions are accessible
- [ ] 10.10 Run `python -m pytest loomworks_addons/upwork_integration/tests/` and ensure all tests pass
