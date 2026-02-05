/**
 * WidgetPropertiesPanel - Configuration panel for editing widget properties
 *
 * Allows editing:
 * - Widget name
 * - Data source configuration
 * - Visual options
 * - Widget-specific settings
 */

const { useState, useEffect, useCallback } = React;

function WidgetPropertiesPanel({ widget, onUpdate, onDelete, onClose }) {
    const [localWidget, setLocalWidget] = useState(widget);

    // Sync with external widget changes
    useEffect(() => {
        setLocalWidget(widget);
    }, [widget]);

    // Handle field change
    const handleChange = useCallback((field, value) => {
        setLocalWidget(prev => {
            const updated = { ...prev };

            // Handle nested fields
            if (field.includes('.')) {
                const parts = field.split('.');
                let current = updated;
                for (let i = 0; i < parts.length - 1; i++) {
                    current[parts[i]] = { ...current[parts[i]] };
                    current = current[parts[i]];
                }
                current[parts[parts.length - 1]] = value;
            } else {
                updated[field] = value;
            }

            return updated;
        });
    }, []);

    // Apply changes
    const handleApply = useCallback(() => {
        onUpdate(localWidget);
    }, [localWidget, onUpdate]);

    // Render common settings
    const renderCommonSettings = () => (
        <div className="lw-props-section">
            <h6>General</h6>
            <div className="lw-props-field">
                <label>Widget Name</label>
                <input
                    type="text"
                    value={localWidget.name || ''}
                    onChange={(e) => handleChange('name', e.target.value)}
                />
            </div>
        </div>
    );

    // Render data source settings
    const renderDataSourceSettings = () => (
        <div className="lw-props-section">
            <h6>Data Source</h6>
            <div className="lw-props-field">
                <label>Model</label>
                <select
                    value={localWidget.inlineDataSource?.model || ''}
                    onChange={(e) => handleChange('inlineDataSource.model', e.target.value)}
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

            <div className="lw-props-field">
                <label>Measure Field</label>
                <input
                    type="text"
                    value={localWidget.inlineDataSource?.measureField || ''}
                    onChange={(e) => handleChange('inlineDataSource.measureField', e.target.value)}
                    placeholder="e.g., amount_total"
                />
            </div>

            <div className="lw-props-field">
                <label>Aggregation</label>
                <select
                    value={localWidget.inlineDataSource?.aggregation || 'sum'}
                    onChange={(e) => handleChange('inlineDataSource.aggregation', e.target.value)}
                >
                    <option value="sum">Sum</option>
                    <option value="avg">Average</option>
                    <option value="count">Count</option>
                    <option value="min">Minimum</option>
                    <option value="max">Maximum</option>
                </select>
            </div>

            {localWidget.type?.startsWith('chart_') && (
                <div className="lw-props-field">
                    <label>Group By</label>
                    <input
                        type="text"
                        value={localWidget.inlineDataSource?.groupBy || ''}
                        onChange={(e) => handleChange('inlineDataSource.groupBy', e.target.value)}
                        placeholder="e.g., date_order:month"
                    />
                </div>
            )}
        </div>
    );

    // Render KPI-specific settings
    const renderKPISettings = () => (
        <div className="lw-props-section">
            <h6>KPI Settings</h6>
            <div className="lw-props-field">
                <label>Format</label>
                <select
                    value={localWidget.config?.format || 'number'}
                    onChange={(e) => handleChange('config.format', e.target.value)}
                >
                    <option value="number">Number</option>
                    <option value="currency">Currency</option>
                    <option value="percent">Percentage</option>
                </select>
            </div>

            <div className="lw-props-field">
                <label>Prefix</label>
                <input
                    type="text"
                    value={localWidget.config?.prefix || ''}
                    onChange={(e) => handleChange('config.prefix', e.target.value)}
                    placeholder="e.g., $"
                />
            </div>

            <div className="lw-props-field">
                <label>Suffix</label>
                <input
                    type="text"
                    value={localWidget.config?.suffix || ''}
                    onChange={(e) => handleChange('config.suffix', e.target.value)}
                    placeholder="e.g., %"
                />
            </div>

            <div className="lw-props-field lw-props-checkbox">
                <label>
                    <input
                        type="checkbox"
                        checked={localWidget.config?.showTrend !== false}
                        onChange={(e) => handleChange('config.showTrend', e.target.checked)}
                    />
                    Show Trend Indicator
                </label>
            </div>

            <div className="lw-props-field">
                <label>Target Value</label>
                <input
                    type="number"
                    value={localWidget.config?.target || ''}
                    onChange={(e) => handleChange('config.target', parseFloat(e.target.value) || null)}
                    placeholder="Optional target"
                />
            </div>
        </div>
    );

    // Render chart-specific settings
    const renderChartSettings = () => (
        <div className="lw-props-section">
            <h6>Chart Settings</h6>
            <div className="lw-props-field lw-props-checkbox">
                <label>
                    <input
                        type="checkbox"
                        checked={localWidget.config?.showLegend !== false}
                        onChange={(e) => handleChange('config.showLegend', e.target.checked)}
                    />
                    Show Legend
                </label>
            </div>

            <div className="lw-props-field lw-props-checkbox">
                <label>
                    <input
                        type="checkbox"
                        checked={localWidget.config?.showGrid !== false}
                        onChange={(e) => handleChange('config.showGrid', e.target.checked)}
                    />
                    Show Grid
                </label>
            </div>

            {(localWidget.type === 'chart_bar' || localWidget.type === 'chart_area') && (
                <div className="lw-props-field lw-props-checkbox">
                    <label>
                        <input
                            type="checkbox"
                            checked={localWidget.config?.stacked || false}
                            onChange={(e) => handleChange('config.stacked', e.target.checked)}
                        />
                        Stacked
                    </label>
                </div>
            )}

            <div className="lw-props-field">
                <label>Colors (comma-separated hex)</label>
                <input
                    type="text"
                    value={(localWidget.config?.colors || []).join(',')}
                    onChange={(e) => handleChange('config.colors', e.target.value.split(',').map(c => c.trim()).filter(Boolean))}
                    placeholder="#6366f1,#8b5cf6,#ec4899"
                />
            </div>
        </div>
    );

    // Render table-specific settings
    const renderTableSettings = () => (
        <div className="lw-props-section">
            <h6>Table Settings</h6>
            <div className="lw-props-field">
                <label>Page Size</label>
                <input
                    type="number"
                    value={localWidget.config?.pageSize || 10}
                    onChange={(e) => handleChange('config.pageSize', parseInt(e.target.value) || 10)}
                    min={1}
                    max={100}
                />
            </div>
        </div>
    );

    // Render gauge-specific settings
    const renderGaugeSettings = () => (
        <div className="lw-props-section">
            <h6>Gauge Settings</h6>
            <div className="lw-props-field">
                <label>Target Value</label>
                <input
                    type="number"
                    value={localWidget.config?.target || 100}
                    onChange={(e) => handleChange('config.target', parseFloat(e.target.value) || 100)}
                />
            </div>

            <div className="lw-props-field">
                <label>Format</label>
                <select
                    value={localWidget.config?.format || 'number'}
                    onChange={(e) => handleChange('config.format', e.target.value)}
                >
                    <option value="number">Number</option>
                    <option value="currency">Currency</option>
                    <option value="percent">Percentage</option>
                </select>
            </div>
        </div>
    );

    // Render type-specific settings
    const renderTypeSettings = () => {
        switch (localWidget.type) {
            case 'kpi':
                return renderKPISettings();
            case 'chart_line':
            case 'chart_bar':
            case 'chart_area':
            case 'chart_pie':
                return renderChartSettings();
            case 'table':
                return renderTableSettings();
            case 'gauge':
                return renderGaugeSettings();
            default:
                return null;
        }
    };

    if (!widget) return null;

    return (
        <div className="lw-widget-properties">
            <div className="lw-props-header">
                <h5>Widget Properties</h5>
                <button className="lw-props-close" onClick={onClose}>
                    <i className="fa fa-times"></i>
                </button>
            </div>

            <div className="lw-props-content">
                {renderCommonSettings()}
                {renderDataSourceSettings()}
                {renderTypeSettings()}
            </div>

            <div className="lw-props-actions">
                <button
                    className="lw-btn lw-btn-danger"
                    onClick={() => {
                        if (confirm('Delete this widget?')) {
                            onDelete();
                        }
                    }}
                >
                    <i className="fa fa-trash"></i> Delete
                </button>
                <button
                    className="lw-btn lw-btn-primary"
                    onClick={handleApply}
                >
                    Apply
                </button>
            </div>
        </div>
    );
}

// Export globally
window.WidgetPropertiesPanel = WidgetPropertiesPanel;
