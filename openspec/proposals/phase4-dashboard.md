# Change: Phase 4 Dashboard System (Core Feature)

## Why

Business users need visual, interactive dashboards to monitor KPIs, trends, and operational metrics without writing code or SQL. Traditional Odoo dashboards are limited to static configurations with basic graph and pivot views. The Loomworks Dashboard System provides a modern drag-drop builder with AI-powered dashboard generation, enabling users to create custom visualizations from natural language descriptions.

**This is now a CORE FEATURE** of the Loomworks fork, not an addon module. By integrating directly into the Odoo web module:
- Dashboard becomes a native view type alongside form, list, kanban, graph, and pivot
- React becomes a first-class citizen in the asset pipeline
- Unified charting replaces fragmented Odoo graph/pivot implementations
- AI dashboard generation integrates at the framework level

This positions Loomworks ERP as a truly AI-first platform where business intelligence is built into the core, not bolted on.

## What Changes

### Core Odoo Modifications (Fork Changes)

- **NEW** `odoo/addons/web/static/src/views/dashboard/` - Native dashboard view type in core
- **NEW** `odoo/addons/web/static/src/core/react_bridge/` - React integration infrastructure
- **NEW** `odoo/addons/web/static/src/core/react_provider/` - Shared React context provider
- **MODIFIED** `odoo/addons/web/static/src/views/graph/` - Replace with Recharts-based implementation
- **MODIFIED** `odoo/addons/web/static/src/views/pivot/` - Enhanced pivot with Recharts visualizations
- **MODIFIED** `odoo/addons/web/__manifest__.py` - React as core dependency with asset bundling
- **NEW** `odoo/addons/web/static/lib/react/` - React 18 core libraries (vendored)

### Dashboard Module (Loomworks Addon)

- **NEW** `loomworks_addons/loomworks_dashboard/` - Dashboard persistence and AI generation
- **NEW** `dashboard.board` model for storing dashboard configurations
- **NEW** `dashboard.widget` model for individual widget definitions
- **NEW** `dashboard.data_source` model for connecting widgets to Odoo models
- **NEW** AI dashboard generation service using Claude

## Impact

- Affected specs: `loomworks-dashboard` (new capability), `odoo-web-views` (modified)
- Affected code:
  - **Core**: `odoo/addons/web/static/src/views/` (new dashboard view, modified graph/pivot)
  - **Core**: `odoo/addons/web/static/src/core/` (React bridge infrastructure)
  - **Addon**: `loomworks_addons/loomworks_dashboard/` (persistence, AI generation)
- Dependencies:
  - Core: React 18+, ReactDOM, Recharts (bundled in web module)
  - Addon: `loomworks_core`, `loomworks_ai` (optional for AI generation)

### Runtime Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| **Node.js** | >= 20.0.0 (LTS) | Required for React 18+ builds and Odoo asset bundling |
| **npm** | >= 9.0.0 | Package management |
| **Python** | >= 3.10 | Odoo v18 requirement |
| **PostgreSQL** | >= 15 | Required for WAL features |

## Scope

This proposal covers **Phase 4 (Weeks 31-38)** of the implementation plan:

1. **Core View System**: Add dashboard as native Odoo view type
2. **React Integration**: Embed React in Odoo's Owl-based frontend at the core level
3. **Unified Charting**: Replace Odoo's graph/pivot views with Recharts
4. **Dashboard Builder**: Drag-drop canvas with widget library
5. **AI Generation**: Natural language to dashboard configuration
6. **Data Connectors**: Connect widgets to Odoo models with real-time updates

---

## Technical Design

### 1. Core View System Architecture

The dashboard view type follows Odoo 18's standard view architecture with Controller, Model, Renderer, and ArchParser components. This ensures dashboards work seamlessly with Odoo's action system, search views, and favorites.

#### 1.1 View Registration (`odoo/addons/web/static/src/views/dashboard/dashboard_view.js`)

```javascript
/** @odoo-module */

import { registry } from "@web/core/registry";
import { DashboardController } from "./dashboard_controller";
import { DashboardArchParser } from "./dashboard_arch_parser";
import { DashboardModel } from "./dashboard_model";
import { DashboardRenderer } from "./dashboard_renderer";

export const dashboardView = {
    type: "dashboard",
    display_name: "Dashboard",
    icon: "fa fa-tachometer",
    multiRecord: true,
    Controller: DashboardController,
    ArchParser: DashboardArchParser,
    Model: DashboardModel,
    Renderer: DashboardRenderer,

    props(genericProps, view) {
        const { ArchParser } = view;
        const { arch } = genericProps;
        const archInfo = new ArchParser().parse(arch);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            archInfo,
        };
    },
};

// Register as core view type
registry.category("views").add("dashboard", dashboardView);
```

#### 1.2 Dashboard Controller (`dashboard_controller.js`)

```javascript
/** @odoo-module */

import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useReactBridge } from "@web/core/react_bridge/react_bridge";

export class DashboardController extends Component {
    static template = "web.DashboardView";
    static components = { Layout };

    static props = {
        resModel: String,
        archInfo: Object,
        Model: Function,
        Renderer: Function,
        domain: { type: Array, optional: true },
        context: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.reactBridge = useReactBridge();
        this.containerRef = useRef("dashboardContainer");

        // Dashboard configuration from arch
        this.dashboardConfig = this.props.archInfo;

        // Reactive model state
        this.model = useState(
            new this.props.Model(
                this.orm,
                this.props.resModel,
                this.dashboardConfig,
                this.props.domain || []
            )
        );

        onWillStart(async () => {
            await this.model.load();
        });

        onMounted(() => {
            this.mountReactDashboard();
        });

        onWillUnmount(() => {
            this.unmountReactDashboard();
        });
    }

    mountReactDashboard() {
        if (!this.containerRef.el) return;

        this.reactBridge.mount(
            this.containerRef.el,
            "DashboardCanvas",
            {
                config: this.dashboardConfig,
                data: this.model.data,
                mode: this.dashboardConfig.editable ? "edit" : "view",
                onSave: this.handleSave.bind(this),
                onWidgetAction: this.handleWidgetAction.bind(this),
                onFetchData: this.fetchWidgetData.bind(this),
            }
        );
    }

    unmountReactDashboard() {
        if (this.containerRef.el) {
            this.reactBridge.unmount(this.containerRef.el);
        }
    }

    async handleSave(dashboardData) {
        try {
            await this.orm.call(
                "dashboard.board",
                "save_from_view",
                [this.dashboardConfig.boardId, dashboardData]
            );
            this.notification.add("Dashboard saved", { type: "success" });
        } catch (error) {
            this.notification.add("Failed to save dashboard", { type: "danger" });
        }
    }

    async handleWidgetAction(action) {
        // Handle widget clicks that should open Odoo records/actions
        if (action.type === "open_record") {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: action.model,
                res_id: action.resId,
                views: [[false, "form"]],
            });
        } else if (action.type === "open_list") {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: action.model,
                domain: action.domain,
                views: [[false, "list"], [false, "form"]],
            });
        }
    }

    async fetchWidgetData(dataSourceId, filters) {
        return await this.orm.call(
            "dashboard.data_source",
            "fetch_data",
            [dataSourceId, filters]
        );
    }
}
```

#### 1.3 Dashboard Arch Parser (`dashboard_arch_parser.js`)

```javascript
/** @odoo-module */

import { XMLParser } from "@web/core/utils/xml";

/**
 * Parses dashboard view arch definitions.
 *
 * Example arch:
 * <dashboard board_id="1" editable="true" auto_refresh="60">
 *     <widget type="kpi" data_source="sales_total" x="0" y="0" w="3" h="2"/>
 *     <widget type="chart_line" data_source="sales_trend" x="3" y="0" w="6" h="4"/>
 *     <widget type="table" data_source="recent_orders" x="0" y="2" w="3" h="4"/>
 * </dashboard>
 */
export class DashboardArchParser extends XMLParser {
    parse(arch) {
        const xmlDoc = this.parseXML(arch);

        // Dashboard-level attributes
        const boardId = xmlDoc.getAttribute("board_id");
        const editable = xmlDoc.getAttribute("editable") === "true";
        const autoRefresh = parseInt(xmlDoc.getAttribute("auto_refresh") || "0", 10);
        const title = xmlDoc.getAttribute("string") || "Dashboard";

        // Parse widget definitions
        const widgets = [];
        const widgetNodes = xmlDoc.querySelectorAll("widget");
        for (const node of widgetNodes) {
            widgets.push({
                type: node.getAttribute("type"),
                dataSource: node.getAttribute("data_source"),
                x: parseInt(node.getAttribute("x") || "0", 10),
                y: parseInt(node.getAttribute("y") || "0", 10),
                w: parseInt(node.getAttribute("w") || "4", 10),
                h: parseInt(node.getAttribute("h") || "3", 10),
                config: this._parseWidgetConfig(node),
            });
        }

        return {
            boardId,
            editable,
            autoRefresh,
            title,
            widgets,
        };
    }

    _parseWidgetConfig(node) {
        const config = {};

        // Chart-specific
        if (node.hasAttribute("chart_type")) {
            config.chartType = node.getAttribute("chart_type");
        }
        if (node.hasAttribute("stacked")) {
            config.stacked = node.getAttribute("stacked") === "true";
        }
        if (node.hasAttribute("colors")) {
            config.colors = node.getAttribute("colors").split(",");
        }

        // KPI-specific
        if (node.hasAttribute("format")) {
            config.format = node.getAttribute("format");
        }
        if (node.hasAttribute("trend")) {
            config.trend = node.getAttribute("trend");
        }

        // Table-specific
        if (node.hasAttribute("page_size")) {
            config.pageSize = parseInt(node.getAttribute("page_size"), 10);
        }

        return config;
    }
}
```

### 2. React Integration in Core

React integration is implemented at the core level to enable seamless embedding of React components within Odoo's Owl framework. This is not an addon-level hack but a proper architectural integration.

#### 2.1 React Bridge Service (`odoo/addons/web/static/src/core/react_bridge/react_bridge.js`)

```javascript
/** @odoo-module */

import { registry } from "@web/core/registry";

/**
 * ReactBridge - Core service for mounting React components in Owl
 *
 * This service manages React's lifecycle within Odoo's Owl framework:
 * - Lazy-loads React and ReactDOM
 * - Maintains a registry of React components
 * - Handles mounting/unmounting with proper cleanup
 * - Provides shared context for Odoo services
 */
class ReactBridgeService {
    constructor(env, services) {
        this.env = env;
        this.services = services;
        this.roots = new Map(); // container -> ReactRoot
        this.components = new Map(); // name -> Component
        this.reactLoaded = false;
        this.React = null;
        this.ReactDOM = null;
    }

    async ensureReactLoaded() {
        if (this.reactLoaded) return;

        // React is bundled in web.assets_backend
        const [React, ReactDOM] = await Promise.all([
            import("@web/lib/react/react"),
            import("@web/lib/react/react-dom"),
        ]);

        this.React = React.default || React;
        this.ReactDOM = ReactDOM.default || ReactDOM;
        this.reactLoaded = true;
    }

    /**
     * Register a React component for use in Odoo
     */
    registerComponent(name, component) {
        this.components.set(name, component);
    }

    /**
     * Mount a React component into a DOM container
     */
    async mount(container, componentName, props = {}) {
        await this.ensureReactLoaded();

        const Component = this.components.get(componentName);
        if (!Component) {
            throw new Error(`React component "${componentName}" not registered`);
        }

        // Unmount existing root if any
        if (this.roots.has(container)) {
            this.unmount(container);
        }

        // Create new root and render
        const root = this.ReactDOM.createRoot(container);

        // Wrap with OdooContext provider
        const element = this.React.createElement(
            OdooContextProvider,
            {
                value: {
                    env: this.env,
                    services: this.services,
                    orm: this.services.orm,
                    notification: this.services.notification,
                    action: this.services.action,
                }
            },
            this.React.createElement(Component, props)
        );

        root.render(element);
        this.roots.set(container, root);
    }

    /**
     * Unmount React from a container
     */
    unmount(container) {
        const root = this.roots.get(container);
        if (root) {
            root.unmount();
            this.roots.delete(container);
        }
    }

    /**
     * Update props on a mounted component
     */
    async update(container, props) {
        const root = this.roots.get(container);
        if (!root) {
            console.warn("No React root found for container");
            return;
        }

        // Re-render with new props (React handles diffing)
        await this.mount(container, this._getComponentName(container), props);
    }
}

// Service registration
export const reactBridgeService = {
    dependencies: ["orm", "notification", "action"],
    start(env, services) {
        return new ReactBridgeService(env, services);
    },
};

registry.category("services").add("reactBridge", reactBridgeService);

// Hook for Owl components
export function useReactBridge() {
    const { services } = owl.useEnv();
    return services.reactBridge;
}
```

#### 2.2 Odoo Context Provider (`odoo/addons/web/static/src/core/react_provider/OdooContext.jsx`)

```jsx
/**
 * OdooContext - React context providing access to Odoo services
 *
 * This allows React components to access Odoo's ORM, notifications,
 * and other services without prop drilling.
 */
import React, { createContext, useContext } from 'react';

export const OdooContext = createContext(null);

export function OdooContextProvider({ children, value }) {
    return (
        <OdooContext.Provider value={value}>
            {children}
        </OdooContext.Provider>
    );
}

/**
 * Hook to access Odoo services from React components
 */
export function useOdoo() {
    const context = useContext(OdooContext);
    if (!context) {
        throw new Error('useOdoo must be used within OdooContextProvider');
    }
    return context;
}

/**
 * Hook to access Odoo ORM from React
 */
export function useOdooORM() {
    const { orm } = useOdoo();
    return orm;
}

/**
 * Hook to access Odoo notifications from React
 */
export function useOdooNotification() {
    const { notification } = useOdoo();
    return notification;
}

/**
 * Hook to trigger Odoo actions from React
 */
export function useOdooAction() {
    const { action } = useOdoo();
    return action;
}
```

### 3. Unified Charting with Recharts

Replace Odoo's existing graph views with Recharts for consistent, modern visualizations across dashboards and traditional views.

#### 3.1 Enhanced Graph View (`odoo/addons/web/static/src/views/graph/graph_renderer.js`)

```javascript
/** @odoo-module */

import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useReactBridge } from "@web/core/react_bridge/react_bridge";

/**
 * GraphRenderer - Recharts-based graph rendering
 *
 * This replaces Odoo's original Chart.js-based implementation with Recharts,
 * providing consistent visualization across graph views and dashboards.
 */
export class GraphRenderer extends Component {
    static template = "web.GraphRenderer";
    static props = {
        data: Object,
        mode: String, // 'bar' | 'line' | 'pie'
        stacked: { type: Boolean, optional: true },
        colors: { type: Array, optional: true },
        showLegend: { type: Boolean, optional: true },
    };

    setup() {
        this.containerRef = useRef("chartContainer");
        this.reactBridge = useReactBridge();

        onMounted(() => {
            this.renderChart();
        });

        onWillUnmount(() => {
            this.reactBridge.unmount(this.containerRef.el);
        });
    }

    renderChart() {
        if (!this.containerRef.el) return;

        const chartProps = {
            data: this.transformData(),
            type: this.props.mode,
            stacked: this.props.stacked || false,
            colors: this.props.colors || DEFAULT_CHART_COLORS,
            showLegend: this.props.showLegend !== false,
            showGrid: true,
        };

        this.reactBridge.mount(
            this.containerRef.el,
            "RechartsGraph",
            chartProps
        );
    }

    transformData() {
        // Transform Odoo's graph data format to Recharts format
        const { labels, datasets } = this.props.data;

        return labels.map((label, idx) => {
            const point = { name: label };
            datasets.forEach((dataset, dsIdx) => {
                point[dataset.label || `series${dsIdx}`] = dataset.data[idx];
            });
            return point;
        });
    }
}

const DEFAULT_CHART_COLORS = [
    '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
    '#f97316', '#eab308', '#22c55e', '#14b8a6',
];
```

#### 3.2 Recharts Graph Component (`odoo/addons/web/static/src/core/react_components/RechartsGraph.jsx`)

```jsx
import React, { useMemo } from 'react';
import {
    LineChart, Line,
    BarChart, Bar,
    AreaChart, Area,
    PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const DEFAULT_COLORS = [
    '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
    '#f97316', '#eab308', '#22c55e', '#14b8a6',
];

export function RechartsGraph({
    data,
    type = 'bar',
    stacked = false,
    colors = DEFAULT_COLORS,
    showLegend = true,
    showGrid = true,
    height = 300,
}) {
    const dataKeys = useMemo(() => {
        if (!data || data.length === 0) return [];
        return Object.keys(data[0]).filter(k => k !== 'name' && typeof data[0][k] === 'number');
    }, [data]);

    if (!data || data.length === 0) {
        return (
            <div className="lw-chart-empty" style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span>No data available</span>
            </div>
        );
    }

    const commonProps = {
        data,
        margin: { top: 10, right: 30, left: 0, bottom: 0 },
    };

    const renderChart = () => {
        switch (type) {
            case 'line':
                return (
                    <LineChart {...commonProps}>
                        {showGrid && <CartesianGrid strokeDasharray="3 3" />}
                        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip />
                        {showLegend && <Legend />}
                        {dataKeys.map((key, idx) => (
                            <Line
                                key={key}
                                type="monotone"
                                dataKey={key}
                                stroke={colors[idx % colors.length]}
                                strokeWidth={2}
                                dot={{ r: 4 }}
                                activeDot={{ r: 6 }}
                            />
                        ))}
                    </LineChart>
                );

            case 'bar':
                return (
                    <BarChart {...commonProps}>
                        {showGrid && <CartesianGrid strokeDasharray="3 3" />}
                        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip />
                        {showLegend && <Legend />}
                        {dataKeys.map((key, idx) => (
                            <Bar
                                key={key}
                                dataKey={key}
                                fill={colors[idx % colors.length]}
                                stackId={stacked ? 'stack' : undefined}
                            />
                        ))}
                    </BarChart>
                );

            case 'area':
                return (
                    <AreaChart {...commonProps}>
                        {showGrid && <CartesianGrid strokeDasharray="3 3" />}
                        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip />
                        {showLegend && <Legend />}
                        {dataKeys.map((key, idx) => (
                            <Area
                                key={key}
                                type="monotone"
                                dataKey={key}
                                fill={colors[idx % colors.length]}
                                stroke={colors[idx % colors.length]}
                                fillOpacity={0.3}
                                stackId={stacked ? 'stack' : undefined}
                            />
                        ))}
                    </AreaChart>
                );

            case 'pie':
                // Pie charts use the first numeric field
                const valueKey = dataKeys[0] || 'value';
                return (
                    <PieChart>
                        <Pie
                            data={data}
                            dataKey={valueKey}
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius="70%"
                            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                            labelLine={false}
                        >
                            {data.map((entry, idx) => (
                                <Cell key={`cell-${idx}`} fill={colors[idx % colors.length]} />
                            ))}
                        </Pie>
                        <Tooltip />
                        {showLegend && <Legend />}
                    </PieChart>
                );

            default:
                return <div>Unsupported chart type: {type}</div>;
        }
    };

    return (
        <ResponsiveContainer width="100%" height={height}>
            {renderChart()}
        </ResponsiveContainer>
    );
}

export default RechartsGraph;
```

### 4. Asset Bundling Configuration

#### 4.1 Modified Web Manifest (`odoo/addons/web/__manifest__.py`)

```python
{
    'name': 'Web',
    'category': 'Hidden',
    'version': '18.0.1.1.0',  # Bumped for React integration
    'description': """
        Odoo Web core module.
        Enhanced with React integration for dashboard views.
    """,
    'depends': ['base'],
    'assets': {
        # React core libraries (vendored)
        'web.assets_backend': [
            # React core (order matters)
            'web/static/lib/react/react.production.min.js',
            'web/static/lib/react/react-dom.production.min.js',

            # React bridge infrastructure
            'web/static/src/core/react_bridge/**/*.js',
            'web/static/src/core/react_provider/**/*.js',
            'web/static/src/core/react_provider/**/*.jsx',

            # Recharts and dashboard components (built bundle)
            'web/static/lib/recharts/recharts.min.js',
            'web/static/src/core/react_components/**/*.jsx',

            # Dashboard view type
            'web/static/src/views/dashboard/**/*.js',
            'web/static/src/views/dashboard/**/*.xml',
            'web/static/src/views/dashboard/**/*.scss',

            # Enhanced graph/pivot views
            'web/static/src/views/graph/**/*.js',
            'web/static/src/views/graph/**/*.xml',
            'web/static/src/views/pivot/**/*.js',
            'web/static/src/views/pivot/**/*.xml',
        ],

        # Dashboard builder (edit mode only, lazy loaded)
        'web.assets_backend_lazy': [
            'web/static/lib/xyflow/xyflow.min.js',
            'web/static/lib/gridstack/gridstack.min.js',
            'web/static/src/views/dashboard/builder/**/*.jsx',
        ],
    },
    'license': 'LGPL-3',
}
```

#### 4.2 Build Configuration (`odoo/addons/web/static/src/package.json`)

```json
{
    "name": "@odoo/web-react",
    "version": "18.0.0",
    "private": true,
    "scripts": {
        "build": "vite build",
        "build:watch": "vite build --watch",
        "build:dev": "vite build --mode development"
    },
    "dependencies": {
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "recharts": "^2.10.0",
        "@xyflow/react": "^12.0.0",
        "gridstack": "^10.0.0"
    },
    "devDependencies": {
        "@vitejs/plugin-react": "^4.2.0",
        "vite": "^5.0.0",
        "terser": "^5.0.0"
    }
}
```

#### 4.3 Vite Build Configuration (`odoo/addons/web/static/src/vite.config.js`)

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
    plugins: [react()],
    build: {
        outDir: '../lib',
        lib: {
            entry: {
                'react-components': path.resolve(__dirname, 'core/react_components/index.jsx'),
                'dashboard-builder': path.resolve(__dirname, 'views/dashboard/builder/index.jsx'),
            },
            formats: ['es'],
        },
        rollupOptions: {
            external: ['react', 'react-dom'],
            output: {
                globals: {
                    react: 'React',
                    'react-dom': 'ReactDOM',
                },
            },
        },
        minify: 'terser',
        sourcemap: process.env.NODE_ENV !== 'production',
    },
});
```

### 5. Dashboard Module Structure (Loomworks Addon)

The persistence layer and AI generation remain in the Loomworks addon, while core view infrastructure lives in the forked Odoo web module.

```
loomworks_addons/loomworks_dashboard/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── dashboard_board.py          # Dashboard configuration storage
│   ├── dashboard_widget.py         # Widget definitions
│   ├── dashboard_data_source.py    # Data connectors
│   └── dashboard_template.py       # Pre-built templates
├── controllers/
│   ├── __init__.py
│   ├── dashboard_controller.py     # REST API for dashboard CRUD
│   ├── data_controller.py          # Data fetching endpoints
│   └── ai_controller.py            # AI generation endpoints
├── views/
│   ├── dashboard_views.xml         # Admin views for dashboards
│   ├── dashboard_action.xml        # Client actions
│   └── menu.xml                    # Navigation
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── data/
│   ├── dashboard_templates.xml     # Pre-built templates
│   └── demo_dashboards.xml
├── static/
│   └── src/
│       └── scss/
│           └── dashboard_addon.scss  # Addon-specific styles
└── tests/
    ├── __init__.py
    ├── test_dashboard_board.py
    ├── test_dashboard_widget.py
    └── test_ai_generation.py
```

### 6. AI Dashboard Generation Service

#### 6.1 Core Integration (`loomworks_addons/loomworks_dashboard/services/ai_dashboard_service.py`)

```python
from odoo import models, api
import json
import logging

_logger = logging.getLogger(__name__)


class AIDashboardService(models.AbstractModel):
    """
    AI Dashboard Generation Service

    Integrates with loomworks_ai to generate dashboards from natural language.
    Falls back to template-based generation when AI is unavailable.
    """
    _name = 'dashboard.ai.service'
    _description = 'AI Dashboard Generation Service'

    @api.model
    def generate_from_prompt(self, prompt, context=None):
        """
        Generate a dashboard specification from natural language.

        Args:
            prompt: Natural language description of desired dashboard
            context: Optional dict with user preferences, model hints

        Returns:
            dict: Dashboard specification with widgets, data sources, layout
        """
        try:
            # Check if AI module is available
            if 'loomworks.ai.agent' in self.env:
                return self._generate_with_ai(prompt, context)
            else:
                return self._generate_with_templates(prompt, context)
        except Exception as e:
            _logger.error(f"AI dashboard generation failed: {e}")
            return self._generate_with_templates(prompt, context)

    def _generate_with_ai(self, prompt, context):
        """Generate using Claude AI agent."""
        agent = self.env['loomworks.ai.agent'].get_active_agent()

        # Build context for AI
        available_models = self._get_accessible_models()
        widget_types = self._get_widget_type_descriptions()

        generation_prompt = f"""
        Generate a dashboard specification based on this user request:
        "{prompt}"

        Available Odoo models the user can access:
        {json.dumps(available_models, indent=2)}

        Available widget types:
        {json.dumps(widget_types, indent=2)}

        Return a JSON object with this exact structure:
        {{
            "name": "Dashboard Name",
            "description": "Brief description",
            "widgets": [
                {{
                    "name": "Widget Title",
                    "type": "chart_line|chart_bar|chart_pie|chart_area|kpi|table|filter|gauge",
                    "position": {{"x": 0, "y": 0}},
                    "size": {{"width": 4, "height": 3}},
                    "data_source": {{
                        "type": "model",
                        "model": "sale.order",
                        "domain": [],
                        "group_by": "date_order:month",
                        "measure_field": "amount_total",
                        "aggregation": "sum"
                    }},
                    "config": {{
                        "show_legend": true,
                        "colors": ["#6366f1", "#8b5cf6"]
                    }}
                }}
            ],
            "filters": [
                {{
                    "name": "Date Range",
                    "field": "date_order",
                    "type": "date_range",
                    "affects_widgets": [0, 1, 2]
                }}
            ],
            "layout": {{
                "columns": 12,
                "auto_arrange": true
            }}
        }}

        Guidelines:
        - Use appropriate chart types for the data (line for trends, bar for comparisons, pie for proportions)
        - Include KPI widgets for key metrics
        - Add filters for commonly filtered fields (dates, status, categories)
        - Position widgets logically (KPIs at top, main charts in middle, details at bottom)
        - Ensure data sources reference accessible models
        """

        response = agent.execute_prompt(generation_prompt)
        spec = json.loads(response)

        return {
            'success': True,
            'specification': spec,
            'method': 'ai',
        }

    def _generate_with_templates(self, prompt, context):
        """Fallback template-based generation."""
        prompt_lower = prompt.lower()

        # Detect dashboard type from keywords
        if any(w in prompt_lower for w in ['sales', 'revenue', 'order']):
            template = self._get_sales_template()
        elif any(w in prompt_lower for w in ['inventory', 'stock', 'warehouse']):
            template = self._get_inventory_template()
        elif any(w in prompt_lower for w in ['hr', 'employee', 'attendance']):
            template = self._get_hr_template()
        elif any(w in prompt_lower for w in ['crm', 'lead', 'opportunity']):
            template = self._get_crm_template()
        else:
            template = self._get_generic_template()

        return {
            'success': True,
            'specification': template,
            'method': 'template',
            'note': 'Generated from template (AI unavailable)',
        }

    def _get_accessible_models(self):
        """Get models the current user can access."""
        common_models = [
            'sale.order', 'purchase.order', 'account.move',
            'stock.picking', 'crm.lead', 'project.task',
            'hr.employee', 'product.product', 'res.partner',
        ]

        accessible = []
        for model_name in common_models:
            try:
                Model = self.env[model_name]
                if Model.check_access_rights('read', raise_exception=False):
                    fields = Model.fields_get()
                    numeric_fields = [
                        f for f, info in fields.items()
                        if info.get('type') in ('integer', 'float', 'monetary')
                    ][:10]
                    date_fields = [
                        f for f, info in fields.items()
                        if info.get('type') in ('date', 'datetime')
                    ][:5]

                    accessible.append({
                        'model': model_name,
                        'description': Model._description,
                        'numeric_fields': numeric_fields,
                        'date_fields': date_fields,
                    })
            except Exception:
                continue

        return accessible

    def _get_widget_type_descriptions(self):
        """Get widget type descriptions for AI context."""
        return [
            {'type': 'chart_line', 'use_for': 'Trends over time, continuous data'},
            {'type': 'chart_bar', 'use_for': 'Comparisons across categories'},
            {'type': 'chart_pie', 'use_for': 'Distribution, proportions, market share'},
            {'type': 'chart_area', 'use_for': 'Cumulative trends, stacked comparisons'},
            {'type': 'kpi', 'use_for': 'Single key metrics with trend indicators'},
            {'type': 'table', 'use_for': 'Detailed record lists with sorting/filtering'},
            {'type': 'filter', 'use_for': 'User-controlled data filtering'},
            {'type': 'gauge', 'use_for': 'Progress toward targets, percentages'},
        ]

    def _get_sales_template(self):
        """Pre-built sales dashboard template."""
        return {
            'name': 'Sales Overview Dashboard',
            'description': 'Key sales metrics and trends',
            'widgets': [
                {
                    'name': 'Total Revenue',
                    'type': 'kpi',
                    'position': {'x': 0, 'y': 0},
                    'size': {'width': 3, 'height': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                        'measure_field': 'amount_total',
                        'aggregation': 'sum',
                    },
                    'config': {'format': 'currency', 'trend': 'up'},
                },
                {
                    'name': 'Orders Count',
                    'type': 'kpi',
                    'position': {'x': 3, 'y': 0},
                    'size': {'width': 3, 'height': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Revenue Trend',
                    'type': 'chart_line',
                    'position': {'x': 0, 'y': 2},
                    'size': {'width': 8, 'height': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                        'group_by': 'date_order:month',
                        'measure_field': 'amount_total',
                        'aggregation': 'sum',
                    },
                },
                {
                    'name': 'Top Customers',
                    'type': 'table',
                    'position': {'x': 8, 'y': 2},
                    'size': {'width': 4, 'height': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                        'group_by': 'partner_id',
                        'measure_field': 'amount_total',
                        'aggregation': 'sum',
                    },
                    'config': {'page_size': 5, 'sort': 'desc'},
                },
            ],
            'filters': [
                {
                    'name': 'Date Range',
                    'field': 'date_order',
                    'type': 'date_range',
                    'affects_widgets': [0, 1, 2, 3],
                }
            ],
        }

    # Additional template methods...
    def _get_inventory_template(self):
        return {'name': 'Inventory Dashboard', 'widgets': [], 'filters': []}

    def _get_hr_template(self):
        return {'name': 'HR Dashboard', 'widgets': [], 'filters': []}

    def _get_crm_template(self):
        return {'name': 'CRM Dashboard', 'widgets': [], 'filters': []}

    def _get_generic_template(self):
        return {'name': 'Custom Dashboard', 'widgets': [], 'filters': []}
```

### 7. Dashboard Builder React Components

#### 7.1 Dashboard Canvas (`odoo/addons/web/static/src/views/dashboard/builder/DashboardCanvas.jsx`)

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

import { ChartNode, KPINode, TableNode, FilterNode, GaugeNode } from './nodes';
import { WidgetToolbox } from './panels/WidgetToolbox';
import { PropertyPanel } from './panels/PropertyPanel';
import { useOdoo } from '@web/core/react_provider/OdooContext';
import { useDashboardState } from './hooks/useDashboardState';
import { useRealTimeUpdates } from './hooks/useRealTimeUpdates';

import '@xyflow/react/dist/style.css';
import './dashboard.css';

// Node type registry
const nodeTypes = {
    chart: ChartNode,
    kpi: KPINode,
    table: TableNode,
    filter: FilterNode,
    gauge: GaugeNode,
};

function DashboardCanvasInner({
    config,
    data,
    mode = 'view',
    onSave,
    onWidgetAction,
    onFetchData,
}) {
    const reactFlowWrapper = useRef(null);
    const { screenToFlowPosition } = useReactFlow();
    const { notification } = useOdoo();

    // State management
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
    } = useDashboardState(config, data);

    const [showToolbox, setShowToolbox] = useState(mode === 'edit');
    const [showProperties, setShowProperties] = useState(false);
    const [isDirty, setIsDirty] = useState(false);

    // Real-time updates
    useRealTimeUpdates({
        enabled: config.autoRefresh > 0 && mode === 'view',
        interval: config.autoRefresh * 1000,
        onRefresh: async () => {
            await refreshAllWidgets();
        },
    });

    // Initial data fetch
    useEffect(() => {
        refreshAllWidgets();
    }, [filters]);

    const refreshAllWidgets = async () => {
        const updates = {};
        for (const node of nodes) {
            if (node.data.dataSourceId) {
                try {
                    const result = await onFetchData(node.data.dataSourceId, filters);
                    updates[node.id] = result;
                } catch (error) {
                    console.error(`Failed to fetch data for widget ${node.id}:`, error);
                }
            }
        }
        setWidgetData(prev => ({ ...prev, ...updates }));
    };

    // Drag and drop for new widgets
    const onDragOver = useCallback((event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        async (event) => {
            event.preventDefault();
            if (mode !== 'edit') return;

            const widgetType = event.dataTransfer.getData('application/dashboard-widget');
            if (!widgetType) return;

            const position = screenToFlowPosition({
                x: event.clientX,
                y: event.clientY,
            });

            const newNode = {
                id: `widget-${Date.now()}`,
                type: getNodeType(widgetType),
                position,
                data: {
                    label: `New ${widgetType} Widget`,
                    widgetType,
                    config: {},
                    dataSourceId: null,
                },
            };

            setNodes((nds) => [...nds, newNode]);
            setIsDirty(true);
        },
        [screenToFlowPosition, mode]
    );

    // Filter connections
    const onConnect = useCallback(
        (params) => {
            const sourceNode = nodes.find(n => n.id === params.source);
            if (sourceNode?.data.widgetType !== 'filter') {
                notification.add('Only filter widgets can connect to other widgets', { type: 'warning' });
                return;
            }

            setEdges((eds) => addEdge({
                ...params,
                type: 'smoothstep',
                animated: true,
                style: { stroke: '#6366f1' },
            }, eds));
            setIsDirty(true);
        },
        [nodes, notification]
    );

    // Node selection
    const onNodeClick = useCallback((event, node) => {
        setSelectedNode(node);
        if (mode === 'edit') {
            setShowProperties(true);
        }
    }, [mode]);

    // Save handler
    const handleSave = useCallback(async () => {
        if (!onSave) return;

        try {
            await onSave({
                nodes: nodes.map(n => ({
                    id: n.id,
                    type: n.type,
                    position: n.position,
                    data: n.data,
                })),
                edges,
            });
            setIsDirty(false);
            notification.add('Dashboard saved successfully', { type: 'success' });
        } catch (error) {
            notification.add('Failed to save dashboard', { type: 'danger' });
        }
    }, [nodes, edges, onSave, notification]);

    // Widget action handler (drill-down, open record)
    const handleWidgetClick = useCallback((action) => {
        if (onWidgetAction) {
            onWidgetAction(action);
        }
    }, [onWidgetAction]);

    return (
        <div className="lw-dashboard-container">
            {mode === 'edit' && showToolbox && (
                <WidgetToolbox onClose={() => setShowToolbox(false)} />
            )}

            <div className="lw-dashboard-canvas" ref={reactFlowWrapper}>
                <ReactFlow
                    nodes={nodes.map(n => ({
                        ...n,
                        data: {
                            ...n.data,
                            widgetData: widgetData[n.id],
                            filters,
                            onAction: handleWidgetClick,
                        },
                    }))}
                    edges={edges}
                    onNodesChange={(changes) => {
                        onNodesChange(changes);
                        if (changes.some(c => c.type === 'position')) {
                            setIsDirty(true);
                        }
                    }}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    onNodeClick={onNodeClick}
                    nodeTypes={nodeTypes}
                    fitView
                    snapToGrid
                    snapGrid={[20, 20]}
                    nodesDraggable={mode === 'edit'}
                    nodesConnectable={mode === 'edit'}
                    elementsSelectable={mode === 'edit'}
                    minZoom={0.25}
                    maxZoom={2}
                >
                    <Controls />
                    <Background variant="dots" gap={20} size={1} />
                    <MiniMap nodeStrokeWidth={3} zoomable pannable />

                    <Panel position="top-left" className="lw-dashboard-toolbar">
                        {mode === 'edit' && (
                            <>
                                <button
                                    className="lw-btn lw-btn-secondary"
                                    onClick={() => setShowToolbox(true)}
                                >
                                    <i className="fa fa-plus" /> Add Widget
                                </button>
                                <button
                                    className={`lw-btn ${isDirty ? 'lw-btn-primary' : 'lw-btn-secondary'}`}
                                    onClick={handleSave}
                                    disabled={!isDirty}
                                >
                                    <i className="fa fa-save" /> Save
                                </button>
                            </>
                        )}
                        <button
                            className="lw-btn lw-btn-secondary"
                            onClick={refreshAllWidgets}
                        >
                            <i className="fa fa-refresh" /> Refresh
                        </button>
                    </Panel>
                </ReactFlow>
            </div>

            {mode === 'edit' && showProperties && selectedNode && (
                <PropertyPanel
                    node={selectedNode}
                    onUpdate={(updates) => {
                        setNodes(nds => nds.map(n =>
                            n.id === selectedNode.id
                                ? { ...n, data: { ...n.data, ...updates } }
                                : n
                        ));
                        setIsDirty(true);
                    }}
                    onDelete={() => {
                        setNodes(nds => nds.filter(n => n.id !== selectedNode.id));
                        setEdges(eds => eds.filter(e =>
                            e.source !== selectedNode.id && e.target !== selectedNode.id
                        ));
                        setSelectedNode(null);
                        setShowProperties(false);
                        setIsDirty(true);
                    }}
                    onClose={() => setShowProperties(false)}
                />
            )}
        </div>
    );
}

function getNodeType(widgetType) {
    if (widgetType.startsWith('chart_')) return 'chart';
    if (widgetType === 'kpi') return 'kpi';
    if (widgetType === 'table') return 'table';
    if (widgetType === 'filter') return 'filter';
    if (widgetType === 'gauge') return 'gauge';
    return 'chart';
}

export function DashboardCanvas(props) {
    return (
        <ReactFlowProvider>
            <DashboardCanvasInner {...props} />
        </ReactFlowProvider>
    );
}

export default DashboardCanvas;
```

---

## Implementation Steps

### Milestone 1: Core View Infrastructure (Week 31-32)

- [ ] 1.1 Fork Odoo v18 and set up development branch
- [ ] 1.2 Create `odoo/addons/web/static/src/views/dashboard/` directory structure
- [ ] 1.3 Implement `DashboardController` following Odoo's view pattern
- [ ] 1.4 Implement `DashboardArchParser` for `<dashboard>` XML parsing
- [ ] 1.5 Implement `DashboardModel` for data management
- [ ] 1.6 Implement `DashboardRenderer` with Owl template
- [ ] 1.7 Register dashboard view type in core registry
- [ ] 1.8 Create Owl templates for dashboard view

### Milestone 2: React Bridge in Core (Week 32-33)

- [ ] 2.1 Create `odoo/addons/web/static/src/core/react_bridge/` infrastructure
- [ ] 2.2 Implement `ReactBridgeService` as core Odoo service
- [ ] 2.3 Create `OdooContextProvider` for React-Odoo integration
- [ ] 2.4 Vendor React 18 and ReactDOM in `web/static/lib/react/`
- [ ] 2.5 Configure asset bundling in web module manifest
- [ ] 2.6 Write tests for React mounting/unmounting lifecycle
- [ ] 2.7 Document React bridge API for addon developers

### Milestone 3: Unified Charting with Recharts (Week 33-34)

- [ ] 3.1 Vendor Recharts in `web/static/lib/recharts/`
- [ ] 3.2 Create `RechartsGraph` React component with all chart types
- [ ] 3.3 Modify `GraphRenderer` to use React bridge and Recharts
- [ ] 3.4 Update `PivotRenderer` to use Recharts for visualizations
- [ ] 3.5 Ensure backward compatibility with existing graph/pivot views
- [ ] 3.6 Add color theme support matching Odoo's design system
- [ ] 3.7 Performance test with large datasets (10k+ records)

### Milestone 4: Dashboard Builder Components (Week 34-35)

- [ ] 4.1 Set up Vite build pipeline for React components
- [ ] 4.2 Implement `DashboardCanvas` with React Flow
- [ ] 4.3 Create `ChartNode` with all chart type support
- [ ] 4.4 Create `KPINode` with trend indicators and sparklines
- [ ] 4.5 Create `TableNode` with pagination and sorting
- [ ] 4.6 Create `FilterNode` with all filter types
- [ ] 4.7 Create `GaugeNode` for progress visualization
- [ ] 4.8 Implement `WidgetToolbox` for drag-drop widget creation
- [ ] 4.9 Implement `PropertyPanel` for widget configuration

### Milestone 5: Dashboard Persistence Module (Week 35-36)

- [ ] 5.1 Create `loomworks_dashboard` module scaffold
- [ ] 5.2 Implement `dashboard.board` model with all fields
- [ ] 5.3 Implement `dashboard.widget` model with position/config
- [ ] 5.4 Implement `dashboard.data_source` model with connectors
- [ ] 5.5 Create REST API controllers for CRUD operations
- [ ] 5.6 Implement security rules and access rights
- [ ] 5.7 Write unit tests for all models
- [ ] 5.8 Create admin views for dashboard management

### Milestone 6: AI Dashboard Generation (Week 36-37)

- [ ] 6.1 Create `dashboard.ai.service` abstract model
- [ ] 6.2 Implement AI generation with Claude integration
- [ ] 6.3 Implement template-based fallback generation
- [ ] 6.4 Build model/field discovery for AI context
- [ ] 6.5 Create pre-built dashboard templates (Sales, Inventory, HR, CRM)
- [ ] 6.6 Add "Generate with AI" button to dashboard builder UI
- [ ] 6.7 Test AI generation with various natural language prompts
- [ ] 6.8 Document AI generation capabilities and limitations

### Milestone 7: Data Integration & Real-Time (Week 37-38)

- [ ] 7.1 Implement `useOdooData` React hook for data fetching
- [ ] 7.2 Create data transformation utilities (Odoo -> Recharts format)
- [ ] 7.3 Implement filter -> widget data flow with edge connections
- [ ] 7.4 Add `useRealTimeUpdates` hook with configurable polling
- [ ] 7.5 Implement data caching layer for performance
- [ ] 7.6 Add WebSocket support preparation (optional)
- [ ] 7.7 Performance optimization (lazy loading, virtualization)

### Milestone 8: Polish & Documentation (Week 38)

- [ ] 8.1 Create demo dashboards for common use cases
- [ ] 8.2 Implement dashboard sharing and permissions
- [ ] 8.3 Add export functionality (PNG, PDF)
- [ ] 8.4 Accessibility audit (WCAG 2.1 AA compliance)
- [ ] 8.5 Write integration tests for full workflows
- [ ] 8.6 Create developer documentation for extending dashboards
- [ ] 8.7 Create user documentation for dashboard builder
- [ ] 8.8 Performance benchmarking and optimization

---

## Testing Criteria

### Unit Tests

| Test Area | Test Cases |
|-----------|------------|
| Dashboard view registration | View type registered in core, arch parsing works |
| React bridge service | Mount, unmount, update, error handling |
| `dashboard.board` model | Create, read, update, delete, permissions |
| `dashboard.widget` model | All widget types, position serialization |
| `dashboard.data_source` | Model fetch, aggregation, filtering |
| AI generation | Prompt parsing, spec generation, fallback |

### Integration Tests

| Test Area | Test Cases |
|-----------|------------|
| Dashboard view rendering | Dashboard loads in Odoo action, widgets display |
| React-Owl communication | Props flow, callbacks invoke RPC correctly |
| Widget data flow | Data source -> Widget -> Chart renders |
| Filter connections | Filter changes propagate to connected widgets |
| Graph view compatibility | Existing graph views work with Recharts |

### Visual/UI Tests

| Test Area | Test Cases |
|-----------|------------|
| Drag-drop builder | Widgets drag from toolbox, drop on canvas |
| Widget resize | NodeResizer works, minimum sizes enforced |
| All chart types | Line, bar, pie, area render with sample data |
| Responsive layout | Dashboard adapts to different screen sizes |
| Dark mode support | Dashboards render correctly in dark theme |

### Performance Tests

| Metric | Target |
|--------|--------|
| Dashboard load time | < 1 second (20 widgets) |
| Data refresh | < 3 seconds (10k records) |
| Drag-drop framerate | 60fps smooth |
| Memory usage | < 100MB (complex dashboard) |
| React bundle size | < 500KB gzipped |

---

## Success Criteria

1. **Core Integration**
   - Dashboard is a native Odoo view type (works with actions, menus, favorites)
   - React bridge is a documented, stable core service
   - Graph/pivot views use unified Recharts implementation
   - No regressions in existing Odoo view functionality

2. **Functional Requirements**
   - Users can create dashboards via drag-drop builder
   - All widget types render correctly with live data
   - Filters affect connected widgets in real-time
   - AI generates usable dashboards from natural language
   - Dashboards persist and reload correctly

3. **Performance Requirements**
   - Dashboard canvas loads in < 1 second
   - Data refresh completes in < 3 seconds
   - Smooth 60fps drag-drop interactions
   - Memory usage < 100MB for complex dashboards

4. **Quality Requirements**
   - 80%+ test coverage on backend models and core services
   - No console errors in production builds
   - LGPL v3 compliance for all code
   - Accessible (WCAG 2.1 AA) color contrast and keyboard navigation

5. **Developer Experience**
   - Clear API for creating custom widget types
   - Documentation for React component development in Odoo
   - Type definitions for TypeScript users (optional)

---

## References

### Odoo View Architecture
- [Customize a view type - Odoo 18.0 documentation](https://www.odoo.com/documentation/18.0/developer/howtos/javascript_view.html)
- [How to Create a New View Type in Odoo 18](https://www.cybrosys.com/blog/how-to-create-a-new-view-type-in-odoo-18)
- [View architectures - Odoo 18.0 documentation](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_architectures.html)

### Odoo Frontend Development
- [Owl components - Odoo 18.0 documentation](https://www.odoo.com/documentation/18.0/developer/reference/frontend/owl_components.html)
- [Assets - Odoo 18.0 documentation](https://www.odoo.com/documentation/18.0/developer/reference/frontend/assets.html)
- [JavaScript Modules - Odoo 18.0 documentation](https://www.odoo.com/documentation/18.0/developer/reference/frontend/javascript_modules.html)

### React Integration
- [React Flow Documentation](https://reactflow.dev)
- [Recharts Documentation](https://recharts.org)
- [Gridstack.js Documentation](https://gridstackjs.com)

### AI Dashboard Generation
- [AI Dashboard Generator Tools](https://clickup.com/blog/ai-dashboard-generators/)
- [Natural Language Analytics](https://dashboardbuilder.net/ai-driven-dashboard)
- [How To Use AI for Data Visualizations](https://www.gooddata.com/blog/how-to-use-ai-for-data-visualizations-and-dashboards/)

### Research Sources (Context7)
- Odoo 18.0 Developer documentation: `/websites/odoo_18_0_developer`
- Recharts library: `/recharts/recharts`
