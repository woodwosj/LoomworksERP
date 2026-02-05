/**
 * FilterWidget - Global filter control widget
 *
 * Provides interactive filter controls:
 * - Dropdown select
 * - Multi-select
 * - Date range picker
 * - Number range slider
 * - Text search
 */

const { useState, useMemo, useCallback } = React;

function FilterWidget({ widget, data, filters, mode, onAction }) {
    const config = widget.config || {};
    const filterType = config.filterType || 'select';
    const fieldName = config.field || '';

    // Current filter value
    const currentValue = filters?.[fieldName];

    // Get options for select filters
    const options = useMemo(() => {
        if (config.options) return config.options;
        if (data?.data) {
            // Extract unique values from data
            return [...new Set(data.data.map(item => item.name))]
                .filter(Boolean)
                .map(value => ({ value, label: value }));
        }
        return [];
    }, [config.options, data]);

    // Handle value change
    const handleChange = useCallback((newValue) => {
        // This would need to be wired up to parent filter state
        console.log('Filter changed:', fieldName, newValue);
    }, [fieldName]);

    // Render based on filter type
    const renderControl = () => {
        switch (filterType) {
            case 'select':
                return (
                    <SelectFilter
                        options={options}
                        value={currentValue}
                        placeholder={config.placeholder || 'Select...'}
                        onChange={handleChange}
                    />
                );

            case 'multiselect':
                return (
                    <MultiSelectFilter
                        options={options}
                        value={currentValue || []}
                        placeholder={config.placeholder || 'Select...'}
                        onChange={handleChange}
                    />
                );

            case 'date_range':
                return (
                    <DateRangeFilter
                        value={currentValue || {}}
                        presets={config.datePresets}
                        onChange={handleChange}
                    />
                );

            case 'number_range':
                return (
                    <NumberRangeFilter
                        value={currentValue || {}}
                        min={config.range?.min || 0}
                        max={config.range?.max || 100}
                        step={config.range?.step || 1}
                        onChange={handleChange}
                    />
                );

            case 'search':
                return (
                    <SearchFilter
                        value={currentValue || ''}
                        placeholder={config.placeholder || 'Search...'}
                        onChange={handleChange}
                    />
                );

            default:
                return <div>Unknown filter type: {filterType}</div>;
        }
    };

    return (
        <div className="lw-filter-widget">
            <div className="lw-filter-label">
                {config.label || widget.name}
            </div>
            <div className="lw-filter-control">
                {renderControl()}
            </div>
        </div>
    );
}

/**
 * Select dropdown filter
 */
function SelectFilter({ options, value, placeholder, onChange }) {
    return (
        <select
            className="lw-filter-select"
            value={value || ''}
            onChange={(e) => onChange(e.target.value || null)}
        >
            <option value="">{placeholder}</option>
            {options.map((opt, index) => (
                <option key={index} value={opt.value}>
                    {opt.label}
                </option>
            ))}
        </select>
    );
}

/**
 * Multi-select filter
 */
function MultiSelectFilter({ options, value, placeholder, onChange }) {
    const [isOpen, setIsOpen] = useState(false);

    const handleToggle = (optValue) => {
        const newValue = value.includes(optValue)
            ? value.filter(v => v !== optValue)
            : [...value, optValue];
        onChange(newValue);
    };

    return (
        <div className="lw-filter-multiselect">
            <div
                className="lw-filter-multiselect-trigger"
                onClick={() => setIsOpen(!isOpen)}
            >
                {value.length > 0 ? `${value.length} selected` : placeholder}
                <i className={`fa fa-chevron-${isOpen ? 'up' : 'down'}`}></i>
            </div>
            {isOpen && (
                <div className="lw-filter-multiselect-dropdown">
                    {options.map((opt, index) => (
                        <label key={index} className="lw-filter-multiselect-option">
                            <input
                                type="checkbox"
                                checked={value.includes(opt.value)}
                                onChange={() => handleToggle(opt.value)}
                            />
                            {opt.label}
                        </label>
                    ))}
                </div>
            )}
        </div>
    );
}

/**
 * Date range filter
 */
function DateRangeFilter({ value, presets, onChange }) {
    const [showPresets, setShowPresets] = useState(false);

    const handlePresetClick = (preset) => {
        onChange({ from: preset.from, to: preset.to });
        setShowPresets(false);
    };

    const defaultPresets = [
        { name: 'Today', from: new Date().toISOString().split('T')[0], to: new Date().toISOString().split('T')[0] },
        { name: 'Last 7 Days', from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], to: new Date().toISOString().split('T')[0] },
        { name: 'Last 30 Days', from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], to: new Date().toISOString().split('T')[0] },
        { name: 'This Month', from: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0], to: new Date().toISOString().split('T')[0] },
    ];

    const effectivePresets = presets || defaultPresets;

    return (
        <div className="lw-filter-daterange">
            <div className="lw-filter-daterange-inputs">
                <input
                    type="date"
                    className="lw-filter-date-input"
                    value={value.from || ''}
                    onChange={(e) => onChange({ ...value, from: e.target.value })}
                    placeholder="From"
                />
                <span className="lw-filter-daterange-separator">to</span>
                <input
                    type="date"
                    className="lw-filter-date-input"
                    value={value.to || ''}
                    onChange={(e) => onChange({ ...value, to: e.target.value })}
                    placeholder="To"
                />
            </div>
            <div className="lw-filter-daterange-presets">
                <button
                    className="lw-filter-preset-toggle"
                    onClick={() => setShowPresets(!showPresets)}
                >
                    Quick select <i className="fa fa-caret-down"></i>
                </button>
                {showPresets && (
                    <div className="lw-filter-preset-dropdown">
                        {effectivePresets.map((preset, index) => (
                            <button
                                key={index}
                                className="lw-filter-preset-btn"
                                onClick={() => handlePresetClick(preset)}
                            >
                                {preset.name}
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

/**
 * Number range filter
 */
function NumberRangeFilter({ value, min, max, step, onChange }) {
    return (
        <div className="lw-filter-numrange">
            <input
                type="number"
                className="lw-filter-num-input"
                value={value.from || ''}
                min={min}
                max={max}
                step={step}
                onChange={(e) => onChange({ ...value, from: parseFloat(e.target.value) || null })}
                placeholder="Min"
            />
            <span className="lw-filter-numrange-separator">to</span>
            <input
                type="number"
                className="lw-filter-num-input"
                value={value.to || ''}
                min={min}
                max={max}
                step={step}
                onChange={(e) => onChange({ ...value, to: parseFloat(e.target.value) || null })}
                placeholder="Max"
            />
        </div>
    );
}

/**
 * Text search filter
 */
function SearchFilter({ value, placeholder, onChange }) {
    const [localValue, setLocalValue] = useState(value);

    const handleSubmit = () => {
        onChange(localValue);
    };

    return (
        <div className="lw-filter-search">
            <input
                type="text"
                className="lw-filter-search-input"
                value={localValue}
                onChange={(e) => setLocalValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                placeholder={placeholder}
            />
            <button className="lw-filter-search-btn" onClick={handleSubmit}>
                <i className="fa fa-search"></i>
            </button>
        </div>
    );
}

// Also export FilterControl for global filters
function FilterControl({ filter, value, onChange }) {
    return (
        <FilterWidget
            widget={{
                name: filter.name,
                config: {
                    field: filter.fieldName,
                    filterType: filter.type,
                    label: filter.label,
                    placeholder: filter.placeholder,
                    options: filter.options,
                    datePresets: filter.datePresets,
                    range: filter.range,
                },
            }}
            data={null}
            filters={{ [filter.fieldName]: value }}
            mode="view"
            onAction={() => {}}
        />
    );
}

// Export globally
window.FilterWidget = FilterWidget;
window.FilterControl = FilterControl;
