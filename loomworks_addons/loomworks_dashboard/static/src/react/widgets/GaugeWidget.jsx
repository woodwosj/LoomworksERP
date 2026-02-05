/**
 * GaugeWidget - Progress gauge widget
 *
 * Displays progress toward a target using:
 * - Circular progress indicator
 * - Current value and target
 * - Percentage completion
 */

const { useMemo } = React;

function GaugeWidget({ widget, data, filters, mode, onAction }) {
    // Extract value from data
    const value = useMemo(() => {
        if (!data) return 0;
        if (data.error) return 0;

        if (data.type === 'single') {
            return data.value || 0;
        }
        if (data.type === 'grouped' && data.data && data.data.length > 0) {
            return data.data.reduce((sum, item) => sum + (item.value || 0), 0);
        }
        return 0;
    }, [data]);

    const config = widget.config || {};
    const target = config.target || 100;
    const format = config.format || 'number';

    // Calculate percentage
    const percentage = useMemo(() => {
        if (!target) return 0;
        return Math.min(100, Math.round((value / target) * 100));
    }, [value, target]);

    // Determine color based on percentage
    const color = useMemo(() => {
        if (percentage >= 80) return '#22c55e'; // Green
        if (percentage >= 50) return '#eab308'; // Yellow
        return '#ef4444'; // Red
    }, [percentage]);

    // Format value for display
    const formattedValue = useMemo(() => {
        switch (format) {
            case 'currency':
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    minimumFractionDigits: 0,
                }).format(value);
            case 'percent':
                return `${value}%`;
            default:
                if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
                return new Intl.NumberFormat().format(Math.round(value));
        }
    }, [value, format]);

    const formattedTarget = useMemo(() => {
        switch (format) {
            case 'currency':
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                    minimumFractionDigits: 0,
                }).format(target);
            case 'percent':
                return `${target}%`;
            default:
                if (target >= 1000000) return (target / 1000000).toFixed(1) + 'M';
                if (target >= 1000) return (target / 1000).toFixed(1) + 'K';
                return new Intl.NumberFormat().format(Math.round(target));
        }
    }, [target, format]);

    // SVG parameters for circular gauge
    const radius = 45;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference * (1 - percentage / 100);

    // Error state
    if (data?.error) {
        return (
            <div className="lw-gauge-widget lw-gauge-error">
                <div className="lw-gauge-error-message">
                    <i className="fa fa-exclamation-triangle"></i>
                    <span>Failed to load data</span>
                </div>
            </div>
        );
    }

    // Loading state
    if (!data) {
        return (
            <div className="lw-gauge-widget lw-gauge-loading">
                <div className="lw-gauge-loading-spinner">
                    <i className="fa fa-spinner fa-spin fa-2x"></i>
                </div>
            </div>
        );
    }

    return (
        <div className="lw-gauge-widget">
            <div className="lw-gauge-chart">
                <svg viewBox="0 0 100 100" className="lw-gauge-svg">
                    {/* Background circle */}
                    <circle
                        cx="50"
                        cy="50"
                        r={radius}
                        fill="none"
                        stroke="#e5e7eb"
                        strokeWidth="8"
                    />
                    {/* Progress circle */}
                    <circle
                        cx="50"
                        cy="50"
                        r={radius}
                        fill="none"
                        stroke={color}
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        transform="rotate(-90 50 50)"
                        style={{ transition: 'stroke-dashoffset 0.5s ease' }}
                    />
                </svg>
                <div className="lw-gauge-center">
                    <div className="lw-gauge-percentage">{percentage}%</div>
                </div>
            </div>

            <div className="lw-gauge-info">
                <div className="lw-gauge-value">
                    <span className="lw-gauge-current">{formattedValue}</span>
                    <span className="lw-gauge-separator">/</span>
                    <span className="lw-gauge-target">{formattedTarget}</span>
                </div>
                <div className="lw-gauge-label">
                    {percentage >= 100 ? 'Target reached!' : `${100 - percentage}% to target`}
                </div>
            </div>
        </div>
    );
}

// Export globally
window.GaugeWidget = GaugeWidget;
