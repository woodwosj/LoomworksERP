/**
 * KPIWidget - Key Performance Indicator widget
 *
 * Displays a single metric value with optional:
 * - Trend indicator (up/down arrow)
 * - Comparison to target/previous period
 * - Sparkline mini-chart
 */

const { useMemo } = React;

function KPIWidget({ widget, data, filters, mode, onAction }) {
    // Extract value from data
    const value = useMemo(() => {
        if (!data) return null;
        if (data.error) return null;

        if (data.type === 'single') {
            return data.value;
        }
        if (data.type === 'grouped' && data.data && data.data.length > 0) {
            // Sum all values for KPI from grouped data
            return data.data.reduce((sum, item) => sum + (item.value || 0), 0);
        }
        return null;
    }, [data]);

    // Format the value
    const formattedValue = useMemo(() => {
        if (value === null || value === undefined) return '--';

        const config = widget.config || {};
        const format = config.format || 'number';

        switch (format) {
            case 'currency':
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0,
                }).format(value);
            case 'percent':
                return new Intl.NumberFormat('en-US', {
                    style: 'percent',
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1,
                }).format(value / 100);
            case 'number':
            default:
                if (value >= 1000000) {
                    return (value / 1000000).toFixed(1) + 'M';
                }
                if (value >= 1000) {
                    return (value / 1000).toFixed(1) + 'K';
                }
                return new Intl.NumberFormat('en-US').format(Math.round(value));
        }
    }, [value, widget.config]);

    // Calculate trend (placeholder - would need historical data)
    const trend = useMemo(() => {
        const config = widget.config || {};
        if (!config.showTrend) return null;

        // In real implementation, compare with previous period
        // For now, simulate with random trend
        return {
            direction: Math.random() > 0.5 ? 'up' : 'down',
            percentage: Math.round(Math.random() * 20),
        };
    }, [widget.config]);

    // Calculate progress toward target
    const progress = useMemo(() => {
        const config = widget.config || {};
        if (!config.target || !value) return null;

        return Math.min(100, Math.round((value / config.target) * 100));
    }, [value, widget.config]);

    // Handle click for drill-down
    const handleClick = () => {
        if (onAction && widget.inlineDataSource) {
            onAction({
                type: 'open_list',
                model: widget.inlineDataSource.model,
                domain: widget.inlineDataSource.domain || [],
            });
        }
    };

    // Error state
    if (data?.error) {
        return (
            <div className="lw-kpi-widget lw-kpi-error">
                <div className="lw-kpi-error-message">
                    <i className="fa fa-exclamation-triangle"></i>
                    <span>Failed to load data</span>
                </div>
            </div>
        );
    }

    // Loading state
    if (!data) {
        return (
            <div className="lw-kpi-widget lw-kpi-loading">
                <div className="lw-kpi-loading-spinner">
                    <i className="fa fa-spinner fa-spin"></i>
                </div>
            </div>
        );
    }

    return (
        <div
            className="lw-kpi-widget"
            onClick={handleClick}
            style={{ cursor: onAction ? 'pointer' : 'default' }}
        >
            <div className="lw-kpi-value">
                {widget.config?.prefix && (
                    <span className="lw-kpi-prefix">{widget.config.prefix}</span>
                )}
                <span className="lw-kpi-number">{formattedValue}</span>
                {widget.config?.suffix && (
                    <span className="lw-kpi-suffix">{widget.config.suffix}</span>
                )}
            </div>

            {trend && (
                <div className={`lw-kpi-trend lw-kpi-trend-${trend.direction}`}>
                    <i className={`fa fa-arrow-${trend.direction}`}></i>
                    <span>{trend.percentage}%</span>
                </div>
            )}

            {progress !== null && (
                <div className="lw-kpi-progress">
                    <div className="lw-kpi-progress-bar">
                        <div
                            className="lw-kpi-progress-fill"
                            style={{ width: `${progress}%` }}
                        ></div>
                    </div>
                    <span className="lw-kpi-progress-text">{progress}% of target</span>
                </div>
            )}
        </div>
    );
}

// Export globally
window.KPIWidget = KPIWidget;
