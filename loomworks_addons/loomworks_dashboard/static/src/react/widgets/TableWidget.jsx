/**
 * TableWidget - Data table widget
 *
 * Displays records in a paginated table with:
 * - Sortable columns
 * - Pagination
 * - Row click actions
 */

const { useState, useMemo, useCallback } = React;

function TableWidget({ widget, data, filters, mode, onAction }) {
    const [currentPage, setCurrentPage] = useState(1);
    const [sortField, setSortField] = useState(null);
    const [sortDirection, setSortDirection] = useState('asc');

    const pageSize = widget.config?.pageSize || 10;
    const columns = widget.config?.columns || [];

    // Parse table data
    const tableData = useMemo(() => {
        if (!data) return [];
        if (data.error) return [];

        if (data.type === 'records' && data.data) {
            return data.data;
        }
        if (data.type === 'grouped' && data.data) {
            return data.data;
        }
        if (Array.isArray(data.data)) {
            return data.data;
        }
        return [];
    }, [data]);

    // Sort data
    const sortedData = useMemo(() => {
        if (!sortField) return tableData;

        return [...tableData].sort((a, b) => {
            const aVal = a[sortField];
            const bVal = b[sortField];

            if (aVal === null || aVal === undefined) return 1;
            if (bVal === null || bVal === undefined) return -1;

            let comparison = 0;
            if (typeof aVal === 'number' && typeof bVal === 'number') {
                comparison = aVal - bVal;
            } else {
                comparison = String(aVal).localeCompare(String(bVal));
            }

            return sortDirection === 'asc' ? comparison : -comparison;
        });
    }, [tableData, sortField, sortDirection]);

    // Paginate data
    const paginatedData = useMemo(() => {
        const start = (currentPage - 1) * pageSize;
        return sortedData.slice(start, start + pageSize);
    }, [sortedData, currentPage, pageSize]);

    // Calculate total pages
    const totalPages = Math.ceil(sortedData.length / pageSize);

    // Handle column click for sorting
    const handleSort = useCallback((field) => {
        if (sortField === field) {
            setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('asc');
        }
    }, [sortField]);

    // Handle row click
    const handleRowClick = useCallback((row) => {
        if (onAction && row.id && widget.inlineDataSource?.model) {
            onAction({
                type: 'open_record',
                model: widget.inlineDataSource.model,
                resId: row.id,
            });
        }
    }, [onAction, widget.inlineDataSource]);

    // Format cell value
    const formatValue = useCallback((value, column) => {
        if (value === null || value === undefined) return '--';

        // Handle Many2one fields (tuple)
        if (Array.isArray(value) && value.length === 2) {
            return value[1];
        }

        // Handle dates
        if (column?.type === 'date' || column?.type === 'datetime') {
            const date = new Date(value);
            return date.toLocaleDateString();
        }

        // Handle numbers
        if (typeof value === 'number') {
            if (column?.format === 'currency') {
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                }).format(value);
            }
            return new Intl.NumberFormat().format(value);
        }

        return String(value);
    }, []);

    // Generate columns from data if not configured
    const effectiveColumns = useMemo(() => {
        if (columns.length > 0) return columns;

        // Auto-generate columns from first row
        if (paginatedData.length > 0) {
            return Object.keys(paginatedData[0])
                .filter(key => !key.startsWith('_') && key !== 'id')
                .slice(0, 6)
                .map(key => ({
                    field: key,
                    label: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
                }));
        }

        return [];
    }, [columns, paginatedData]);

    // Error state
    if (data?.error) {
        return (
            <div className="lw-table-widget lw-table-error">
                <div className="lw-table-error-message">
                    <i className="fa fa-exclamation-triangle"></i>
                    <span>Failed to load table data</span>
                </div>
            </div>
        );
    }

    // Loading state
    if (!data) {
        return (
            <div className="lw-table-widget lw-table-loading">
                <div className="lw-table-loading-spinner">
                    <i className="fa fa-spinner fa-spin fa-2x"></i>
                </div>
            </div>
        );
    }

    // Empty state
    if (tableData.length === 0) {
        return (
            <div className="lw-table-widget lw-table-empty">
                <i className="fa fa-table text-muted"></i>
                <span>No records found</span>
            </div>
        );
    }

    return (
        <div className="lw-table-widget">
            <div className="lw-table-container">
                <table className="lw-table">
                    <thead>
                        <tr>
                            {effectiveColumns.map((col, index) => (
                                <th
                                    key={index}
                                    onClick={() => handleSort(col.field)}
                                    className={sortField === col.field ? 'lw-table-sorted' : ''}
                                >
                                    {col.label}
                                    {sortField === col.field && (
                                        <i className={`fa fa-sort-${sortDirection === 'asc' ? 'up' : 'down'} ms-1`}></i>
                                    )}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedData.map((row, rowIndex) => (
                            <tr
                                key={row.id || rowIndex}
                                onClick={() => handleRowClick(row)}
                                className={row.id ? 'lw-table-row-clickable' : ''}
                            >
                                {effectiveColumns.map((col, colIndex) => (
                                    <td key={colIndex}>
                                        {formatValue(row[col.field], col)}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {totalPages > 1 && (
                <div className="lw-table-pagination">
                    <button
                        className="lw-table-page-btn"
                        disabled={currentPage === 1}
                        onClick={() => setCurrentPage(1)}
                    >
                        <i className="fa fa-angle-double-left"></i>
                    </button>
                    <button
                        className="lw-table-page-btn"
                        disabled={currentPage === 1}
                        onClick={() => setCurrentPage(p => p - 1)}
                    >
                        <i className="fa fa-angle-left"></i>
                    </button>
                    <span className="lw-table-page-info">
                        Page {currentPage} of {totalPages}
                    </span>
                    <button
                        className="lw-table-page-btn"
                        disabled={currentPage === totalPages}
                        onClick={() => setCurrentPage(p => p + 1)}
                    >
                        <i className="fa fa-angle-right"></i>
                    </button>
                    <button
                        className="lw-table-page-btn"
                        disabled={currentPage === totalPages}
                        onClick={() => setCurrentPage(totalPages)}
                    >
                        <i className="fa fa-angle-double-right"></i>
                    </button>
                </div>
            )}

            <div className="lw-table-footer">
                <span className="lw-table-count">
                    {sortedData.length} record{sortedData.length !== 1 ? 's' : ''}
                </span>
            </div>
        </div>
    );
}

// Export globally
window.TableWidget = TableWidget;
