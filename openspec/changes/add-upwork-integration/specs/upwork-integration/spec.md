## ADDED Requirements

### Requirement: Upwork OAuth2 Authentication

The system SHALL provide OAuth2 authorization code flow for connecting Upwork accounts to Loomworks ERP. The system MUST store OAuth2 credentials (client_id, client_secret, access_token, refresh_token) in the `upwork.account` model. The system MUST generate a CSRF state token for each authorization attempt and validate it on callback. The system MUST support token refresh to maintain persistent API access. The OAuth2 callback controller MUST handle error cases (invalid state, token exchange failure) and display meaningful error messages.

#### Scenario: Successful Upwork account authorization

- **WHEN** a user with Upwork Manager permissions enters a valid client_id and client_secret, then clicks "Connect to Upwork"
- **THEN** the system generates an oauth_state token, sets the account state to "connecting", and redirects the user to the Upwork authorization URL with correct parameters (client_id, response_type=code, redirect_uri, state)

#### Scenario: OAuth callback processes authorization code

- **WHEN** Upwork redirects to `/upwork/oauth/callback` with a valid authorization code and matching state token
- **THEN** the system exchanges the code for access and refresh tokens via POST to `https://www.upwork.com/api/v3/oauth2/token`, stores the tokens in the upwork.account record, sets the state to "connected", and redirects the user to the account form view

#### Scenario: OAuth callback with invalid state

- **WHEN** the OAuth callback receives a state parameter that does not match any upwork.account oauth_state value
- **THEN** the system rejects the callback, does not store any tokens, and displays an error message to the user

#### Scenario: Token refresh before expiry

- **WHEN** the daily token refresh cron job runs and an account's access token is approaching expiry
- **THEN** the system uses the refresh token to obtain a new access token via the token endpoint, updates the stored tokens and expiry timestamp, and logs the refresh operation

### Requirement: Upwork Account Management

The system SHALL provide a dedicated Odoo model (`upwork.account`) for managing Upwork API connections. Each account MUST be uniquely identified by name within a company. The account form MUST display connection status, provide connect/disconnect/test actions, and show OAuth2 configuration (restricted to system administrators). The model MUST inherit `mail.thread` and `mail.activity.mixin` for audit logging and activity scheduling.

#### Scenario: Create new Upwork account

- **WHEN** a user with Upwork Manager permissions creates a new upwork.account record with a name, client_id, and client_secret
- **THEN** the system creates the record with state "draft", is_connected=False, and the account appears in the Upwork Accounts list view

#### Scenario: Test existing connection

- **WHEN** a user clicks "Test Connection" on a connected Upwork account
- **THEN** the system makes a test API call to Upwork, and if successful, confirms the connection is active; if the call fails, the system sets the state to "error" and records the error message in last_error

#### Scenario: Disconnect Upwork account

- **WHEN** a user clicks "Disconnect" on a connected account and confirms the action
- **THEN** the system clears the access_token, refresh_token, and token_expiry fields, sets the state to "draft", and sets is_connected to False

### Requirement: Contract Management

The system SHALL synchronize Upwork contracts into the `upwork.contract` model via scheduled cron jobs. Each contract MUST be uniquely identified by its external Upwork contract ID within an account. Contracts MUST be classifiable as hourly or fixed-price and trackable by state (active, paused, ended). Contracts MUST support linking to an Odoo partner (client) and an Odoo project. The model MUST inherit `mail.thread` and `mail.activity.mixin`.

#### Scenario: Sync creates new contract

- **WHEN** the contract sync cron job runs and fetches a contract from Upwork that does not exist in the database
- **THEN** the system creates a new `upwork.contract` record with the contract's title, type, state, dates, hourly rate, and external ID, linked to the appropriate upwork.account

#### Scenario: Sync updates existing contract

- **WHEN** the contract sync cron job fetches a contract whose `upwork_contract_id` already exists for the given account
- **THEN** the system updates the existing record with the latest state, dates, and rate information without creating a duplicate

#### Scenario: Contract linked to Odoo partner and project

- **WHEN** a contract is synced and the contract's client name matches an existing res.partner record
- **THEN** the system links the contract to that partner via the partner_id field; the user can also manually link the contract to an Odoo project via the project_id field

### Requirement: Time Log Synchronization and Timesheet Creation

The system SHALL synchronize Upwork time logs into the `upwork.timelog` model via a daily cron job. Each time log entry MUST record the date, tracked hours, manual hours, total hours, and work memo. The system MUST support creating Odoo timesheets (`account.analytic.line`) from time logs, either manually via a server action or automatically based on a configuration toggle. Each time log MUST be unique per contract and date.

#### Scenario: Daily time log sync

- **WHEN** the time log sync cron job runs for an active, connected Upwork account
- **THEN** the system fetches time reports from the Upwork API for the recent period, creates or updates `upwork.timelog` records with tracked_hours, manual_hours, total_hours, date, and memo for each contract

#### Scenario: Manual timesheet creation

- **WHEN** a user selects one or more time log records and triggers the "Create Timesheets" server action
- **THEN** the system creates `account.analytic.line` records for each time log that does not already have a linked timesheet, using the contract's linked project, the time log date, hours, and memo

#### Scenario: Automatic timesheet creation

- **WHEN** the `upwork_auto_create_timesheets` setting is enabled and the time log sync completes
- **THEN** the system automatically creates Odoo timesheets for all newly synced time logs that have a linked contract with a project_id set

#### Scenario: Duplicate time log prevention

- **WHEN** the sync job encounters a time log for a contract and date combination that already exists
- **THEN** the system updates the existing record rather than creating a duplicate, enforced by the unique constraint on (contract_id, date)

### Requirement: Earnings Tracking and Invoice Creation

The system SHALL synchronize Upwork earnings into the `upwork.earning` model via a weekly cron job. Each earning record MUST capture the gross amount, Upwork service fee, fee percentage, and net amount. The system MUST support creating Odoo customer invoices (`account.move`) from earnings, either manually or automatically. Fee journal entries MUST be created when a fee expense account is configured. Earnings MUST be linked to their parent contract and support a billing period (period_start, period_end).

#### Scenario: Weekly earnings sync

- **WHEN** the earnings sync cron job runs for an active, connected Upwork account
- **THEN** the system fetches financial reports from the Upwork API, creates or updates `upwork.earning` records with gross_amount, upwork_fee, upwork_fee_percent, net_amount, total_hours, date, and billing period

#### Scenario: Manual invoice creation

- **WHEN** a user selects one or more earning records and triggers the "Create Invoices" server action
- **THEN** the system creates draft `account.move` records (type: out_invoice) for each earning that does not already have a linked invoice, using the configured income account, the earning's gross amount as the invoice line, and the contract's partner as the invoice customer

#### Scenario: Upwork fee journal entry

- **WHEN** an invoice is created from an earning and the `upwork_fee_expense_account_id` and `upwork_fee_payable_account_id` settings are configured
- **THEN** the system creates a separate journal entry recording the Upwork fee as an expense, debiting the fee expense account and crediting the fee payable account, and links it to the earning via journal_entry_id

#### Scenario: Automatic invoice creation

- **WHEN** the `upwork_auto_create_invoices` setting is enabled and the earnings sync completes
- **THEN** the system automatically creates draft invoices for all newly synced earnings

### Requirement: Milestone Tracking

The system SHALL provide a `upwork.milestone` model for tracking fixed-price contract milestones. Each milestone MUST have a name, amount, due date, and state (pending, active, completed, paid). Milestones MUST be linked to their parent contract.

#### Scenario: Milestone creation for fixed-price contract

- **WHEN** a fixed-price contract is synced and contains milestone data
- **THEN** the system creates `upwork.milestone` records with the milestone name, amount, due date, and state linked to the contract

#### Scenario: Milestone state progression

- **WHEN** a milestone's state changes on Upwork (e.g., from pending to active to completed to paid)
- **THEN** the system updates the milestone's state field during the next contract sync

### Requirement: Proposal Pipeline

The system SHALL provide a `upwork.proposal` model for managing the Upwork proposal pipeline. Each proposal MUST track the job title, requirements, proposed rate, estimated hours, submission date, and state (draft, submitted, hired, declined). Proposals MUST support rich HTML content for the proposal body. When a proposal results in a hire, it MUST be linkable to the resulting contract. The model MUST inherit `mail.thread` and `mail.activity.mixin`.

#### Scenario: Create and track a proposal

- **WHEN** a user creates a new proposal record with a job title, requirements, proposed rate, and estimated hours
- **THEN** the system creates the proposal in "draft" state and it appears in the Proposals list view

#### Scenario: Proposal status transitions

- **WHEN** a proposal's state changes (draft to submitted, submitted to hired or declined)
- **THEN** the system updates the state field and logs the change in the chatter via mail.thread

#### Scenario: Proposal hired and linked to contract

- **WHEN** a proposal's state is set to "hired" and a matching contract exists
- **THEN** the user can link the proposal to the resulting contract via the contract_id field

### Requirement: Configuration Settings

The system SHALL extend `res.config.settings` with Upwork-specific configuration fields. The settings MUST include: income account (for invoice line items), fee expense account (for recording Upwork fees), fee payable account (for fee liabilities), auto-create timesheets toggle, and auto-create invoices toggle. The settings MUST be accessible via a dedicated Upwork settings page in the general configuration.

#### Scenario: Configure financial accounts

- **WHEN** an administrator navigates to Settings and opens the Upwork Integration section
- **THEN** the system displays fields for Income Account, Fee Expense Account, and Fee Payable Account, allowing the user to select from existing chart of accounts entries

#### Scenario: Enable automatic timesheet creation

- **WHEN** an administrator enables the "Auto-create Timesheets" toggle in Upwork settings
- **THEN** the system stores this preference and uses it during time log sync to automatically generate Odoo timesheets

#### Scenario: Validate financial configuration

- **WHEN** an administrator clicks "Check Financial Configuration" in the Upwork settings
- **THEN** the system validates that the required accounts are configured and displays a success or warning notification

### Requirement: AI Tool Integration

The system SHALL provide an AI tool provider (`upwork.tool.provider`) that registers Upwork-related tools with the Loomworks AI framework. The tool provider MUST inherit from `loomworks.ai.tool.provider` and implement `_get_tool_definitions()`. Tools MUST enable AI agents to query Upwork contracts, earnings, time logs, and proposals, and to trigger manual sync operations.

#### Scenario: AI queries active contracts

- **WHEN** a user asks the AI agent "What are my active Upwork contracts?"
- **THEN** the AI uses the `upwork_list_contracts` tool to query `upwork.contract` records with state "active" and returns a formatted list of contract names, types, and hourly rates

#### Scenario: AI provides earnings summary

- **WHEN** a user asks the AI agent "How much did we earn on Upwork last month?"
- **THEN** the AI uses the `upwork_get_earnings_summary` tool to aggregate earnings for the requested period and returns the total gross amount, total fees, and net amount

#### Scenario: AI triggers manual sync

- **WHEN** a user asks the AI agent to "sync my Upwork data now"
- **THEN** the AI uses the `upwork_sync_now` tool (with confirmation) to trigger an immediate sync of contracts, time logs, and earnings for all active accounts, and reports the sync results

### Requirement: Automated Synchronization

The system SHALL provide 4 scheduled cron jobs for automated Upwork data synchronization. The contract sync MUST run every 4 hours. The time log sync MUST run daily. The earnings sync MUST run weekly. The token refresh MUST run daily. All cron jobs MUST iterate over active, connected Upwork accounts and handle errors gracefully without stopping the entire batch. Sync operations MUST be idempotent using external Upwork IDs as deduplication keys.

#### Scenario: Contract sync cron executes successfully

- **WHEN** the "Upwork: Sync Contracts" cron job fires at its 4-hour interval
- **THEN** the system iterates over all upwork.account records where state is "connected" and sync_enabled is True, fetches contracts from each account, performs idempotent upserts, and updates the account's last_sync timestamp

#### Scenario: Sync handles API errors gracefully

- **WHEN** a sync cron job encounters an API error (rate limit, network timeout, authentication failure) for one account
- **THEN** the system logs the error, sets the account's last_error field with the error message, and continues processing remaining accounts without aborting the batch

#### Scenario: Token refresh prevents expiration

- **WHEN** the daily token refresh cron job runs
- **THEN** the system refreshes OAuth2 tokens for all connected accounts, updating the access_token, refresh_token, and token_expiry fields, ensuring uninterrupted API access
