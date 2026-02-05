/**
 * Loomworks Dashboard - React Component Bundle
 *
 * This file combines all React components for the dashboard system.
 * Components are registered globally on the window object for use
 * by the Owl bridge component.
 *
 * Dependencies (loaded by loomworks_spreadsheet):
 * - React 18
 * - ReactDOM 18
 *
 * Optional dependencies:
 * - Recharts (for charts)
 * - Gridstack.js (for drag-drop)
 */

(function() {
    'use strict';

    // Verify React is available
    if (typeof React === 'undefined') {
        console.error('Loomworks Dashboard: React is not loaded. Please ensure loomworks_spreadsheet is installed.');
        return;
    }

    console.log('Loomworks Dashboard: Initializing React components...');

    // =========================================================================
    // Utility Hooks
    // =========================================================================

    /**
     * Hook for debouncing values
     */
    window.useDebounce = function useDebounce(value, delay) {
        const [debouncedValue, setDebouncedValue] = React.useState(value);

        React.useEffect(() => {
            const handler = setTimeout(() => {
                setDebouncedValue(value);
            }, delay);

            return () => {
                clearTimeout(handler);
            };
        }, [value, delay]);

        return debouncedValue;
    };

    /**
     * Hook for managing local storage
     */
    window.useLocalStorage = function useLocalStorage(key, initialValue) {
        const [storedValue, setStoredValue] = React.useState(() => {
            try {
                const item = window.localStorage.getItem(key);
                return item ? JSON.parse(item) : initialValue;
            } catch (error) {
                return initialValue;
            }
        });

        const setValue = React.useCallback((value) => {
            try {
                const valueToStore = value instanceof Function ? value(storedValue) : value;
                setStoredValue(valueToStore);
                window.localStorage.setItem(key, JSON.stringify(valueToStore));
            } catch (error) {
                console.error('useLocalStorage error:', error);
            }
        }, [key, storedValue]);

        return [storedValue, setValue];
    };

    /**
     * Hook for auto-refresh interval
     */
    window.useAutoRefresh = function useAutoRefresh(callback, interval, enabled = true) {
        React.useEffect(() => {
            if (!enabled || !interval || interval <= 0) return;

            const id = setInterval(callback, interval);
            return () => clearInterval(id);
        }, [callback, interval, enabled]);
    };

    // =========================================================================
    // Load Component Files
    // =========================================================================

    // The individual component files (KPIWidget.jsx, ChartWidget.jsx, etc.)
    // are loaded separately by Odoo's asset system and register themselves
    // on the window object.

    // =========================================================================
    // Dashboard Context and Providers
    // =========================================================================

    /**
     * Odoo Context for React components
     */
    const OdooContext = React.createContext(null);
    window.OdooContext = OdooContext;

    window.useOdoo = function useOdoo() {
        const context = React.useContext(OdooContext);
        if (!context) {
            console.warn('useOdoo called outside OdooContext');
            return {};
        }
        return context;
    };

    /**
     * Dashboard Context for sharing state between widgets
     */
    const DashboardContext = React.createContext(null);
    window.DashboardContext = DashboardContext;

    window.useDashboard = function useDashboard() {
        return React.useContext(DashboardContext);
    };

    // =========================================================================
    // Component Registration Check
    // =========================================================================

    /**
     * Check if all required components are registered
     */
    function checkComponents() {
        const required = [
            'LoomworksDashboardApp',
            'DashboardCanvas',
            'KPIWidget',
            'ChartWidget',
            'TableWidget',
            'FilterWidget',
            'GaugeWidget',
            'WidgetToolbox',
            'WidgetPropertiesPanel',
        ];

        const missing = required.filter(name => typeof window[name] === 'undefined');

        if (missing.length > 0) {
            console.warn('Loomworks Dashboard: Some components not yet loaded:', missing);
        } else {
            console.log('Loomworks Dashboard: All components registered successfully');
        }
    }

    // Check components after a short delay to allow async loading
    setTimeout(checkComponents, 1000);

    // =========================================================================
    // Utility Functions
    // =========================================================================

    /**
     * Format number for display
     */
    window.formatDashboardNumber = function formatDashboardNumber(value, format = 'number', options = {}) {
        if (value === null || value === undefined) return '--';

        switch (format) {
            case 'currency':
                return new Intl.NumberFormat(options.locale || 'en-US', {
                    style: 'currency',
                    currency: options.currency || 'USD',
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 0,
                }).format(value);

            case 'percent':
                return new Intl.NumberFormat(options.locale || 'en-US', {
                    style: 'percent',
                    minimumFractionDigits: 1,
                    maximumFractionDigits: 1,
                }).format(value / 100);

            case 'compact':
                if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
                if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
                return new Intl.NumberFormat().format(Math.round(value));

            case 'number':
            default:
                return new Intl.NumberFormat(options.locale || 'en-US').format(value);
        }
    };

    /**
     * Transform Odoo data to Recharts format
     */
    window.transformToRechartsData = function transformToRechartsData(data) {
        if (!data) return [];

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
    };

    /**
     * Default chart colors
     */
    window.DASHBOARD_COLORS = [
        '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e',
        '#f97316', '#eab308', '#22c55e', '#14b8a6',
        '#06b6d4', '#3b82f6',
    ];

    console.log('Loomworks Dashboard: Bundle loaded');

})();
