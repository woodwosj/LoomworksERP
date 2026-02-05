/**
 * ChartWidget - Chart visualization widget
 *
 * Supports multiple chart types using Recharts:
 * - Line chart (chart_line)
 * - Bar chart (chart_bar)
 * - Area chart (chart_area)
 * - Pie chart (chart_pie)
 */

const { useMemo } = React;

// Default color palette
const DEFAULT_COLORS = [
    '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
    '#f97316', '#eab308', '#22c55e', '#14b8a6',
    '#06b6d4', '#3b82f6',
];

function ChartWidget({ widget, data, filters, mode, onAction }) {
    // Transform data for Recharts
    const chartData = useMemo(() => {
        if (!data || data.error) return [];

        if (data.type === 'grouped' && data.data) {
            return data.data.map(item => ({
                name: item.name || 'Unknown',
                value: item.value || 0,
            }));
        }

        if (Array.isArray(data.data)) {
            return data.data;
        }

        return [];
    }, [data]);

    // Get chart type
    const chartType = widget.type.replace('chart_', '');

    // Get colors
    const colors = useMemo(() => {
        if (widget.config?.colors && widget.config.colors.length > 0) {
            return widget.config.colors;
        }
        return DEFAULT_COLORS;
    }, [widget.config]);

    // Error state
    if (data?.error) {
        return (
            <div className="lw-chart-widget lw-chart-error">
                <div className="lw-chart-error-message">
                    <i className="fa fa-exclamation-triangle"></i>
                    <span>Failed to load chart data</span>
                </div>
            </div>
        );
    }

    // Loading state
    if (!data) {
        return (
            <div className="lw-chart-widget lw-chart-loading">
                <div className="lw-chart-loading-spinner">
                    <i className="fa fa-spinner fa-spin fa-2x"></i>
                </div>
            </div>
        );
    }

    // Empty state
    if (chartData.length === 0) {
        return (
            <div className="lw-chart-widget lw-chart-empty">
                <i className="fa fa-bar-chart text-muted"></i>
                <span>No data available</span>
            </div>
        );
    }

    // Check if Recharts is available
    if (typeof Recharts === 'undefined') {
        return (
            <div className="lw-chart-widget lw-chart-fallback">
                <FallbackChart data={chartData} type={chartType} colors={colors} />
            </div>
        );
    }

    // Render using Recharts
    const {
        ResponsiveContainer,
        LineChart, Line,
        BarChart, Bar,
        AreaChart, Area,
        PieChart, Pie, Cell,
        XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    } = Recharts;

    const showLegend = widget.config?.showLegend !== false;
    const showGrid = widget.config?.showGrid !== false;
    const stacked = widget.config?.stacked || false;

    const renderChart = () => {
        switch (chartType) {
            case 'line':
                return (
                    <LineChart data={chartData}>
                        {showGrid && <CartesianGrid strokeDasharray="3 3" />}
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        {showLegend && <Legend />}
                        <Line
                            type="monotone"
                            dataKey="value"
                            stroke={colors[0]}
                            strokeWidth={2}
                            dot={{ r: 3 }}
                            activeDot={{ r: 5 }}
                        />
                    </LineChart>
                );

            case 'bar':
                return (
                    <BarChart data={chartData}>
                        {showGrid && <CartesianGrid strokeDasharray="3 3" />}
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        {showLegend && <Legend />}
                        <Bar dataKey="value" fill={colors[0]}>
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                            ))}
                        </Bar>
                    </BarChart>
                );

            case 'area':
                return (
                    <AreaChart data={chartData}>
                        {showGrid && <CartesianGrid strokeDasharray="3 3" />}
                        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                        <YAxis tick={{ fontSize: 11 }} />
                        <Tooltip />
                        {showLegend && <Legend />}
                        <Area
                            type="monotone"
                            dataKey="value"
                            stroke={colors[0]}
                            fill={colors[0]}
                            fillOpacity={0.3}
                        />
                    </AreaChart>
                );

            case 'pie':
                return (
                    <PieChart>
                        <Pie
                            data={chartData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius="70%"
                            label={({ name, percent }) =>
                                `${name}: ${(percent * 100).toFixed(0)}%`
                            }
                            labelLine={false}
                        >
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                            ))}
                        </Pie>
                        <Tooltip />
                        {showLegend && <Legend />}
                    </PieChart>
                );

            default:
                return <div>Unknown chart type: {chartType}</div>;
        }
    };

    return (
        <div className="lw-chart-widget">
            <ResponsiveContainer width="100%" height="100%">
                {renderChart()}
            </ResponsiveContainer>
        </div>
    );
}

/**
 * Fallback chart using CSS when Recharts is not available
 */
function FallbackChart({ data, type, colors }) {
    const maxValue = Math.max(...data.map(d => d.value));

    if (type === 'pie') {
        const total = data.reduce((sum, d) => sum + d.value, 0);
        let cumulativePercent = 0;

        return (
            <div className="lw-fallback-pie">
                <div className="lw-fallback-pie-chart">
                    {/* Simple list representation for pie */}
                    {data.map((item, index) => {
                        const percent = (item.value / total) * 100;
                        return (
                            <div key={index} className="lw-fallback-pie-item">
                                <span
                                    className="lw-fallback-pie-color"
                                    style={{ backgroundColor: colors[index % colors.length] }}
                                ></span>
                                <span className="lw-fallback-pie-label">{item.name}</span>
                                <span className="lw-fallback-pie-value">{percent.toFixed(1)}%</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }

    // Bar/Line chart fallback
    return (
        <div className="lw-fallback-bar">
            {data.map((item, index) => (
                <div key={index} className="lw-fallback-bar-item">
                    <div className="lw-fallback-bar-label">{item.name}</div>
                    <div className="lw-fallback-bar-track">
                        <div
                            className="lw-fallback-bar-fill"
                            style={{
                                width: `${(item.value / maxValue) * 100}%`,
                                backgroundColor: colors[index % colors.length],
                            }}
                        ></div>
                    </div>
                    <div className="lw-fallback-bar-value">
                        {new Intl.NumberFormat().format(item.value)}
                    </div>
                </div>
            ))}
        </div>
    );
}

// Export globally
window.ChartWidget = ChartWidget;
