/**
 * DashboardApp - Main React application wrapper for Loomworks Dashboard
 *
 * Entry point for the React dashboard canvas. Provides:
 * - Odoo context to all child components
 * - Dashboard state management
 * - Real-time data refresh
 */

const { useState, useEffect, useCallback, createContext, useContext } = React;

// Odoo Context - provides access to Odoo services from React
const OdooContext = createContext(null);

function useOdoo() {
    const context = useContext(OdooContext);
    if (!context) {
        console.warn('useOdoo called outside OdooContext');
        return {};
    }
    return context;
}

// Dashboard App Component
function DashboardApp({
    dashboardId,
    dashboardData,
    mode = 'view',
    onSave,
    onWidgetAction,
    onFetchData,
    onModeChange,
    odooServices = {},
}) {
    const [widgets, setWidgets] = useState([]);
    const [filters, setFilters] = useState({});
    const [widgetData, setWidgetData] = useState({});
    const [isLoading, setIsLoading] = useState(true);
    const [isDirty, setIsDirty] = useState(false);
    const [selectedWidget, setSelectedWidget] = useState(null);
    const [showToolbox, setShowToolbox] = useState(mode === 'edit');

    // Initialize from dashboard data
    useEffect(() => {
        if (dashboardData) {
            setWidgets(dashboardData.widgets || []);
            // Initialize filters with default values
            const initialFilters = {};
            (dashboardData.filters || []).forEach(f => {
                if (f.defaultValue !== null && f.defaultValue !== undefined) {
                    initialFilters[f.fieldName] = f.defaultValue;
                }
            });
            setFilters(initialFilters);
            setIsLoading(false);
        }
    }, [dashboardData]);

    // Fetch data for all widgets
    const refreshAllWidgets = useCallback(async () => {
        if (!onFetchData) return;

        const updates = {};
        for (const widget of widgets) {
            if (widget.dataSourceId || widget.inlineDataSource) {
                try {
                    const data = await onFetchData(widget.id, filters);
                    updates[widget.id] = data;
                } catch (error) {
                    console.error(`Failed to fetch data for widget ${widget.id}:`, error);
                    updates[widget.id] = { error: error.message };
                }
            }
        }
        setWidgetData(prev => ({ ...prev, ...updates }));
    }, [widgets, filters, onFetchData]);

    // Refresh data when filters change
    useEffect(() => {
        refreshAllWidgets();
    }, [filters, refreshAllWidgets]);

    // Auto-refresh
    useEffect(() => {
        if (dashboardData?.autoRefresh && dashboardData.autoRefresh > 0 && mode === 'view') {
            const interval = setInterval(refreshAllWidgets, dashboardData.autoRefresh * 1000);
            return () => clearInterval(interval);
        }
    }, [dashboardData?.autoRefresh, mode, refreshAllWidgets]);

    // Handle widget position/size change
    const handleWidgetChange = useCallback((widgetId, changes) => {
        setWidgets(prev => prev.map(w =>
            w.id === widgetId ? { ...w, ...changes } : w
        ));
        setIsDirty(true);
    }, []);

    // Handle adding a new widget
    const handleAddWidget = useCallback((widgetConfig) => {
        const newWidget = {
            id: `new_${Date.now()}`,
            ...widgetConfig,
        };
        setWidgets(prev => [...prev, newWidget]);
        setIsDirty(true);
    }, []);

    // Handle deleting a widget
    const handleDeleteWidget = useCallback((widgetId) => {
        setWidgets(prev => prev.filter(w => w.id !== widgetId));
        setIsDirty(true);
        setSelectedWidget(null);
    }, []);

    // Handle save
    const handleSave = useCallback(async () => {
        if (!onSave) return;

        const canvasData = {
            widgets: widgets.map(w => ({
                id: w.id,
                name: w.name,
                type: w.type,
                position: w.position,
                size: w.size,
                config: w.config,
                inlineDataSource: w.inlineDataSource,
            })),
            filters,
        };

        const success = await onSave(canvasData);
        if (success) {
            setIsDirty(false);
        }
    }, [widgets, filters, onSave]);

    // Handle filter change
    const handleFilterChange = useCallback((fieldName, value) => {
        setFilters(prev => ({
            ...prev,
            [fieldName]: value,
        }));
    }, []);

    // Odoo context value
    const odooContextValue = {
        services: odooServices,
        rpc: odooServices.rpc,
        notification: odooServices.notification,
        action: odooServices.action,
    };

    if (isLoading) {
        return (
            <div className="lw-dashboard-loading">
                <div className="lw-loading-content">
                    <i className="fa fa-spinner fa-spin fa-3x"></i>
                    <p>Loading dashboard...</p>
                </div>
            </div>
        );
    }

    return (
        <OdooContext.Provider value={odooContextValue}>
            <div className="lw-dashboard-app">
                {/* Toolbar (edit mode) */}
                {mode === 'edit' && (
                    <div className="lw-dashboard-edit-toolbar">
                        <button
                            className="lw-btn lw-btn-secondary"
                            onClick={() => setShowToolbox(!showToolbox)}
                        >
                            <i className="fa fa-plus"></i> Add Widget
                        </button>
                        <button
                            className={`lw-btn ${isDirty ? 'lw-btn-primary' : 'lw-btn-secondary'}`}
                            onClick={handleSave}
                            disabled={!isDirty}
                        >
                            <i className="fa fa-save"></i> Save
                        </button>
                        <button
                            className="lw-btn lw-btn-secondary"
                            onClick={refreshAllWidgets}
                        >
                            <i className="fa fa-refresh"></i> Refresh
                        </button>
                    </div>
                )}

                <div className="lw-dashboard-content">
                    {/* Widget Toolbox */}
                    {mode === 'edit' && showToolbox && (
                        <WidgetToolbox
                            onAddWidget={handleAddWidget}
                            onClose={() => setShowToolbox(false)}
                        />
                    )}

                    {/* Dashboard Canvas */}
                    <DashboardCanvas
                        widgets={widgets}
                        widgetData={widgetData}
                        filters={filters}
                        mode={mode}
                        layoutColumns={dashboardData?.layoutColumns || 12}
                        onWidgetChange={handleWidgetChange}
                        onWidgetSelect={setSelectedWidget}
                        onWidgetAction={onWidgetAction}
                        onDeleteWidget={handleDeleteWidget}
                    />

                    {/* Widget Properties Panel */}
                    {mode === 'edit' && selectedWidget && (
                        <WidgetPropertiesPanel
                            widget={widgets.find(w => w.id === selectedWidget)}
                            onUpdate={(updates) => handleWidgetChange(selectedWidget, updates)}
                            onDelete={() => handleDeleteWidget(selectedWidget)}
                            onClose={() => setSelectedWidget(null)}
                        />
                    )}
                </div>

                {/* Global Filters */}
                {(dashboardData?.filters || []).length > 0 && (
                    <div className="lw-dashboard-filters">
                        {dashboardData.filters.map(filter => (
                            <FilterControl
                                key={filter.id}
                                filter={filter}
                                value={filters[filter.fieldName]}
                                onChange={(value) => handleFilterChange(filter.fieldName, value)}
                            />
                        ))}
                    </div>
                )}
            </div>
        </OdooContext.Provider>
    );
}

// Export for global access
window.LoomworksDashboardApp = DashboardApp;
window.useOdoo = useOdoo;
