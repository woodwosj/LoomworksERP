# Specification: loomworks_spreadsheet

Excel-like spreadsheet interface with business intelligence capabilities, integrated with Odoo data sources.

## ADDED Requirements

### Requirement: Spreadsheet Document Management

The system SHALL provide document management for spreadsheet files within Odoo.

Spreadsheet documents MUST support:
- Creation of new blank spreadsheets
- Naming and description
- Folder organization (if documents module installed)
- Tagging for categorization
- Ownership and sharing permissions
- Version tracking

#### Scenario: User creates a new spreadsheet

- **GIVEN** a user with spreadsheet access permissions
- **WHEN** the user clicks "New Spreadsheet" from the Spreadsheet menu
- **THEN** the system creates a `spreadsheet.document` record
- **AND** opens the spreadsheet editor with a blank workbook
- **AND** auto-saves changes every 2 seconds

#### Scenario: User shares spreadsheet with colleagues

- **GIVEN** a spreadsheet owned by User A
- **WHEN** User A sets sharing to "Can Edit" and adds User B
- **THEN** User B can open and modify the spreadsheet
- **AND** changes from both users are visible (with potential for collaboration conflicts)

#### Scenario: User organizes spreadsheets in folders

- **GIVEN** the Documents module is installed
- **WHEN** a user creates a spreadsheet and assigns it to folder "Finance Reports"
- **THEN** the spreadsheet appears in the Documents app under "Finance Reports"
- **AND** can be tagged with labels like "Q1 2026", "Budget"

---

### Requirement: Full Spreadsheet Functionality

The system SHALL provide a full-featured spreadsheet interface comparable to Excel/Google Sheets.

Core features MUST include:
- Multiple sheets (tabs) per document
- Cell formatting (fonts, colors, borders, alignment)
- Number formatting (currency, percentage, date, custom)
- Cell merging and splitting
- Row and column resize, insert, delete, hide
- Copy, paste, cut operations
- Undo/redo with history
- Find and replace
- Cell comments/notes

#### Scenario: User formats cells as currency

- **GIVEN** a spreadsheet with numeric values in column B
- **WHEN** the user selects B2:B100 and applies "Currency" format with USD
- **THEN** all values display with $ symbol and 2 decimal places
- **AND** the format persists when the spreadsheet is saved and reopened

#### Scenario: User creates a multi-sheet workbook

- **GIVEN** a new spreadsheet
- **WHEN** the user clicks "Add Sheet" twice
- **THEN** the workbook has three sheets: "Sheet 1", "Sheet 2", "Sheet 3"
- **AND** the user can rename sheets by double-clicking the tab
- **AND** formulas can reference cells across sheets (e.g., `=Sheet2!A1`)

#### Scenario: User undoes a series of changes

- **GIVEN** a user has made 10 changes to the spreadsheet
- **WHEN** the user presses Ctrl+Z five times
- **THEN** the last five changes are undone in reverse order
- **AND** pressing Ctrl+Y redoes the changes

---

### Requirement: Formula Engine

The system SHALL provide a formula engine supporting common spreadsheet functions.

Minimum supported functions MUST include:
- Math: SUM, AVERAGE, MIN, MAX, COUNT, ROUND, ABS, SQRT
- Text: CONCAT, LEFT, RIGHT, MID, LEN, UPPER, LOWER, TRIM
- Logical: IF, AND, OR, NOT, IFERROR, SWITCH
- Lookup: VLOOKUP, HLOOKUP, INDEX, MATCH, XLOOKUP
- Date: TODAY, NOW, DATE, YEAR, MONTH, DAY, DATEDIF
- Statistical: COUNTIF, SUMIF, AVERAGEIF, STDEV
- Financial: PMT, PV, FV, NPV, IRR

#### Scenario: User calculates sum with SUM function

- **GIVEN** values 10, 20, 30 in cells A1:A3
- **WHEN** the user enters `=SUM(A1:A3)` in cell A4
- **THEN** cell A4 displays 60
- **AND** updates automatically when A1:A3 values change

#### Scenario: User uses VLOOKUP to find product price

- **GIVEN** a product list in columns A (name) and B (price)
- **WHEN** the user enters `=VLOOKUP("Widget",A:B,2,FALSE)` in cell D1
- **THEN** cell D1 displays the price of "Widget" from the list
- **AND** returns #N/A if "Widget" is not found

#### Scenario: User creates nested IF formula

- **GIVEN** a grade value in cell A1
- **WHEN** the user enters `=IF(A1>=90,"A",IF(A1>=80,"B",IF(A1>=70,"C","F")))`
- **THEN** the formula correctly returns the letter grade based on the numeric value

---

### Requirement: Odoo Data Source Integration

The system SHALL allow inserting live data from any Odoo model into spreadsheets.

Data source features MUST include:
- Select any accessible Odoo model
- Choose specific fields to include
- Apply domain filters
- Auto-refresh on document open
- Manual refresh option
- Cell reference to data source values

#### Scenario: User inserts sales order data

- **GIVEN** a user editing a spreadsheet
- **WHEN** the user clicks "Insert Odoo Data" and selects model "Sales Order"
- **AND** chooses fields: Order Reference, Customer, Total, Date
- **AND** filters to orders from the current month
- **THEN** the system inserts a table starting at the selected cell
- **AND** headers row contains field names
- **AND** data rows contain actual sales order data

#### Scenario: Data auto-refreshes on open

- **GIVEN** a spreadsheet with an Odoo data source configured
- **WHEN** a user opens the spreadsheet
- **THEN** the system fetches the latest data from Odoo
- **AND** updates all cells linked to that data source
- **AND** displays a "Last refreshed" timestamp

#### Scenario: User manually refreshes data

- **GIVEN** a spreadsheet with Odoo data that may be stale
- **WHEN** the user clicks "Refresh All Data"
- **THEN** all data sources are re-queried
- **AND** cell values update to reflect current database state
- **AND** formulas referencing data cells recalculate

---

### Requirement: Odoo-Specific Formula Functions

The system SHALL provide custom formula functions for querying Odoo data directly in cells.

Custom functions MUST include:
- `ODOO.DATA(model, domain, fields, row, col)` - Fetch data from model
- `ODOO.PIVOT(pivot_id, row_index, measure)` - Get pivot cell value
- `ODOO.PIVOT.HEADER(pivot_id, row_index)` - Get pivot row header
- `ODOO.COUNT(model, domain)` - Count records matching domain
- `ODOO.SUM(model, domain, field)` - Sum field values matching domain

#### Scenario: User fetches single value with ODOO.DATA

- **GIVEN** a spreadsheet cell
- **WHEN** the user enters `=ODOO.DATA("sale.order",[["state","=","sale"]],"amount_total",0,0)`
- **THEN** the cell displays the total amount of the first confirmed sale order
- **AND** the value updates when data is refreshed

#### Scenario: User counts records with ODOO.COUNT

- **GIVEN** a dashboard spreadsheet
- **WHEN** the user enters `=ODOO.COUNT("crm.lead",[["stage_id.is_won","=",true]])`
- **THEN** the cell displays the count of won opportunities
- **AND** serves as a KPI that updates on refresh

#### Scenario: Formula handles Odoo query errors

- **GIVEN** an ODOO.DATA formula with an invalid model name
- **WHEN** the formula is evaluated
- **THEN** the cell displays "#ERROR" or a descriptive error message
- **AND** does not crash the spreadsheet application

---

### Requirement: Dynamic Pivot Tables

The system SHALL support pivot tables that aggregate data from Odoo models.

Pivot table features MUST include:
- Select source model and domain filter
- Configure row groupings (single or multi-level)
- Configure column groupings
- Select measures with aggregation functions (sum, avg, count, min, max)
- Date grouping granularity (day, week, month, quarter, year)
- Row and column totals
- Grand total

#### Scenario: User creates pivot table of sales by product category and month

- **GIVEN** a user editing a spreadsheet
- **WHEN** the user inserts a pivot table with:
  - Model: Sale Order Line
  - Row Group: Product Category
  - Column Group: Order Date (by Month)
  - Measure: Quantity (Sum)
- **THEN** the spreadsheet displays a pivot table with categories as rows
- **AND** months as columns
- **AND** quantity sums in each cell

#### Scenario: Pivot table updates when underlying data changes

- **GIVEN** a pivot table showing sales totals
- **WHEN** a new sale order is confirmed in Odoo
- **AND** the user refreshes the spreadsheet
- **THEN** the pivot table includes the new order in aggregations
- **AND** totals update accordingly

#### Scenario: User drills down into pivot cell

- **GIVEN** a pivot cell showing "Category: Electronics, Month: January, Total: 150"
- **WHEN** the user double-clicks the cell
- **THEN** the system shows the underlying records that make up that total
- **OR** creates a filtered list view in Odoo showing those records

---

### Requirement: Chart Visualization

The system SHALL support creating charts from spreadsheet data and pivot tables.

Supported chart types MUST include:
- Bar chart (vertical and horizontal)
- Line chart
- Pie chart
- Area chart
- Scatter plot
- Combo chart (bar + line)

Chart configuration MUST include:
- Data range selection (or pivot source)
- Title and subtitle
- Legend position and visibility
- Axis labels and scaling
- Color customization
- Stacked option for bar/area charts

#### Scenario: User creates bar chart from data range

- **GIVEN** a spreadsheet with data in A1:B10 (categories and values)
- **WHEN** the user selects the range and inserts a bar chart
- **AND** sets title "Sales by Region"
- **THEN** a bar chart appears showing categories on X-axis and values as bar heights
- **AND** the chart is embedded in the spreadsheet

#### Scenario: User creates chart from pivot table

- **GIVEN** a pivot table showing monthly sales by category
- **WHEN** the user clicks "Create Chart" on the pivot
- **AND** selects "Line Chart"
- **THEN** a line chart is created with months on X-axis
- **AND** separate lines for each category
- **AND** the chart updates when pivot data refreshes

#### Scenario: User customizes chart appearance

- **GIVEN** a bar chart in the spreadsheet
- **WHEN** the user opens chart configuration
- **AND** changes colors to company brand colors
- **AND** enables data labels on bars
- **AND** repositions legend to bottom
- **THEN** the chart renders with all customizations applied

---

### Requirement: Spreadsheet Templates

The system SHALL support creating and using spreadsheet templates for common use cases.

Template features MUST include:
- Save spreadsheet as template
- Template library accessible to all users
- Create new spreadsheet from template
- Templates include: structure, formatting, formulas, data source configurations

#### Scenario: User saves spreadsheet as template

- **GIVEN** a configured spreadsheet with pivot tables and charts
- **WHEN** the user clicks "Save as Template" and enters name "Monthly Sales Report"
- **THEN** the template is saved without current data values
- **AND** appears in the template library for future use

#### Scenario: User creates spreadsheet from template

- **GIVEN** a template "Monthly Sales Report" exists
- **WHEN** a user creates a new spreadsheet and selects this template
- **THEN** the new spreadsheet has the same structure, formatting, and data source configurations
- **AND** data sources are refreshed to show current data
- **AND** the new spreadsheet is an independent copy

---

### Requirement: Export and Import

The system SHALL support exporting spreadsheets to standard formats and importing from Excel.

Export formats MUST include:
- XLSX (Excel format)
- CSV (for single sheet)
- PDF (with charts and formatting)

Import capabilities MUST include:
- XLSX file upload
- Parsing of formulas (where compatible)
- Preservation of formatting
- Data import without overwriting existing

#### Scenario: User exports spreadsheet to Excel

- **GIVEN** a spreadsheet with data, formulas, and charts
- **WHEN** the user clicks "Download as Excel"
- **THEN** the browser downloads an XLSX file
- **AND** the file opens correctly in Microsoft Excel
- **AND** formulas are preserved (where function names match)

#### Scenario: User imports Excel file

- **GIVEN** an Excel file with multiple sheets and data
- **WHEN** the user uploads the file to create a new spreadsheet
- **THEN** all sheets are imported with data and basic formatting
- **AND** Odoo data sources are NOT automatically created (manual configuration needed)
- **AND** unsupported features are logged with warnings

#### Scenario: User exports to PDF

- **GIVEN** a spreadsheet with a chart and formatted data
- **WHEN** the user exports to PDF
- **THEN** the PDF includes all visible sheets
- **AND** charts render as images
- **AND** formatting matches screen display
- **AND** page breaks are applied appropriately

---

### Requirement: Spreadsheet Access Control

The system SHALL enforce access control for spreadsheet documents and data sources.

Access levels MUST include:
- **Private**: Only owner can view/edit
- **Read Only**: Shared users can view but not edit
- **Can Edit**: Shared users can view and edit

Data access MUST respect:
- Odoo model access rights for data sources
- Record rules for filtered data
- Field-level access restrictions

#### Scenario: Shared user cannot see restricted data

- **GIVEN** a spreadsheet with data source from "HR Employee Salary" model
- **AND** the spreadsheet is shared with User B who lacks HR Manager access
- **WHEN** User B opens the spreadsheet
- **THEN** salary data cells show "#ACCESS" or are empty
- **AND** non-sensitive data remains visible

#### Scenario: User tries to edit read-only spreadsheet

- **GIVEN** a spreadsheet shared as "Read Only" with User B
- **WHEN** User B opens the spreadsheet
- **THEN** all editing features are disabled
- **AND** a banner indicates "View Only - You cannot edit this document"
- **AND** User B can still export or duplicate the spreadsheet

---

### Requirement: Performance for Large Datasets

The system SHALL handle large datasets efficiently without browser performance degradation.

Performance requirements:
- Data sources limited to 10,000 rows by default (configurable)
- Lazy loading for large ranges
- Pagination for data source queries
- Warning when approaching limits

#### Scenario: Data source exceeds row limit

- **GIVEN** a data source query that would return 50,000 records
- **WHEN** the user inserts this data source
- **THEN** the system displays a warning about the row limit
- **AND** suggests adding filters to reduce data volume
- **AND** inserts only the first 10,000 rows if user proceeds

#### Scenario: Large spreadsheet renders progressively

- **GIVEN** a spreadsheet with 100 columns and 5,000 rows of data
- **WHEN** the user opens the spreadsheet
- **THEN** the visible viewport renders immediately
- **AND** scrolling loads additional rows/columns on demand
- **AND** total load time is under 3 seconds

---

### Requirement: AI Agent Integration

The system SHALL expose spreadsheet operations to AI agents via MCP tools.

AI capabilities MUST include:
- Create new spreadsheets
- Add data sources with specified configurations
- Create pivot tables
- Generate charts
- Read and write cell values
- Execute formulas

#### Scenario: AI creates sales analysis spreadsheet

- **GIVEN** a user asks the AI "Create a spreadsheet showing this quarter's sales by region"
- **WHEN** the AI processes the request
- **THEN** the AI uses MCP tools to:
  - Create a new spreadsheet document
  - Add a data source for sale.order with date filter
  - Create a pivot table grouped by region
  - Generate a bar chart of the results
- **AND** returns the spreadsheet link to the user

#### Scenario: AI answers question using spreadsheet data

- **GIVEN** a spreadsheet with financial data
- **AND** a user asks "What was our total revenue in January?"
- **WHEN** the AI analyzes the question
- **THEN** the AI can query the spreadsheet data source
- **OR** read the relevant cells
- **AND** provides the answer with source reference
