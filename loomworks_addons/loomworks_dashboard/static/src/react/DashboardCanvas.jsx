/**
 * DashboardCanvas - Gridstack-based dashboard canvas
 *
 * Uses Gridstack.js for drag-drop widget placement and resizing.
 * Renders widget components inside the grid items.
 */

const { useState, useEffect, useRef, useCallback } = React;

// Widget component mapping
const WIDGET_COMPONENTS = {
    kpi: 'KPIWidget',
    chart_line: 'ChartWidget',
    chart_bar: 'ChartWidget',
    chart_area: 'ChartWidget',
    chart_pie: 'ChartWidget',
    table: 'TableWidget',
    filter: 'FilterWidget',
    gauge: 'GaugeWidget',
};

function DashboardCanvas({
    widgets,
    widgetData,
    filters,
    mode,
    layoutColumns = 12,
    onWidgetChange,
    onWidgetSelect,
    onWidgetAction,
    onDeleteWidget,
}) {
    const gridRef = useRef(null);
    const gridInstanceRef = useRef(null);

    // Initialize Gridstack
    useEffect(() => {
        if (!gridRef.current || gridInstanceRef.current) return;

        // Check if GridStack is available
        if (typeof GridStack === 'undefined') {
            console.error('GridStack not loaded');
            return;
        }

        // Initialize grid
        const grid = GridStack.init({
            column: layoutColumns,
            cellHeight: 80,
            minRow: 1,
            float: true,
            animate: true,
            resizable: {
                handles: mode === 'edit' ? 'e, se, s, sw, w' : '',
            },
            draggable: {
                handle: '.lw-widget-header',
            },
            disableDrag: mode !== 'edit',
            disableResize: mode !== 'edit',
        }, gridRef.current);

        gridInstanceRef.current = grid;

        // Handle widget movement
        grid.on('dragstop', (event, el) => {
            const node = el.gridstackNode;
            if (node && onWidgetChange) {
                onWidgetChange(node.id, {
                    position: { x: node.x, y: node.y },
                });
            }
        });

        // Handle widget resize
        grid.on('resizestop', (event, el) => {
            const node = el.gridstackNode;
            if (node && onWidgetChange) {
                onWidgetChange(node.id, {
                    size: { w: node.w, h: node.h },
                });
            }
        });

        return () => {
            if (gridInstanceRef.current) {
                gridInstanceRef.current.destroy(false);
                gridInstanceRef.current = null;
            }
        };
    }, [layoutColumns, mode]);

    // Update grid mode (edit/view)
    useEffect(() => {
        if (!gridInstanceRef.current) return;

        const grid = gridInstanceRef.current;
        if (mode === 'edit') {
            grid.enableMove(true);
            grid.enableResize(true);
        } else {
            grid.enableMove(false);
            grid.enableResize(false);
        }
    }, [mode]);

    // Render widget content
    const renderWidgetContent = useCallback((widget) => {
        const data = widgetData[widget.id];
        const componentName = WIDGET_COMPONENTS[widget.type] || 'KPIWidget';

        const props = {
            widget,
            data,
            filters,
            mode,
            onAction: onWidgetAction,
        };

        // Use the globally registered widget components
        switch (componentName) {
            case 'KPIWidget':
                return <KPIWidget {...props} />;
            case 'ChartWidget':
                return <ChartWidget {...props} />;
            case 'TableWidget':
                return <TableWidget {...props} />;
            case 'FilterWidget':
                return <FilterWidget {...props} />;
            case 'GaugeWidget':
                return <GaugeWidget {...props} />;
            default:
                return <div className="lw-widget-placeholder">Unknown widget type</div>;
        }
    }, [widgetData, filters, mode, onWidgetAction]);

    return (
        <div className="lw-dashboard-canvas">
            <div className="grid-stack" ref={gridRef}>
                {widgets.map(widget => (
                    <div
                        key={widget.id}
                        className="grid-stack-item"
                        gs-id={widget.id}
                        gs-x={widget.position?.x || 0}
                        gs-y={widget.position?.y || 0}
                        gs-w={widget.size?.w || 4}
                        gs-h={widget.size?.h || 3}
                        gs-min-w={widget.minSize?.w || 2}
                        gs-min-h={widget.minSize?.h || 2}
                    >
                        <div className="grid-stack-item-content">
                            <div
                                className={`lw-widget ${mode === 'edit' ? 'lw-widget-editable' : ''}`}
                                onClick={() => onWidgetSelect && onWidgetSelect(widget.id)}
                            >
                                <div className="lw-widget-header">
                                    <span className="lw-widget-title">{widget.name}</span>
                                    {mode === 'edit' && (
                                        <div className="lw-widget-actions">
                                            <button
                                                className="lw-widget-action-btn"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onWidgetSelect && onWidgetSelect(widget.id);
                                                }}
                                                title="Settings"
                                            >
                                                <i className="fa fa-cog"></i>
                                            </button>
                                            <button
                                                className="lw-widget-action-btn lw-widget-action-delete"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    onDeleteWidget && onDeleteWidget(widget.id);
                                                }}
                                                title="Delete"
                                            >
                                                <i className="fa fa-trash"></i>
                                            </button>
                                        </div>
                                    )}
                                </div>
                                <div className="lw-widget-body">
                                    {renderWidgetContent(widget)}
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {widgets.length === 0 && (
                <div className="lw-dashboard-empty">
                    <i className="fa fa-tachometer fa-4x text-muted"></i>
                    <h4>No widgets yet</h4>
                    <p className="text-muted">
                        {mode === 'edit'
                            ? 'Click "Add Widget" to get started'
                            : 'This dashboard is empty'}
                    </p>
                </div>
            )}
        </div>
    );
}

// Export for use in DashboardApp
window.DashboardCanvas = DashboardCanvas;
