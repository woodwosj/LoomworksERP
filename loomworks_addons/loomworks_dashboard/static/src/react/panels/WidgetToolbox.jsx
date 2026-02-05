/**
 * WidgetToolbox - Widget selection panel for adding new widgets
 *
 * Displays available widget types with drag-drop support
 */

const { useState, useCallback } = React;

const WIDGET_TYPES = [
    {
        type: 'kpi',
        name: 'KPI Card',
        description: 'Single metric with trend',
        icon: 'fa-tachometer',
        defaultSize: { w: 3, h: 2 },
    },
    {
        type: 'chart_line',
        name: 'Line Chart',
        description: 'Trends over time',
        icon: 'fa-line-chart',
        defaultSize: { w: 6, h: 4 },
    },
    {
        type: 'chart_bar',
        name: 'Bar Chart',
        description: 'Compare categories',
        icon: 'fa-bar-chart',
        defaultSize: { w: 6, h: 4 },
    },
    {
        type: 'chart_area',
        name: 'Area Chart',
        description: 'Cumulative trends',
        icon: 'fa-area-chart',
        defaultSize: { w: 6, h: 4 },
    },
    {
        type: 'chart_pie',
        name: 'Pie Chart',
        description: 'Show proportions',
        icon: 'fa-pie-chart',
        defaultSize: { w: 4, h: 4 },
    },
    {
        type: 'table',
        name: 'Data Table',
        description: 'List of records',
        icon: 'fa-table',
        defaultSize: { w: 6, h: 4 },
    },
    {
        type: 'gauge',
        name: 'Gauge',
        description: 'Progress to target',
        icon: 'fa-dashboard',
        defaultSize: { w: 3, h: 3 },
    },
    {
        type: 'filter',
        name: 'Filter',
        description: 'Global filter control',
        icon: 'fa-filter',
        defaultSize: { w: 3, h: 2 },
    },
];

function WidgetToolbox({ onAddWidget, onClose }) {
    const [selectedType, setSelectedType] = useState(null);
    const [showConfig, setShowConfig] = useState(false);
    const [widgetConfig, setWidgetConfig] = useState({
        name: '',
        model: '',
        measureField: '',
        groupBy: '',
        aggregation: 'sum',
    });

    // Handle quick add (with defaults)
    const handleQuickAdd = useCallback((widgetType) => {
        const type = WIDGET_TYPES.find(t => t.type === widgetType);
        if (!type) return;

        onAddWidget({
            name: type.name,
            type: type.type,
            position: { x: 0, y: 0 },
            size: type.defaultSize,
            config: {},
            inlineDataSource: null,
        });
    }, [onAddWidget]);

    // Handle configured add
    const handleConfiguredAdd = useCallback(() => {
        if (!selectedType || !widgetConfig.name) return;

        const type = WIDGET_TYPES.find(t => t.type === selectedType);

        const widget = {
            name: widgetConfig.name,
            type: selectedType,
            position: { x: 0, y: 0 },
            size: type?.defaultSize || { w: 4, h: 3 },
            config: {
                format: widgetConfig.format || 'number',
            },
            inlineDataSource: widgetConfig.model ? {
                type: 'model',
                model: widgetConfig.model,
                domain: [],
                groupBy: widgetConfig.groupBy,
                measureField: widgetConfig.measureField,
                aggregation: widgetConfig.aggregation,
            } : null,
        };

        onAddWidget(widget);
        setShowConfig(false);
        setSelectedType(null);
        setWidgetConfig({
            name: '',
            model: '',
            measureField: '',
            groupBy: '',
            aggregation: 'sum',
        });
    }, [selectedType, widgetConfig, onAddWidget]);

    // Handle drag start
    const handleDragStart = useCallback((e, widgetType) => {
        e.dataTransfer.setData('application/dashboard-widget', widgetType);
        e.dataTransfer.effectAllowed = 'copy';
    }, []);

    return (
        <div className="lw-widget-toolbox">
            <div className="lw-toolbox-header">
                <h5>Add Widget</h5>
                <button className="lw-toolbox-close" onClick={onClose}>
                    <i className="fa fa-times"></i>
                </button>
            </div>

            {!showConfig ? (
                <div className="lw-toolbox-content">
                    <div className="lw-toolbox-widgets">
                        {WIDGET_TYPES.map((type) => (
                            <div
                                key={type.type}
                                className="lw-toolbox-widget"
                                draggable
                                onDragStart={(e) => handleDragStart(e, type.type)}
                                onClick={() => handleQuickAdd(type.type)}
                            >
                                <div className="lw-toolbox-widget-icon">
                                    <i className={`fa ${type.icon}`}></i>
                                </div>
                                <div className="lw-toolbox-widget-info">
                                    <div className="lw-toolbox-widget-name">{type.name}</div>
                                    <div className="lw-toolbox-widget-desc">{type.description}</div>
                                </div>
                                <button
                                    className="lw-toolbox-config-btn"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setSelectedType(type.type);
                                        setWidgetConfig(prev => ({ ...prev, name: type.name }));
                                        setShowConfig(true);
                                    }}
                                    title="Configure"
                                >
                                    <i className="fa fa-cog"></i>
                                </button>
                            </div>
                        ))}
                    </div>

                    <div className="lw-toolbox-tip">
                        <i className="fa fa-lightbulb-o"></i>
                        Click to add, or drag to position
                    </div>
                </div>
            ) : (
                <div className="lw-toolbox-config">
                    <div className="lw-config-header">
                        <button
                            className="lw-config-back"
                            onClick={() => setShowConfig(false)}
                        >
                            <i className="fa fa-arrow-left"></i> Back
                        </button>
                        <span>Configure {WIDGET_TYPES.find(t => t.type === selectedType)?.name}</span>
                    </div>

                    <div className="lw-config-form">
                        <div className="lw-config-field">
                            <label>Widget Name</label>
                            <input
                                type="text"
                                value={widgetConfig.name}
                                onChange={(e) => setWidgetConfig(prev => ({ ...prev, name: e.target.value }))}
                                placeholder="Enter widget name"
                            />
                        </div>

                        <div className="lw-config-field">
                            <label>Data Model</label>
                            <select
                                value={widgetConfig.model}
                                onChange={(e) => setWidgetConfig(prev => ({ ...prev, model: e.target.value }))}
                            >
                                <option value="">Select model...</option>
                                <option value="sale.order">Sales Orders</option>
                                <option value="purchase.order">Purchase Orders</option>
                                <option value="account.move">Journal Entries</option>
                                <option value="stock.picking">Transfers</option>
                                <option value="crm.lead">CRM Leads</option>
                                <option value="hr.employee">Employees</option>
                                <option value="project.task">Tasks</option>
                                <option value="res.partner">Partners</option>
                            </select>
                        </div>

                        {selectedType !== 'filter' && (
                            <>
                                <div className="lw-config-field">
                                    <label>Measure Field</label>
                                    <input
                                        type="text"
                                        value={widgetConfig.measureField}
                                        onChange={(e) => setWidgetConfig(prev => ({ ...prev, measureField: e.target.value }))}
                                        placeholder="e.g., amount_total, id"
                                    />
                                </div>

                                <div className="lw-config-field">
                                    <label>Aggregation</label>
                                    <select
                                        value={widgetConfig.aggregation}
                                        onChange={(e) => setWidgetConfig(prev => ({ ...prev, aggregation: e.target.value }))}
                                    >
                                        <option value="sum">Sum</option>
                                        <option value="avg">Average</option>
                                        <option value="count">Count</option>
                                        <option value="min">Minimum</option>
                                        <option value="max">Maximum</option>
                                    </select>
                                </div>

                                {selectedType?.startsWith('chart_') && (
                                    <div className="lw-config-field">
                                        <label>Group By</label>
                                        <input
                                            type="text"
                                            value={widgetConfig.groupBy}
                                            onChange={(e) => setWidgetConfig(prev => ({ ...prev, groupBy: e.target.value }))}
                                            placeholder="e.g., date_order:month, state"
                                        />
                                    </div>
                                )}
                            </>
                        )}
                    </div>

                    <div className="lw-config-actions">
                        <button
                            className="lw-btn lw-btn-secondary"
                            onClick={() => setShowConfig(false)}
                        >
                            Cancel
                        </button>
                        <button
                            className="lw-btn lw-btn-primary"
                            onClick={handleConfiguredAdd}
                            disabled={!widgetConfig.name}
                        >
                            Add Widget
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

// Export globally
window.WidgetToolbox = WidgetToolbox;
