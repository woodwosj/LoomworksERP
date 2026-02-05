# Change: Phase 4 Dashboard System

## Why

Business users need visual, interactive dashboards to monitor KPIs, trends, and operational metrics without writing code or SQL. Traditional Odoo dashboards are limited to static configurations. The Loomworks Dashboard System provides a modern drag-drop builder with AI-powered dashboard generation, enabling users to create custom visualizations from natural language descriptions. This differentiates Loomworks ERP by making business intelligence accessible to non-technical users.

## What Changes

- **NEW** `loomworks_dashboard` module with complete dashboard building infrastructure
- **NEW** `dashboard.board` model for storing dashboard configurations (layout, filters, metadata)
- **NEW** `dashboard.widget` model for individual widget definitions (type, data source, styling)
- **NEW** `dashboard.data_source` model for connecting widgets to Odoo models and computed metrics
- **NEW** Owl-React bridge component for embedding React canvas in Odoo UI
- **NEW** React component library: DashboardCanvas, ChartNode, KPINode, TableNode, FilterNode
- **NEW** AI dashboard generation endpoint using Claude for natural language to dashboard conversion
- **NEW** Real-time data refresh infrastructure with configurable polling and WebSocket support
- **NEW** Asset bundling configuration for React dependencies in Odoo

## Impact

- Affected specs: `loomworks-dashboard` (new capability)
- Affected code:
  - `/loomworks_addons/loomworks_dashboard/` (new module)
  - Asset bundles: `web.assets_backend` (React bundle), `web.assets_common` (shared utilities)
- Dependencies:
  - Requires `loomworks_core` for branding
  - Requires `loomworks_ai` for AI generation features (optional, graceful degradation)
  - Node.js packages: `@xyflow/react`, `react`, `react-dom`, `recharts`, `@tremor/react`, `gridstack`

### Runtime Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| **Node.js** | >= 20.0.0 (LTS) | Required for React 18+ builds and Odoo asset bundling. Node.js 20 LTS recommended (EOL: April 2026). Node.js 22 LTS also supported. |
| **npm** | >= 9.0.0 | Package management |
| **Python** | >= 3.10 | Odoo v18 requirement |
| **PostgreSQL** | >= 15 | Required for WAL features |

**Rationale for Node.js 20+:**
- React 18+ and associated tooling require modern Node.js features
- Node.js 18 LTS reached end-of-life on April 30, 2025
- Node.js 20 LTS provides security updates until April 2026
- Consistent with Phase 3.1 (Studio/Spreadsheet) requirements

## Scope

This proposal covers **Phase 4 (Weeks 31-38)** of the implementation plan:
1. Create `loomworks_dashboard` module structure
2. Implement backend models for dashboard persistence
3. Build Owl-React bridge for React component embedding
4. Develop React dashboard canvas with drag-drop
5. Implement widget node types (Chart, KPI, Table, Filter)
6. Create data connectors to Odoo models
7. Add AI dashboard generation capability
8. Configure asset bundling and deployment

---

## Technical Design

### 1. Module Structure

```
loomworks_addons/loomworks_dashboard/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── dashboard_board.py          # Main dashboard model
│   ├── dashboard_widget.py         # Individual widget definitions
│   ├── dashboard_data_source.py    # Data connectors to Odoo models
│   └── dashboard_template.py       # Pre-built dashboard templates
├── controllers/
│   ├── __init__.py
│   ├── dashboard_controller.py     # REST API for dashboard CRUD
│   └── data_controller.py          # Data fetching endpoints
├── views/
│   ├── dashboard_views.xml         # Odoo tree/form views for admin
│   ├── dashboard_action.xml        # Client action to launch React canvas
│   └── menu.xml                    # Navigation menu entries
├── security/
│   ├── ir.model.access.csv         # Model-level permissions
│   └── security.xml                # Record rules for multi-tenancy
├── data/
│   ├── dashboard_templates.xml     # Pre-built dashboard templates
│   └── demo_dashboards.xml         # Demo data for testing
├── static/
│   ├── src/
│   │   ├── components/             # Owl components
│   │   │   ├── react_bridge.js     # Owl-React bridge component
│   │   │   └── dashboard_launcher.xml
│   │   ├── dashboard/              # React components
│   │   │   ├── index.jsx           # Entry point
│   │   │   ├── DashboardCanvas.jsx # Main canvas container
│   │   │   ├── nodes/
│   │   │   │   ├── index.js        # Node type exports
│   │   │   │   ├── ChartNode.jsx   # Chart visualization node
│   │   │   │   ├── KPINode.jsx     # KPI metric node
│   │   │   │   ├── TableNode.jsx   # Data table node
│   │   │   │   └── FilterNode.jsx  # Filter control node
│   │   │   ├── panels/
│   │   │   │   ├── WidgetToolbox.jsx    # Sidebar with draggable widgets
│   │   │   │   ├── PropertyPanel.jsx    # Widget configuration panel
│   │   │   │   └── DataSourcePanel.jsx  # Data source selector
│   │   │   ├── hooks/
│   │   │   │   ├── useOdooData.js       # Fetch data from Odoo
│   │   │   │   ├── useDashboardState.js # Dashboard state management
│   │   │   │   └── useRealTimeUpdates.js # Polling/WebSocket logic
│   │   │   └── utils/
│   │   │       ├── chartUtils.js        # Chart configuration helpers
│   │   │       └── dataTransform.js     # Data transformation utilities
│   │   ├── scss/
│   │   │   └── dashboard.scss
│   │   └── xml/
│   │       └── dashboard_templates.xml
│   └── lib/                        # Vendored/bundled dependencies
│       └── README.md               # Build instructions
└── tests/
    ├── __init__.py
    ├── test_dashboard_board.py
    ├── test_dashboard_widget.py
    └── test_data_source.py
```

### 2. Backend Models

#### 2.1 Dashboard Board Model (`dashboard_board.py`)

```python
from odoo import models, fields, api
import json

class DashboardBoard(models.Model):
    _name = 'dashboard.board'
    _description = 'Dashboard Board'
    _order = 'sequence, name'

    name = fields.Char(string='Dashboard Name', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    # Ownership and sharing
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user)
    is_public = fields.Boolean(string='Public Dashboard', default=False)
    shared_user_ids = fields.Many2many('res.users', string='Shared With')
    shared_group_ids = fields.Many2many('res.groups', string='Shared With Groups')

    # Layout configuration (React Flow serialization)
    layout_config = fields.Text(
        string='Layout Configuration',
        help='JSON serialization of React Flow nodes and edges'
    )
    grid_config = fields.Text(
        string='Grid Configuration',
        help='JSON serialization of Gridstack widget positions'
    )

    # Canvas settings
    canvas_width = fields.Integer(string='Canvas Width', default=12)
    canvas_zoom = fields.Float(string='Default Zoom', default=1.0)
    background_color = fields.Char(string='Background Color', default='#f5f5f5')

    # Refresh settings
    auto_refresh = fields.Boolean(string='Auto Refresh', default=False)
    refresh_interval = fields.Integer(
        string='Refresh Interval (seconds)',
        default=60,
        help='Minimum 10 seconds'
    )

    # Widgets relationship
    widget_ids = fields.One2many('dashboard.widget', 'board_id', string='Widgets')

    # AI Generation metadata
    ai_generated = fields.Boolean(string='AI Generated', default=False)
    ai_prompt = fields.Text(string='Original AI Prompt')

    # Template reference
    template_id = fields.Many2one('dashboard.template', string='Based On Template')

    @api.model
    def get_dashboard_data(self, dashboard_id):
        """Fetch complete dashboard data for React canvas rendering."""
        dashboard = self.browse(dashboard_id)
        if not dashboard.exists():
            return {'error': 'Dashboard not found'}

        # Check access
        if not dashboard.is_public and dashboard.user_id != self.env.user:
            if self.env.user not in dashboard.shared_user_ids:
                if not any(g in dashboard.shared_group_ids for g in self.env.user.groups_id):
                    return {'error': 'Access denied'}

        return {
            'id': dashboard.id,
            'name': dashboard.name,
            'layout': json.loads(dashboard.layout_config or '{"nodes":[],"edges":[]}'),
            'grid': json.loads(dashboard.grid_config or '[]'),
            'settings': {
                'width': dashboard.canvas_width,
                'zoom': dashboard.canvas_zoom,
                'background': dashboard.background_color,
                'autoRefresh': dashboard.auto_refresh,
                'refreshInterval': max(dashboard.refresh_interval, 10),
            },
            'widgets': [w.get_widget_data() for w in dashboard.widget_ids],
        }

    def save_layout(self, layout_data, grid_data=None):
        """Save React Flow layout and optionally Gridstack positions."""
        self.ensure_one()
        vals = {'layout_config': json.dumps(layout_data)}
        if grid_data:
            vals['grid_config'] = json.dumps(grid_data)
        self.write(vals)
        return True
```

#### 2.2 Dashboard Widget Model (`dashboard_widget.py`)

```python
from odoo import models, fields, api
import json

class DashboardWidget(models.Model):
    _name = 'dashboard.widget'
    _description = 'Dashboard Widget'
    _order = 'sequence'

    name = fields.Char(string='Widget Name', required=True)
    board_id = fields.Many2one('dashboard.board', string='Dashboard', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    # Widget type
    widget_type = fields.Selection([
        ('chart_line', 'Line Chart'),
        ('chart_bar', 'Bar Chart'),
        ('chart_pie', 'Pie Chart'),
        ('chart_area', 'Area Chart'),
        ('chart_composed', 'Composed Chart'),
        ('kpi', 'KPI Card'),
        ('table', 'Data Table'),
        ('filter', 'Filter Control'),
        ('text', 'Text/Markdown'),
        ('gauge', 'Gauge'),
    ], string='Widget Type', required=True)

    # Position (React Flow node position)
    node_id = fields.Char(string='React Flow Node ID')
    position_x = fields.Float(string='X Position', default=0)
    position_y = fields.Float(string='Y Position', default=0)

    # Size (Gridstack compatible)
    width = fields.Integer(string='Width (grid units)', default=4)
    height = fields.Integer(string='Height (grid units)', default=3)
    min_width = fields.Integer(string='Min Width', default=2)
    min_height = fields.Integer(string='Min Height', default=2)

    # Data source
    data_source_id = fields.Many2one('dashboard.data_source', string='Data Source')

    # Widget configuration (JSON)
    config = fields.Text(
        string='Widget Configuration',
        help='JSON configuration for the widget (colors, labels, axes, etc.)'
    )

    # Styling
    background_color = fields.Char(string='Background', default='#ffffff')
    border_radius = fields.Integer(string='Border Radius', default=8)
    shadow = fields.Boolean(string='Show Shadow', default=True)

    # Chart-specific fields
    chart_colors = fields.Text(string='Chart Colors', help='JSON array of hex colors')
    show_legend = fields.Boolean(string='Show Legend', default=True)
    show_grid = fields.Boolean(string='Show Grid', default=True)

    # KPI-specific fields
    kpi_value_field = fields.Char(string='Value Field')
    kpi_comparison_field = fields.Char(string='Comparison Field')
    kpi_format = fields.Selection([
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('percent', 'Percentage'),
    ], string='KPI Format', default='number')
    kpi_trend_positive = fields.Selection([
        ('up', 'Up is Good'),
        ('down', 'Down is Good'),
        ('neutral', 'Neutral'),
    ], string='Trend Interpretation', default='up')

    # Table-specific fields
    table_columns = fields.Text(string='Table Columns', help='JSON array of column definitions')
    table_page_size = fields.Integer(string='Page Size', default=10)
    table_sortable = fields.Boolean(string='Sortable', default=True)

    # Filter-specific fields
    filter_target_widgets = fields.Many2many(
        'dashboard.widget',
        'dashboard_widget_filter_rel',
        'filter_widget_id',
        'target_widget_id',
        string='Affects Widgets'
    )
    filter_field = fields.Char(string='Filter Field')
    filter_type = fields.Selection([
        ('select', 'Dropdown'),
        ('multiselect', 'Multi-Select'),
        ('date_range', 'Date Range'),
        ('number_range', 'Number Range'),
        ('search', 'Search Text'),
    ], string='Filter Type', default='select')

    def get_widget_data(self):
        """Get widget data for React rendering."""
        self.ensure_one()
        return {
            'id': self.id,
            'nodeId': self.node_id,
            'name': self.name,
            'type': self.widget_type,
            'position': {'x': self.position_x, 'y': self.position_y},
            'size': {
                'width': self.width,
                'height': self.height,
                'minWidth': self.min_width,
                'minHeight': self.min_height,
            },
            'dataSourceId': self.data_source_id.id if self.data_source_id else None,
            'config': json.loads(self.config or '{}'),
            'style': {
                'background': self.background_color,
                'borderRadius': self.border_radius,
                'shadow': self.shadow,
            },
            'chartConfig': {
                'colors': json.loads(self.chart_colors or '[]'),
                'showLegend': self.show_legend,
                'showGrid': self.show_grid,
            } if 'chart' in self.widget_type else None,
            'kpiConfig': {
                'valueField': self.kpi_value_field,
                'comparisonField': self.kpi_comparison_field,
                'format': self.kpi_format,
                'trendPositive': self.kpi_trend_positive,
            } if self.widget_type == 'kpi' else None,
            'tableConfig': {
                'columns': json.loads(self.table_columns or '[]'),
                'pageSize': self.table_page_size,
                'sortable': self.table_sortable,
            } if self.widget_type == 'table' else None,
            'filterConfig': {
                'targetWidgetIds': self.filter_target_widgets.ids,
                'field': self.filter_field,
                'type': self.filter_type,
            } if self.widget_type == 'filter' else None,
        }
```

#### 2.3 Data Source Model (`dashboard_data_source.py`)

```python
from odoo import models, fields, api
from odoo.exceptions import UserError
import json

class DashboardDataSource(models.Model):
    _name = 'dashboard.data_source'
    _description = 'Dashboard Data Source'
    _order = 'name'

    name = fields.Char(string='Data Source Name', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    # Source type
    source_type = fields.Selection([
        ('model', 'Odoo Model'),
        ('sql', 'SQL Query'),
        ('api', 'External API'),
        ('computed', 'Computed/Aggregated'),
    ], string='Source Type', required=True, default='model')

    # Model-based source
    model_id = fields.Many2one('ir.model', string='Model', domain="[('transient','=',False)]")
    model_name = fields.Char(related='model_id.model', string='Model Name', store=True)
    domain = fields.Text(string='Filter Domain', default='[]', help='Odoo domain filter')

    # Field selection
    field_ids = fields.Many2many('ir.model.fields', string='Fields to Include')

    # Grouping and aggregation
    group_by_field = fields.Many2one('ir.model.fields', string='Group By')
    date_field = fields.Many2one('ir.model.fields', string='Date Field', domain="[('ttype','in',['date','datetime'])]")
    date_granularity = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year'),
    ], string='Date Granularity', default='month')

    # Aggregations
    aggregations = fields.Text(
        string='Aggregations',
        help='JSON array of {field, function} objects. Functions: sum, avg, count, min, max'
    )

    # SQL-based source (admin only)
    sql_query = fields.Text(string='SQL Query', help='Raw SQL query (use with caution)')

    # API-based source
    api_url = fields.Char(string='API URL')
    api_method = fields.Selection([('GET', 'GET'), ('POST', 'POST')], default='GET')
    api_headers = fields.Text(string='API Headers', help='JSON object')
    api_body = fields.Text(string='API Body', help='JSON object for POST requests')

    # Computed source
    compute_method = fields.Char(string='Compute Method', help='Method name on dashboard.data_source')

    # Caching
    cache_enabled = fields.Boolean(string='Enable Cache', default=True)
    cache_timeout = fields.Integer(string='Cache Timeout (seconds)', default=300)

    # Limits
    record_limit = fields.Integer(string='Record Limit', default=1000)

    @api.model
    def fetch_data(self, data_source_id, filters=None):
        """Fetch data from the configured source."""
        source = self.browse(data_source_id)
        if not source.exists():
            return {'error': 'Data source not found'}

        filters = filters or {}

        if source.source_type == 'model':
            return source._fetch_model_data(filters)
        elif source.source_type == 'sql':
            return source._fetch_sql_data(filters)
        elif source.source_type == 'api':
            return source._fetch_api_data(filters)
        elif source.source_type == 'computed':
            return source._fetch_computed_data(filters)

        return {'error': 'Unknown source type'}

    def _fetch_model_data(self, filters):
        """Fetch data from Odoo model with grouping/aggregation."""
        self.ensure_one()
        if not self.model_name:
            return {'error': 'No model configured'}

        Model = self.env[self.model_name]
        domain = json.loads(self.domain or '[]')

        # Apply dynamic filters
        for field, value in filters.items():
            if isinstance(value, list) and len(value) == 2:
                domain.append((field, '>=', value[0]))
                domain.append((field, '<=', value[1]))
            elif isinstance(value, list):
                domain.append((field, 'in', value))
            else:
                domain.append((field, '=', value))

        # Build field list
        field_names = [f.name for f in self.field_ids] if self.field_ids else ['id', 'name']

        # Check for grouping
        if self.group_by_field:
            group_fields = [self.group_by_field.name]
            if self.date_field and self.date_granularity:
                group_fields.append(f'{self.date_field.name}:{self.date_granularity}')

            # Parse aggregations
            aggs = json.loads(self.aggregations or '[]')
            agg_fields = [f"{a['field']}:{a['function']}" for a in aggs]

            result = Model.read_group(
                domain,
                fields=agg_fields + field_names,
                groupby=group_fields,
                limit=self.record_limit,
                lazy=False
            )
            return {'data': result, 'grouped': True}
        else:
            records = Model.search_read(
                domain,
                fields=field_names,
                limit=self.record_limit
            )
            return {'data': records, 'grouped': False}

    def _fetch_sql_data(self, filters):
        """Execute raw SQL query (restricted to admin users)."""
        self.ensure_one()
        if not self.env.user.has_group('base.group_system'):
            return {'error': 'SQL queries require admin access'}

        if not self.sql_query:
            return {'error': 'No SQL query configured'}

        # Basic SQL injection prevention (parameterized queries should be used)
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']
        query_upper = self.sql_query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return {'error': f'SQL query cannot contain {keyword}'}

        self.env.cr.execute(self.sql_query)
        columns = [desc[0] for desc in self.env.cr.description]
        rows = self.env.cr.fetchall()

        data = [dict(zip(columns, row)) for row in rows]
        return {'data': data[:self.record_limit], 'grouped': False}

    def _fetch_api_data(self, filters):
        """Fetch data from external API."""
        self.ensure_one()
        import requests

        if not self.api_url:
            return {'error': 'No API URL configured'}

        headers = json.loads(self.api_headers or '{}')

        try:
            if self.api_method == 'POST':
                body = json.loads(self.api_body or '{}')
                body.update(filters)
                response = requests.post(self.api_url, json=body, headers=headers, timeout=30)
            else:
                response = requests.get(self.api_url, params=filters, headers=headers, timeout=30)

            response.raise_for_status()
            return {'data': response.json(), 'grouped': False}
        except Exception as e:
            return {'error': str(e)}

    def _fetch_computed_data(self, filters):
        """Execute a custom compute method."""
        self.ensure_one()
        if not self.compute_method:
            return {'error': 'No compute method configured'}

        method = getattr(self, self.compute_method, None)
        if not method or not callable(method):
            return {'error': f'Method {self.compute_method} not found'}

        return method(filters)
```

### 3. Owl-React Bridge Implementation

The bridge allows React components to be embedded within Odoo's Owl-based UI. Data flows from Odoo models through Owl props to React, while user interactions in React trigger callbacks that invoke Odoo RPC calls.

#### 3.1 Bridge Component (`react_bridge.js`)

```javascript
/** @odoo-module */

import { Component, useRef, onMounted, onWillUnmount, onPatched } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * OwlReactBridge - Embeds React components within Owl
 *
 * Architecture:
 * - Owl manages lifecycle and Odoo integration
 * - React manages the dashboard canvas rendering
 * - Communication via props (Owl -> React) and callbacks (React -> Owl)
 */
export class OwlReactBridge extends Component {
    static template = "loomworks_dashboard.ReactBridge";
    static props = {
        dashboardId: { type: Number, optional: true },
        mode: { type: String, optional: true },  // 'view' | 'edit'
        onSave: { type: Function, optional: true },
    };

    setup() {
        this.containerRef = useRef("reactContainer");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.reactRoot = null;
        this.dashboardData = null;

        onMounted(async () => {
            await this.loadDashboardData();
            this.mountReactApp();
        });

        onPatched(() => {
            // Update React props when Owl props change
            if (this.reactRoot && this.dashboardData) {
                this.updateReactProps();
            }
        });

        onWillUnmount(() => {
            this.unmountReactApp();
        });
    }

    async loadDashboardData() {
        if (!this.props.dashboardId) {
            this.dashboardData = this.getEmptyDashboard();
            return;
        }

        try {
            this.dashboardData = await this.rpc("/dashboard/api/get", {
                dashboard_id: this.props.dashboardId,
            });
        } catch (error) {
            this.notification.add("Failed to load dashboard", { type: "danger" });
            this.dashboardData = this.getEmptyDashboard();
        }
    }

    getEmptyDashboard() {
        return {
            id: null,
            name: "New Dashboard",
            layout: { nodes: [], edges: [] },
            grid: [],
            settings: {
                width: 12,
                zoom: 1.0,
                background: "#f5f5f5",
                autoRefresh: false,
                refreshInterval: 60,
            },
            widgets: [],
        };
    }

    mountReactApp() {
        const container = this.containerRef.el;
        if (!container) return;

        // Dynamic import of React and the dashboard app
        Promise.all([
            import("react"),
            import("react-dom/client"),
            import("@loomworks/dashboard"),
        ]).then(([React, ReactDOM, DashboardModule]) => {
            const { DashboardCanvas } = DashboardModule;

            this.reactRoot = ReactDOM.createRoot(container);
            this.reactRoot.render(
                React.createElement(DashboardCanvas, {
                    initialData: this.dashboardData,
                    mode: this.props.mode || "view",
                    onLayoutChange: this.handleLayoutChange.bind(this),
                    onWidgetAdd: this.handleWidgetAdd.bind(this),
                    onWidgetRemove: this.handleWidgetRemove.bind(this),
                    onWidgetUpdate: this.handleWidgetUpdate.bind(this),
                    onSave: this.handleSave.bind(this),
                    onFetchData: this.fetchWidgetData.bind(this),
                })
            );
        });
    }

    updateReactProps() {
        // Re-render React with updated props
        if (this.reactRoot) {
            this.unmountReactApp();
            this.mountReactApp();
        }
    }

    unmountReactApp() {
        if (this.reactRoot) {
            this.reactRoot.unmount();
            this.reactRoot = null;
        }
    }

    // Callbacks from React to Odoo

    async handleLayoutChange(layoutData) {
        if (!this.props.dashboardId) return;

        try {
            await this.rpc("/dashboard/api/save_layout", {
                dashboard_id: this.props.dashboardId,
                layout: layoutData.nodes,
                grid: layoutData.grid,
            });
        } catch (error) {
            this.notification.add("Failed to save layout", { type: "warning" });
        }
    }

    async handleWidgetAdd(widgetConfig) {
        try {
            const result = await this.rpc("/dashboard/api/widget/create", {
                dashboard_id: this.props.dashboardId,
                widget: widgetConfig,
            });
            return result.widget_id;
        } catch (error) {
            this.notification.add("Failed to add widget", { type: "danger" });
            return null;
        }
    }

    async handleWidgetRemove(widgetId) {
        try {
            await this.rpc("/dashboard/api/widget/delete", {
                widget_id: widgetId,
            });
        } catch (error) {
            this.notification.add("Failed to remove widget", { type: "danger" });
        }
    }

    async handleWidgetUpdate(widgetId, updates) {
        try {
            await this.rpc("/dashboard/api/widget/update", {
                widget_id: widgetId,
                updates: updates,
            });
        } catch (error) {
            this.notification.add("Failed to update widget", { type: "warning" });
        }
    }

    async handleSave(dashboardData) {
        if (this.props.onSave) {
            await this.props.onSave(dashboardData);
        }
    }

    async fetchWidgetData(dataSourceId, filters) {
        try {
            const result = await this.rpc("/dashboard/api/data/fetch", {
                data_source_id: dataSourceId,
                filters: filters || {},
            });
            return result;
        } catch (error) {
            console.error("Data fetch error:", error);
            return { error: "Failed to fetch data" };
        }
    }
}

registry.category("actions").add("loomworks_dashboard_canvas", OwlReactBridge);
```

### 4. React Component Architecture

#### 4.1 DashboardCanvas.jsx (Main Container)

```jsx
import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  Panel,
  useReactFlow,
} from '@xyflow/react';
import { GridStack } from 'gridstack';

import ChartNode from './nodes/ChartNode';
import KPINode from './nodes/KPINode';
import TableNode from './nodes/TableNode';
import FilterNode from './nodes/FilterNode';
import WidgetToolbox from './panels/WidgetToolbox';
import PropertyPanel from './panels/PropertyPanel';
import { useDashboardState } from './hooks/useDashboardState';
import { useRealTimeUpdates } from './hooks/useRealTimeUpdates';

import '@xyflow/react/dist/style.css';
import 'gridstack/dist/gridstack.min.css';
import './styles/dashboard.css';

// Register custom node types
const nodeTypes = {
  chartNode: ChartNode,
  kpiNode: KPINode,
  tableNode: TableNode,
  filterNode: FilterNode,
};

function DashboardCanvasInner({
  initialData,
  mode,
  onLayoutChange,
  onWidgetAdd,
  onWidgetRemove,
  onWidgetUpdate,
  onSave,
  onFetchData,
}) {
  const reactFlowWrapper = useRef(null);
  const { screenToFlowPosition } = useReactFlow();

  // Dashboard state management
  const {
    nodes,
    setNodes,
    onNodesChange,
    edges,
    setEdges,
    onEdgesChange,
    selectedNode,
    setSelectedNode,
    filters,
    updateFilter,
    widgetData,
    setWidgetData,
  } = useDashboardState(initialData);

  const [layoutMode, setLayoutMode] = useState('flow'); // 'flow' | 'grid'
  const [showToolbox, setShowToolbox] = useState(mode === 'edit');
  const [showProperties, setShowProperties] = useState(false);

  // Real-time data updates
  useRealTimeUpdates({
    enabled: initialData.settings.autoRefresh,
    interval: initialData.settings.refreshInterval * 1000,
    onRefresh: async () => {
      // Refresh all widget data
      for (const node of nodes) {
        if (node.data.dataSourceId) {
          const data = await onFetchData(node.data.dataSourceId, filters);
          setWidgetData(prev => ({ ...prev, [node.id]: data }));
        }
      }
    },
  });

  // Initial data fetch
  useEffect(() => {
    const fetchAllData = async () => {
      const dataPromises = nodes
        .filter(n => n.data.dataSourceId)
        .map(async (node) => {
          const data = await onFetchData(node.data.dataSourceId, filters);
          return [node.id, data];
        });

      const results = await Promise.all(dataPromises);
      const dataMap = Object.fromEntries(results);
      setWidgetData(dataMap);
    };

    fetchAllData();
  }, [filters]);

  // Drag and drop handler for new widgets
  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    async (event) => {
      event.preventDefault();

      const widgetType = event.dataTransfer.getData('application/loomworks-widget');
      if (!widgetType) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newWidgetConfig = {
        type: widgetType,
        name: `New ${widgetType} Widget`,
        position,
        size: { width: 4, height: 3, minWidth: 2, minHeight: 2 },
      };

      // Create widget in backend
      const widgetId = await onWidgetAdd(newWidgetConfig);
      if (!widgetId) return;

      const newNode = {
        id: `widget-${widgetId}`,
        type: getNodeType(widgetType),
        position,
        data: {
          id: widgetId,
          label: newWidgetConfig.name,
          widgetType,
          config: {},
          dataSourceId: null,
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [screenToFlowPosition, onWidgetAdd]
  );

  // Connection handler for filter -> widget relationships
  const onConnect = useCallback(
    (params) => {
      // Only allow connections from filter nodes
      const sourceNode = nodes.find(n => n.id === params.source);
      if (sourceNode?.data.widgetType !== 'filter') return;

      setEdges((eds) => addEdge({
        ...params,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#6366f1' },
      }, eds));

      // Notify backend of filter connection
      onWidgetUpdate(sourceNode.data.id, {
        filterTargetIds: edges
          .filter(e => e.source === params.source)
          .map(e => e.target)
          .concat(params.target),
      });
    },
    [nodes, edges, onWidgetUpdate]
  );

  // Node selection handler
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
    if (mode === 'edit') {
      setShowProperties(true);
    }
  }, [mode]);

  // Layout change handler
  const handleNodesChange = useCallback((changes) => {
    onNodesChange(changes);

    // Debounced save to backend
    const positionChanges = changes.filter(c => c.type === 'position' && c.dragging === false);
    if (positionChanges.length > 0) {
      onLayoutChange({
        nodes: nodes.map(n => ({
          id: n.id,
          position: n.position,
          data: n.data,
        })),
        edges,
      });
    }
  }, [nodes, edges, onLayoutChange, onNodesChange]);

  // Widget delete handler
  const handleDeleteWidget = useCallback(async () => {
    if (!selectedNode) return;

    await onWidgetRemove(selectedNode.data.id);
    setNodes(nds => nds.filter(n => n.id !== selectedNode.id));
    setEdges(eds => eds.filter(e => e.source !== selectedNode.id && e.target !== selectedNode.id));
    setSelectedNode(null);
    setShowProperties(false);
  }, [selectedNode, onWidgetRemove]);

  return (
    <div className="lw-dashboard-container">
      {mode === 'edit' && showToolbox && (
        <WidgetToolbox onClose={() => setShowToolbox(false)} />
      )}

      <div className="lw-dashboard-canvas" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes.map(n => ({
            ...n,
            data: { ...n.data, widgetData: widgetData[n.id], filters },
          }))}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          snapToGrid
          snapGrid={[20, 20]}
          minZoom={0.25}
          maxZoom={2}
          defaultViewport={{ x: 0, y: 0, zoom: initialData.settings.zoom }}
        >
          <Controls />
          <Background variant="dots" gap={20} size={1} />
          <MiniMap
            nodeStrokeWidth={3}
            zoomable
            pannable
          />

          <Panel position="top-left" className="lw-dashboard-toolbar">
            {mode === 'edit' && (
              <>
                <button onClick={() => setShowToolbox(true)}>
                  Add Widget
                </button>
                <button onClick={() => setLayoutMode(m => m === 'flow' ? 'grid' : 'flow')}>
                  {layoutMode === 'flow' ? 'Grid Mode' : 'Flow Mode'}
                </button>
                <button onClick={() => onSave({ nodes, edges })}>
                  Save Dashboard
                </button>
              </>
            )}
          </Panel>
        </ReactFlow>
      </div>

      {mode === 'edit' && showProperties && selectedNode && (
        <PropertyPanel
          node={selectedNode}
          onUpdate={(updates) => {
            onWidgetUpdate(selectedNode.data.id, updates);
            setNodes(nds => nds.map(n =>
              n.id === selectedNode.id
                ? { ...n, data: { ...n.data, ...updates } }
                : n
            ));
          }}
          onDelete={handleDeleteWidget}
          onClose={() => setShowProperties(false)}
          onFetchData={onFetchData}
        />
      )}
    </div>
  );
}

// Helper to map widget types to node types
function getNodeType(widgetType) {
  if (widgetType.startsWith('chart_')) return 'chartNode';
  if (widgetType === 'kpi') return 'kpiNode';
  if (widgetType === 'table') return 'tableNode';
  if (widgetType === 'filter') return 'filterNode';
  return 'chartNode'; // fallback
}

// Wrapped with ReactFlowProvider
export function DashboardCanvas(props) {
  return (
    <ReactFlowProvider>
      <DashboardCanvasInner {...props} />
    </ReactFlowProvider>
  );
}

export default DashboardCanvas;
```

#### 4.2 ChartNode.jsx

```jsx
import React, { memo } from 'react';
import { Handle, Position, NodeResizer } from '@xyflow/react';
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  PieChart, Pie, ComposedChart, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts';

const CHART_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
  '#f97316', '#eab308', '#22c55e', '#14b8a6',
];

function ChartNode({ data, selected }) {
  const {
    widgetType,
    label,
    widgetData,
    config = {},
    chartConfig = {},
  } = data;

  const chartData = widgetData?.data || [];
  const colors = chartConfig.colors?.length ? chartConfig.colors : CHART_COLORS;

  const renderChart = () => {
    if (!chartData.length) {
      return (
        <div className="lw-chart-empty">
          <span>No data available</span>
        </div>
      );
    }

    // Determine data keys from first record
    const dataKeys = Object.keys(chartData[0]).filter(k =>
      k !== 'name' && k !== 'date' && k !== 'label' && typeof chartData[0][k] === 'number'
    );
    const xAxisKey = chartData[0].name ? 'name' : chartData[0].date ? 'date' : 'label';

    switch (widgetType) {
      case 'chart_line':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              {chartConfig.showGrid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey={xAxisKey} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              {chartConfig.showLegend && <Legend />}
              {dataKeys.map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={colors[index % colors.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );

      case 'chart_bar':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              {chartConfig.showGrid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey={xAxisKey} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              {chartConfig.showLegend && <Legend />}
              {dataKeys.map((key, index) => (
                <Bar
                  key={key}
                  dataKey={key}
                  fill={colors[index % colors.length]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );

      case 'chart_area':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              {chartConfig.showGrid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey={xAxisKey} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              {chartConfig.showLegend && <Legend />}
              {dataKeys.map((key, index) => (
                <Area
                  key={key}
                  type="monotone"
                  dataKey={key}
                  fill={colors[index % colors.length]}
                  fillOpacity={0.3}
                  stroke={colors[index % colors.length]}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        );

      case 'chart_pie':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey={dataKeys[0] || 'value'}
                nameKey={xAxisKey}
                cx="50%"
                cy="50%"
                outerRadius="70%"
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                ))}
              </Pie>
              <Tooltip />
              {chartConfig.showLegend && <Legend />}
            </PieChart>
          </ResponsiveContainer>
        );

      case 'chart_composed':
        return (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              {chartConfig.showGrid && <CartesianGrid strokeDasharray="3 3" />}
              <XAxis dataKey={xAxisKey} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              {chartConfig.showLegend && <Legend />}
              {dataKeys.map((key, index) => {
                // Alternate between chart types
                if (index % 3 === 0) {
                  return <Bar key={key} dataKey={key} fill={colors[index % colors.length]} />;
                } else if (index % 3 === 1) {
                  return <Line key={key} type="monotone" dataKey={key} stroke={colors[index % colors.length]} />;
                } else {
                  return <Area key={key} type="monotone" dataKey={key} fill={colors[index % colors.length]} fillOpacity={0.3} />;
                }
              })}
            </ComposedChart>
          </ResponsiveContainer>
        );

      default:
        return <div>Unsupported chart type</div>;
    }
  };

  return (
    <div className={`lw-chart-node ${selected ? 'selected' : ''}`}>
      <NodeResizer
        minWidth={200}
        minHeight={150}
        isVisible={selected}
        lineClassName="lw-node-resizer-line"
        handleClassName="lw-node-resizer-handle"
      />

      <Handle type="target" position={Position.Left} className="lw-handle" />

      <div className="lw-node-header">
        <span className="lw-node-title">{label}</span>
      </div>

      <div className="lw-node-content">
        {renderChart()}
      </div>

      <Handle type="source" position={Position.Right} className="lw-handle" />
    </div>
  );
}

export default memo(ChartNode);
```

#### 4.3 KPINode.jsx

```jsx
import React, { memo, useMemo } from 'react';
import { Handle, Position, NodeResizer } from '@xyflow/react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';

function KPINode({ data, selected }) {
  const {
    label,
    widgetData,
    kpiConfig = {},
  } = data;

  const { value, previousValue, sparklineData, trend } = useMemo(() => {
    const records = widgetData?.data || [];
    if (records.length === 0) {
      return { value: 0, previousValue: null, sparklineData: [], trend: 0 };
    }

    const valueField = kpiConfig.valueField || 'value';
    const comparisonField = kpiConfig.comparisonField;

    // For aggregated data
    if (records.length === 1 && typeof records[0][valueField] === 'number') {
      const current = records[0][valueField];
      const previous = comparisonField ? records[0][comparisonField] : null;
      return {
        value: current,
        previousValue: previous,
        sparklineData: [],
        trend: previous ? ((current - previous) / previous) * 100 : 0,
      };
    }

    // For time series data
    const sortedRecords = [...records].sort((a, b) => {
      const dateA = new Date(a.date || a.name);
      const dateB = new Date(b.date || b.name);
      return dateA - dateB;
    });

    const current = sortedRecords[sortedRecords.length - 1]?.[valueField] || 0;
    const previous = sortedRecords.length > 1
      ? sortedRecords[sortedRecords.length - 2]?.[valueField]
      : null;

    return {
      value: current,
      previousValue: previous,
      sparklineData: sortedRecords.slice(-10).map((r, i) => ({
        index: i,
        value: r[valueField] || 0,
      })),
      trend: previous ? ((current - previous) / previous) * 100 : 0,
    };
  }, [widgetData, kpiConfig]);

  const formatValue = (val) => {
    if (val === null || val === undefined) return '-';

    switch (kpiConfig.format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          maximumFractionDigits: 0,
        }).format(val);
      case 'percent':
        return `${val.toFixed(1)}%`;
      default:
        return new Intl.NumberFormat('en-US', {
          maximumFractionDigits: val > 1000 ? 0 : 2,
        }).format(val);
    }
  };

  const getTrendIndicator = () => {
    if (trend === 0) return null;

    const isPositive = trend > 0;
    const isGood = kpiConfig.trendPositive === 'up' ? isPositive :
                   kpiConfig.trendPositive === 'down' ? !isPositive : null;

    const colorClass = isGood === true ? 'positive' : isGood === false ? 'negative' : 'neutral';
    const arrow = isPositive ? 'arrow-up' : 'arrow-down';

    return (
      <div className={`lw-kpi-trend ${colorClass}`}>
        <span className={`lw-kpi-trend-icon ${arrow}`} />
        <span className="lw-kpi-trend-value">{Math.abs(trend).toFixed(1)}%</span>
      </div>
    );
  };

  return (
    <div className={`lw-kpi-node ${selected ? 'selected' : ''}`}>
      <NodeResizer
        minWidth={180}
        minHeight={120}
        isVisible={selected}
        lineClassName="lw-node-resizer-line"
        handleClassName="lw-node-resizer-handle"
      />

      <Handle type="target" position={Position.Left} className="lw-handle" />

      <div className="lw-kpi-content">
        <div className="lw-kpi-label">{label}</div>
        <div className="lw-kpi-value">{formatValue(value)}</div>

        <div className="lw-kpi-footer">
          {getTrendIndicator()}
          {previousValue !== null && (
            <span className="lw-kpi-previous">
              vs {formatValue(previousValue)}
            </span>
          )}
        </div>

        {sparklineData.length > 0 && (
          <div className="lw-kpi-sparkline">
            <ResponsiveContainer width="100%" height={40}>
              <AreaChart data={sparklineData}>
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#6366f1"
                  fill="#6366f1"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Right} className="lw-handle" />
    </div>
  );
}

export default memo(KPINode);
```

#### 4.4 TableNode.jsx

```jsx
import React, { memo, useState, useMemo } from 'react';
import { Handle, Position, NodeResizer } from '@xyflow/react';

function TableNode({ data, selected }) {
  const {
    label,
    widgetData,
    tableConfig = {},
  } = data;

  const [currentPage, setCurrentPage] = useState(0);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  const records = widgetData?.data || [];
  const pageSize = tableConfig.pageSize || 10;
  const sortable = tableConfig.sortable !== false;

  // Auto-detect columns or use configured columns
  const columns = useMemo(() => {
    if (tableConfig.columns?.length) {
      return tableConfig.columns;
    }

    if (records.length === 0) return [];

    return Object.keys(records[0])
      .filter(key => key !== 'id' && !key.startsWith('_'))
      .map(key => ({
        key,
        label: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        type: typeof records[0][key],
      }));
  }, [records, tableConfig.columns]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!sortConfig.key || !sortable) return records;

    return [...records].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];

      if (aVal === bVal) return 0;

      const comparison = aVal < bVal ? -1 : 1;
      return sortConfig.direction === 'asc' ? comparison : -comparison;
    });
  }, [records, sortConfig, sortable]);

  // Paginate data
  const paginatedData = useMemo(() => {
    const start = currentPage * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize]);

  const totalPages = Math.ceil(sortedData.length / pageSize);

  const handleSort = (key) => {
    if (!sortable) return;

    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const formatValue = (value, type) => {
    if (value === null || value === undefined) return '-';
    if (type === 'number') {
      return new Intl.NumberFormat('en-US').format(value);
    }
    if (value instanceof Date || (typeof value === 'string' && value.match(/^\d{4}-\d{2}-\d{2}/))) {
      return new Date(value).toLocaleDateString();
    }
    return String(value);
  };

  return (
    <div className={`lw-table-node ${selected ? 'selected' : ''}`}>
      <NodeResizer
        minWidth={300}
        minHeight={200}
        isVisible={selected}
        lineClassName="lw-node-resizer-line"
        handleClassName="lw-node-resizer-handle"
      />

      <Handle type="target" position={Position.Left} className="lw-handle" />

      <div className="lw-node-header">
        <span className="lw-node-title">{label}</span>
        <span className="lw-table-count">{sortedData.length} records</span>
      </div>

      <div className="lw-table-container">
        {columns.length === 0 ? (
          <div className="lw-table-empty">No data available</div>
        ) : (
          <>
            <table className="lw-table">
              <thead>
                <tr>
                  {columns.map(col => (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      className={sortable ? 'sortable' : ''}
                    >
                      {col.label}
                      {sortConfig.key === col.key && (
                        <span className={`sort-icon ${sortConfig.direction}`} />
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {paginatedData.map((row, rowIndex) => (
                  <tr key={row.id || rowIndex}>
                    {columns.map(col => (
                      <td key={col.key}>
                        {formatValue(row[col.key], col.type)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>

            {totalPages > 1 && (
              <div className="lw-table-pagination">
                <button
                  onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
                  disabled={currentPage === 0}
                >
                  Previous
                </button>
                <span>{currentPage + 1} / {totalPages}</span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages - 1, p + 1))}
                  disabled={currentPage === totalPages - 1}
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>

      <Handle type="source" position={Position.Right} className="lw-handle" />
    </div>
  );
}

export default memo(TableNode);
```

#### 4.5 FilterNode.jsx

```jsx
import React, { memo, useState, useEffect } from 'react';
import { Handle, Position, NodeResizer } from '@xyflow/react';

function FilterNode({ data, selected }) {
  const {
    label,
    filterConfig = {},
    filters,
    onFilterChange,
  } = data;

  const [localValue, setLocalValue] = useState(filters?.[filterConfig.field] || null);

  useEffect(() => {
    setLocalValue(filters?.[filterConfig.field] || null);
  }, [filters, filterConfig.field]);

  const handleChange = (newValue) => {
    setLocalValue(newValue);
    if (onFilterChange) {
      onFilterChange(filterConfig.field, newValue);
    }
  };

  const renderFilterControl = () => {
    switch (filterConfig.type) {
      case 'select':
        return (
          <select
            value={localValue || ''}
            onChange={(e) => handleChange(e.target.value || null)}
            className="lw-filter-select"
          >
            <option value="">All</option>
            {(filterConfig.options || []).map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      case 'multiselect':
        return (
          <div className="lw-filter-multiselect">
            {(filterConfig.options || []).map(opt => (
              <label key={opt.value} className="lw-filter-checkbox">
                <input
                  type="checkbox"
                  checked={(localValue || []).includes(opt.value)}
                  onChange={(e) => {
                    const newValue = e.target.checked
                      ? [...(localValue || []), opt.value]
                      : (localValue || []).filter(v => v !== opt.value);
                    handleChange(newValue.length ? newValue : null);
                  }}
                />
                {opt.label}
              </label>
            ))}
          </div>
        );

      case 'date_range':
        return (
          <div className="lw-filter-daterange">
            <input
              type="date"
              value={localValue?.[0] || ''}
              onChange={(e) => handleChange([e.target.value, localValue?.[1] || ''])}
              placeholder="From"
            />
            <span>to</span>
            <input
              type="date"
              value={localValue?.[1] || ''}
              onChange={(e) => handleChange([localValue?.[0] || '', e.target.value])}
              placeholder="To"
            />
          </div>
        );

      case 'number_range':
        return (
          <div className="lw-filter-numberrange">
            <input
              type="number"
              value={localValue?.[0] || ''}
              onChange={(e) => handleChange([parseFloat(e.target.value) || 0, localValue?.[1] || 0])}
              placeholder="Min"
            />
            <span>to</span>
            <input
              type="number"
              value={localValue?.[1] || ''}
              onChange={(e) => handleChange([localValue?.[0] || 0, parseFloat(e.target.value) || 0])}
              placeholder="Max"
            />
          </div>
        );

      case 'search':
        return (
          <input
            type="text"
            value={localValue || ''}
            onChange={(e) => handleChange(e.target.value || null)}
            placeholder="Search..."
            className="lw-filter-search"
          />
        );

      default:
        return <div>Unknown filter type</div>;
    }
  };

  return (
    <div className={`lw-filter-node ${selected ? 'selected' : ''}`}>
      <NodeResizer
        minWidth={150}
        minHeight={80}
        isVisible={selected}
        lineClassName="lw-node-resizer-line"
        handleClassName="lw-node-resizer-handle"
      />

      <div className="lw-filter-content">
        <div className="lw-filter-label">{label}</div>
        {renderFilterControl()}
        {localValue && (
          <button
            className="lw-filter-clear"
            onClick={() => handleChange(null)}
          >
            Clear
          </button>
        )}
      </div>

      <Handle
        type="source"
        position={Position.Right}
        className="lw-handle lw-handle-filter"
        title="Connect to widgets this filter affects"
      />
    </div>
  );
}

export default memo(FilterNode);
```

### 5. Real-Time Data Updates

#### 5.1 useRealTimeUpdates Hook

```javascript
// hooks/useRealTimeUpdates.js

import { useEffect, useRef, useCallback } from 'react';

/**
 * Real-time data update strategy:
 *
 * 1. Polling (default): Simple interval-based fetching
 *    - Pros: Works everywhere, simple implementation
 *    - Cons: Higher latency, unnecessary requests
 *    - Use when: WebSocket unavailable, low-frequency updates needed
 *
 * 2. WebSocket: Server-push updates
 *    - Pros: Real-time, efficient
 *    - Cons: Requires server support, connection management
 *    - Use when: High-frequency updates, live dashboards
 *
 * 3. Hybrid: WebSocket with polling fallback
 *    - Pros: Best of both worlds
 *    - Use when: Production deployments
 */

export function useRealTimeUpdates({
  enabled,
  interval,
  onRefresh,
  websocketUrl = null,
  dashboardId = null,
}) {
  const intervalRef = useRef(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const startPolling = useCallback(() => {
    if (intervalRef.current) return;

    intervalRef.current = setInterval(() => {
      onRefresh();
    }, interval);
  }, [interval, onRefresh]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (!websocketUrl || wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      wsRef.current = new WebSocket(websocketUrl);

      wsRef.current.onopen = () => {
        console.log('Dashboard WebSocket connected');
        // Subscribe to dashboard updates
        if (dashboardId) {
          wsRef.current.send(JSON.stringify({
            type: 'subscribe',
            dashboardId,
          }));
        }
        // Stop polling when WebSocket is connected
        stopPolling();
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'refresh') {
          onRefresh();
        }
      };

      wsRef.current.onclose = () => {
        console.log('Dashboard WebSocket disconnected');
        // Fallback to polling
        if (enabled) {
          startPolling();
        }
        // Attempt reconnection
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket();
        }, 5000);
      };

      wsRef.current.onerror = (error) => {
        console.error('Dashboard WebSocket error:', error);
        wsRef.current?.close();
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      startPolling();
    }
  }, [websocketUrl, dashboardId, onRefresh, enabled, startPolling, stopPolling]);

  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      stopPolling();
      disconnectWebSocket();
      return;
    }

    // Try WebSocket first, fall back to polling
    if (websocketUrl) {
      connectWebSocket();
    } else {
      startPolling();
    }

    return () => {
      stopPolling();
      disconnectWebSocket();
    };
  }, [enabled, websocketUrl, connectWebSocket, disconnectWebSocket, startPolling, stopPolling]);

  // Manual refresh function
  const refresh = useCallback(() => {
    onRefresh();
  }, [onRefresh]);

  return { refresh };
}
```

### 6. AI Dashboard Generation

#### 6.1 AI Generation Controller

```python
# controllers/ai_controller.py

from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class DashboardAIController(http.Controller):

    @http.route('/dashboard/api/ai/generate', type='json', auth='user', methods=['POST'])
    def generate_dashboard(self, prompt, context=None):
        """
        Generate a dashboard from natural language description.

        Example prompt: "Create a sales dashboard showing monthly revenue trends,
        top 5 customers by order value, and order status distribution"
        """
        try:
            # Check if AI module is available
            if not hasattr(request.env, 'loomworks.ai.agent'):
                return self._fallback_generation(prompt)

            # Build context for AI
            available_models = self._get_available_models()
            dashboard_templates = self._get_template_examples()

            ai_context = {
                'available_models': available_models,
                'widget_types': [
                    {'type': 'chart_line', 'use_for': 'trends over time'},
                    {'type': 'chart_bar', 'use_for': 'comparisons across categories'},
                    {'type': 'chart_pie', 'use_for': 'distribution/proportion'},
                    {'type': 'chart_area', 'use_for': 'cumulative trends'},
                    {'type': 'kpi', 'use_for': 'single important metrics'},
                    {'type': 'table', 'use_for': 'detailed data lists'},
                    {'type': 'filter', 'use_for': 'user-controlled data filtering'},
                ],
                'examples': dashboard_templates,
                'user_context': context or {},
            }

            # Call AI agent to generate dashboard specification
            agent = request.env['loomworks.ai.agent'].get_active_agent()

            generation_prompt = f"""
            Generate a dashboard specification based on this user request:
            "{prompt}"

            Available Odoo models and fields:
            {json.dumps(available_models, indent=2)}

            Widget types and their uses:
            {json.dumps(ai_context['widget_types'], indent=2)}

            Return a JSON object with this structure:
            {{
                "name": "Dashboard Name",
                "description": "Brief description",
                "widgets": [
                    {{
                        "name": "Widget Title",
                        "type": "chart_line|chart_bar|chart_pie|kpi|table|filter",
                        "position": {{"x": 0, "y": 0}},
                        "size": {{"width": 4, "height": 3}},
                        "data_source": {{
                            "model": "sale.order",
                            "domain": [],
                            "group_by": "date_order:month",
                            "aggregations": [{{"field": "amount_total", "function": "sum"}}]
                        }},
                        "config": {{}}
                    }}
                ],
                "connections": [
                    {{"from_filter": "widget_index", "to_widgets": [widget_indices]}}
                ]
            }}
            """

            response = agent.execute_prompt(generation_prompt)
            spec = json.loads(response)

            # Create dashboard from specification
            dashboard = self._create_from_spec(spec, prompt)

            return {
                'success': True,
                'dashboard_id': dashboard.id,
                'dashboard_name': dashboard.name,
            }

        except Exception as e:
            _logger.error(f"AI dashboard generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
            }

    def _get_available_models(self):
        """Get models the user has access to with their key fields."""
        accessible_models = []
        common_models = [
            'sale.order', 'purchase.order', 'account.move',
            'stock.picking', 'crm.lead', 'project.task',
            'hr.employee', 'product.product', 'res.partner',
        ]

        for model_name in common_models:
            try:
                Model = request.env[model_name]
                if not Model.check_access_rights('read', raise_exception=False):
                    continue

                # Get key fields
                fields_info = Model.fields_get(['name', 'date', 'state', 'amount', 'total', 'count'])
                numeric_fields = [f for f, info in fields_info.items()
                                 if info.get('type') in ('integer', 'float', 'monetary')]
                date_fields = [f for f, info in fields_info.items()
                              if info.get('type') in ('date', 'datetime')]

                accessible_models.append({
                    'model': model_name,
                    'name': Model._description,
                    'numeric_fields': numeric_fields[:10],  # Limit for context size
                    'date_fields': date_fields[:5],
                })
            except Exception:
                continue

        return accessible_models

    def _get_template_examples(self):
        """Get example dashboard structures for AI context."""
        return [
            {
                'name': 'Sales Overview',
                'widgets': [
                    {'type': 'kpi', 'name': 'Total Revenue', 'model': 'sale.order'},
                    {'type': 'chart_line', 'name': 'Monthly Trend', 'model': 'sale.order'},
                    {'type': 'chart_pie', 'name': 'By Status', 'model': 'sale.order'},
                ]
            }
        ]

    def _create_from_spec(self, spec, original_prompt):
        """Create dashboard and widgets from AI-generated specification."""
        Dashboard = request.env['dashboard.board']
        Widget = request.env['dashboard.widget']
        DataSource = request.env['dashboard.data_source']

        # Create dashboard
        dashboard = Dashboard.create({
            'name': spec.get('name', 'AI Generated Dashboard'),
            'description': spec.get('description', ''),
            'ai_generated': True,
            'ai_prompt': original_prompt,
        })

        widget_map = {}  # Track created widgets for filter connections

        for idx, widget_spec in enumerate(spec.get('widgets', [])):
            # Create data source if specified
            data_source = None
            if 'data_source' in widget_spec:
                ds_spec = widget_spec['data_source']
                model = request.env['ir.model'].search([('model', '=', ds_spec.get('model'))], limit=1)

                if model:
                    data_source = DataSource.create({
                        'name': f"{widget_spec['name']} Data",
                        'source_type': 'model',
                        'model_id': model.id,
                        'domain': json.dumps(ds_spec.get('domain', [])),
                        'aggregations': json.dumps(ds_spec.get('aggregations', [])),
                    })

            # Create widget
            position = widget_spec.get('position', {'x': (idx % 3) * 400, 'y': (idx // 3) * 300})
            size = widget_spec.get('size', {'width': 4, 'height': 3})

            widget = Widget.create({
                'name': widget_spec.get('name', f'Widget {idx + 1}'),
                'board_id': dashboard.id,
                'widget_type': widget_spec.get('type', 'chart_bar'),
                'position_x': position.get('x', 0),
                'position_y': position.get('y', 0),
                'width': size.get('width', 4),
                'height': size.get('height', 3),
                'data_source_id': data_source.id if data_source else None,
                'config': json.dumps(widget_spec.get('config', {})),
            })

            widget_map[idx] = widget

        # Set up filter connections
        for conn in spec.get('connections', []):
            filter_widget = widget_map.get(conn.get('from_filter'))
            if filter_widget and filter_widget.widget_type == 'filter':
                target_ids = [widget_map[i].id for i in conn.get('to_widgets', [])
                             if i in widget_map]
                filter_widget.write({'filter_target_widgets': [(6, 0, target_ids)]})

        # Generate layout config
        layout_config = {
            'nodes': [
                {
                    'id': f'widget-{w.id}',
                    'type': self._get_node_type(w.widget_type),
                    'position': {'x': w.position_x, 'y': w.position_y},
                    'data': w.get_widget_data(),
                }
                for w in dashboard.widget_ids
            ],
            'edges': [],
        }
        dashboard.write({'layout_config': json.dumps(layout_config)})

        return dashboard

    def _get_node_type(self, widget_type):
        if widget_type.startswith('chart_'):
            return 'chartNode'
        return f'{widget_type}Node'

    def _fallback_generation(self, prompt):
        """Simple template-based generation when AI is unavailable."""
        # Parse keywords for basic dashboard generation
        prompt_lower = prompt.lower()

        widgets = []
        if any(w in prompt_lower for w in ['sales', 'revenue', 'order']):
            widgets.extend([
                {'type': 'kpi', 'name': 'Total Sales', 'model': 'sale.order'},
                {'type': 'chart_line', 'name': 'Sales Trend', 'model': 'sale.order'},
            ])
        if any(w in prompt_lower for w in ['customer', 'partner', 'client']):
            widgets.append({'type': 'table', 'name': 'Top Customers', 'model': 'res.partner'})
        if any(w in prompt_lower for w in ['inventory', 'stock', 'product']):
            widgets.append({'type': 'chart_bar', 'name': 'Stock Levels', 'model': 'product.product'})

        if not widgets:
            widgets = [
                {'type': 'kpi', 'name': 'Overview KPI'},
                {'type': 'chart_bar', 'name': 'Data Overview'},
            ]

        spec = {
            'name': 'Generated Dashboard',
            'description': f'Generated from: {prompt[:100]}',
            'widgets': widgets,
        }

        dashboard = self._create_from_spec(spec, prompt)
        return {
            'success': True,
            'dashboard_id': dashboard.id,
            'dashboard_name': dashboard.name,
            'note': 'Basic generation used (AI unavailable)',
        }
```

### 7. Asset Bundling Configuration

#### 7.1 Manifest File

```python
# __manifest__.py

{
    'name': 'Loomworks Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Interactive drag-drop dashboard builder with AI generation',
    'description': """
        Loomworks Dashboard System
        ==========================

        Features:
        - Drag-and-drop dashboard builder
        - React-based canvas with React Flow
        - Multiple widget types (charts, KPIs, tables, filters)
        - Real-time data from Odoo models
        - AI-powered dashboard generation
        - Resizable and repositionable widgets
        - Multi-user sharing and permissions
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'loomworks_core',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/dashboard_views.xml',
        'views/dashboard_action.xml',
        'views/menu.xml',
        'data/dashboard_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Owl components
            'loomworks_dashboard/static/src/components/**/*.js',
            'loomworks_dashboard/static/src/components/**/*.xml',
            'loomworks_dashboard/static/src/scss/dashboard.scss',

            # React bundle (built separately)
            'loomworks_dashboard/static/lib/dashboard-bundle.js',
        ],
        'web.assets_common': [
            # Shared utilities
            'loomworks_dashboard/static/src/utils/*.js',
        ],
    },
    'external_dependencies': {
        'python': [],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
```

#### 7.2 Build Configuration (package.json)

```json
{
  "name": "@loomworks/dashboard",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "vite build",
    "dev": "vite",
    "watch": "vite build --watch"
  },
  "dependencies": {
    "@xyflow/react": "^12.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "recharts": "^2.10.0",
    "@tremor/react": "^3.14.0",
    "gridstack": "^10.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "terser": "^5.0.0"
  }
}
```

#### 7.3 Vite Build Configuration (vite.config.js)

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../lib',
    lib: {
      entry: path.resolve(__dirname, 'index.jsx'),
      name: 'LoomworksDashboard',
      fileName: () => 'dashboard-bundle.js',
      formats: ['iife'],
    },
    rollupOptions: {
      external: [],  // Bundle everything
      output: {
        globals: {},
        assetFileNames: 'dashboard-styles.[ext]',
      },
    },
    minify: 'terser',
    sourcemap: false,
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
  },
});
```

---

## Implementation Steps

### Milestone 1: Backend Foundation (Week 31-32)

- [ ] 1.1 Create `loomworks_dashboard` module scaffold
- [ ] 1.2 Implement `dashboard.board` model with CRUD operations
- [ ] 1.3 Implement `dashboard.widget` model with all widget types
- [ ] 1.4 Implement `dashboard.data_source` model with Odoo model connector
- [ ] 1.5 Create security rules and access rights
- [ ] 1.6 Write unit tests for all models
- [ ] 1.7 Create REST API controllers for dashboard operations

### Milestone 2: Owl-React Bridge (Week 33)

- [ ] 2.1 Set up React build pipeline with Vite
- [ ] 2.2 Implement `OwlReactBridge` component
- [ ] 2.3 Configure asset bundling in manifest
- [ ] 2.4 Create client action for launching dashboard canvas
- [ ] 2.5 Test Owl-React communication (props and callbacks)
- [ ] 2.6 Handle React unmounting and cleanup

### Milestone 3: React Dashboard Canvas (Week 34-35)

- [ ] 3.1 Implement `DashboardCanvas.jsx` with React Flow
- [ ] 3.2 Create `WidgetToolbox` sidebar component
- [ ] 3.3 Implement drag-and-drop widget creation
- [ ] 3.4 Create `PropertyPanel` for widget configuration
- [ ] 3.5 Implement layout persistence (save/load)
- [ ] 3.6 Add minimap and zoom controls

### Milestone 4: Widget Nodes (Week 35-36)

- [ ] 4.1 Implement `ChartNode` with all chart types (line, bar, pie, area, composed)
- [ ] 4.2 Implement `KPINode` with trend indicators and sparklines
- [ ] 4.3 Implement `TableNode` with pagination and sorting
- [ ] 4.4 Implement `FilterNode` with all filter types
- [ ] 4.5 Add node resizing with NodeResizer
- [ ] 4.6 Style all nodes with consistent design system

### Milestone 5: Data Integration (Week 36-37)

- [ ] 5.1 Implement `useOdooData` hook for data fetching
- [ ] 5.2 Create data transformation utilities
- [ ] 5.3 Implement filter → widget data flow
- [ ] 5.4 Add `useRealTimeUpdates` hook with polling
- [ ] 5.5 (Optional) Add WebSocket support for real-time updates
- [ ] 5.6 Implement data caching layer

### Milestone 6: AI Generation (Week 37-38)

- [ ] 6.1 Create AI generation controller
- [ ] 6.2 Implement model/field discovery for AI context
- [ ] 6.3 Build AI prompt templates
- [ ] 6.4 Create fallback template-based generation
- [ ] 6.5 Add "Generate Dashboard" UI button
- [ ] 6.6 Test AI generation with various prompts

### Milestone 7: Polish and Testing (Week 38)

- [ ] 7.1 Add pre-built dashboard templates
- [ ] 7.2 Implement dashboard sharing permissions
- [ ] 7.3 Add export functionality (PNG, PDF)
- [ ] 7.4 Performance optimization (lazy loading, virtualization)
- [ ] 7.5 Write integration tests
- [ ] 7.6 Documentation and demo data

---

## Testing Criteria

### Unit Tests

| Test Area | Test Cases |
|-----------|------------|
| `dashboard.board` | Create, read, update, delete dashboards |
| `dashboard.widget` | Create widgets of all types, validate config |
| `dashboard.data_source` | Fetch data from Odoo models, SQL queries |
| Data transformation | Grouping, aggregation, filtering |
| Layout serialization | Save/load React Flow layout JSON |

### Integration Tests

| Test Area | Test Cases |
|-----------|------------|
| Owl-React bridge | Props flow correctly, callbacks invoke RPC |
| Widget data flow | Data source → Widget → Chart renders |
| Filter connections | Filter changes propagate to connected widgets |
| Real-time updates | Polling refreshes data correctly |
| AI generation | Prompt generates valid dashboard structure |

### Visual/UI Tests

| Test Area | Test Cases |
|-----------|------------|
| Drag-drop | Widgets can be dragged from toolbox to canvas |
| Resize | Widgets resize correctly with NodeResizer |
| Charts | All chart types render with sample data |
| Responsive | Dashboard displays on different screen sizes |
| Performance | Dashboard with 20 widgets loads < 1 second |

### Data Accuracy Tests

| Test Area | Test Cases |
|-----------|------------|
| Aggregations | Sum, avg, count match raw SQL results |
| Date grouping | Monthly/weekly/daily groupings are correct |
| Filters | Domain filters return correct record counts |
| KPI calculations | Trend percentages are mathematically correct |

---

## Success Criteria

1. **Functional Requirements**
   - Users can create dashboards via drag-drop builder
   - All 10 widget types render correctly with data
   - Filters affect connected widgets in real-time
   - Dashboards persist and reload correctly
   - AI generates usable dashboards from natural language

2. **Performance Requirements**
   - Dashboard canvas loads in < 1 second
   - Data refresh completes in < 3 seconds
   - Smooth drag-drop at 60fps
   - Memory usage < 100MB for complex dashboards

3. **Quality Requirements**
   - 80%+ unit test coverage on backend models
   - No console errors in production builds
   - LGPL v3 compliance for all code
   - Accessible (WCAG 2.1 AA) color contrast

4. **Integration Requirements**
   - Works with standard Odoo v18 installation
   - No conflicts with other Loomworks modules
   - React bundle < 500KB gzipped
   - Compatible with Odoo's asset pipeline

---

## References

### Technology Documentation
- [React Flow Documentation](https://reactflow.dev) - Node-based canvas library
- [Tremor Documentation](https://tremor.so) - Dashboard UI components
- [Recharts Documentation](https://recharts.org) - React charting library
- [Gridstack.js Documentation](https://gridstackjs.com) - Resizable grid layouts
- [Odoo 18 Developer Docs](https://www.odoo.com/documentation/18.0/developer.html) - Odoo development
- [Owl Framework](https://github.com/odoo/owl) - Odoo's frontend framework

### Real-Time Updates
- [WebSocket vs Polling Guide](https://www.mergesociety.com/code-report/websocket-polling) - Communication patterns
- [SSE vs WebSockets](https://dev.to/haraf/server-sent-events-sse-vs-websockets-vs-long-polling-whats-best-in-2025-5ep8) - Best practices 2025

### Research Sources
- React Flow custom nodes and drag-drop: Context7 `/websites/reactflow_dev`
- Tremor chart components: Context7 `/websites/tremor_so`
- Recharts visualization: Context7 `/recharts/recharts`
- Gridstack React integration: Context7 `/gridstack/gridstack.js`
