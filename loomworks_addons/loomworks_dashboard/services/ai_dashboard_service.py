# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
AI Dashboard Generation Service

Generates dashboard specifications from natural language prompts.
Falls back to template-based generation when AI is unavailable.
"""

from odoo import api, models
import json
import logging

_logger = logging.getLogger(__name__)


class AIDashboardGenerationService(models.AbstractModel):
    """
    AI Dashboard Generation Service

    Integrates with loomworks_ai to generate dashboards from natural language.
    Falls back to template-based generation when AI is unavailable.
    """
    _name = 'dashboard.ai.generation.service'
    _description = 'AI Dashboard Generation Service'

    @api.model
    def generate_from_prompt(self, prompt, context=None):
        """
        Generate a dashboard specification from natural language.

        Args:
            prompt: Natural language description of desired dashboard
            context: Optional dict with user preferences, model hints

        Returns:
            dict: Dashboard specification with widgets, data sources, layout
        """
        try:
            # Check if AI module is available
            if 'loomworks.ai.agent' in self.env:
                return self._generate_with_ai(prompt, context)
            else:
                return self._generate_with_templates(prompt, context)
        except Exception as e:
            _logger.error("AI dashboard generation failed: %s", e)
            return self._generate_with_templates(prompt, context)

    def _generate_with_ai(self, prompt, context):
        """Generate using Claude AI agent."""
        try:
            agent_model = self.env['loomworks.ai.agent']
            agent = agent_model.search([('active', '=', True)], limit=1)

            if not agent:
                _logger.warning("No active AI agent found, falling back to templates")
                return self._generate_with_templates(prompt, context)

            # Build context for AI
            available_models = self._get_accessible_models()
            widget_types = self._get_widget_type_descriptions()

            generation_prompt = self._build_ai_prompt(prompt, available_models, widget_types)

            # Execute AI prompt
            response = agent.execute_prompt(generation_prompt)
            spec = json.loads(response)

            return {
                'success': True,
                'specification': spec,
                'method': 'ai',
            }
        except Exception as e:
            _logger.error("AI generation error: %s", e)
            return self._generate_with_templates(prompt, context)

    def _build_ai_prompt(self, prompt, available_models, widget_types):
        """Build the prompt for AI dashboard generation."""
        return f"""
Generate a dashboard specification based on this user request:
"{prompt}"

Available Odoo models the user can access:
{json.dumps(available_models, indent=2)}

Available widget types:
{json.dumps(widget_types, indent=2)}

Return a JSON object with this exact structure:
{{
    "name": "Dashboard Name",
    "description": "Brief description",
    "widgets": [
        {{
            "name": "Widget Title",
            "type": "chart_line|chart_bar|chart_pie|chart_area|kpi|table|filter|gauge",
            "position": {{"x": 0, "y": 0}},
            "size": {{"w": 4, "h": 3}},
            "data_source": {{
                "type": "model",
                "model": "sale.order",
                "domain": [],
                "group_by": "date_order:month",
                "measure_field": "amount_total",
                "aggregation": "sum"
            }},
            "config": {{
                "show_legend": true,
                "colors": ["#6366f1", "#8b5cf6"]
            }}
        }}
    ],
    "filters": [
        {{
            "name": "Date Range",
            "field": "date_order",
            "type": "date_range",
            "affects_widgets": [0, 1, 2]
        }}
    ],
    "layout": {{
        "columns": 12,
        "auto_arrange": true
    }}
}}

Guidelines:
- Use appropriate chart types for the data (line for trends, bar for comparisons, pie for proportions)
- Include KPI widgets for key metrics at the top
- Add filters for commonly filtered fields (dates, status, categories)
- Position widgets logically (KPIs at top, main charts in middle, details at bottom)
- Ensure data sources reference accessible models from the list above
- Use grid positions: x range 0-11, typical widths: KPI=3, charts=6, tables=6
- For sales dashboards: use sale.order, amount_total, date_order
- For inventory: use stock.picking, product_qty, scheduled_date
- For HR: use hr.employee, department_id
- For CRM: use crm.lead, expected_revenue, create_date

Return ONLY valid JSON, no explanation text.
"""

    def _generate_with_templates(self, prompt, context):
        """Fallback template-based generation."""
        prompt_lower = prompt.lower()

        # Detect dashboard type from keywords
        if any(w in prompt_lower for w in ['sales', 'revenue', 'order', 'customer']):
            template = self._get_sales_template()
        elif any(w in prompt_lower for w in ['inventory', 'stock', 'warehouse', 'product']):
            template = self._get_inventory_template()
        elif any(w in prompt_lower for w in ['hr', 'employee', 'attendance', 'leave', 'payroll']):
            template = self._get_hr_template()
        elif any(w in prompt_lower for w in ['crm', 'lead', 'opportunity', 'pipeline']):
            template = self._get_crm_template()
        elif any(w in prompt_lower for w in ['purchase', 'vendor', 'supplier']):
            template = self._get_purchase_template()
        else:
            template = self._get_generic_template()

        return {
            'success': True,
            'specification': template,
            'method': 'template',
            'note': 'Generated from template',
        }

    def _get_accessible_models(self):
        """Get models the current user can access."""
        common_models = [
            'sale.order', 'purchase.order', 'account.move',
            'stock.picking', 'crm.lead', 'project.task',
            'hr.employee', 'product.product', 'res.partner',
        ]

        accessible = []
        for model_name in common_models:
            try:
                Model = self.env.get(model_name)
                if Model and Model.check_access_rights('read', raise_exception=False):
                    fields = Model.fields_get()
                    numeric_fields = [
                        f for f, info in fields.items()
                        if info.get('type') in ('integer', 'float', 'monetary')
                    ][:10]
                    date_fields = [
                        f for f, info in fields.items()
                        if info.get('type') in ('date', 'datetime')
                    ][:5]

                    accessible.append({
                        'model': model_name,
                        'description': Model._description,
                        'numeric_fields': numeric_fields,
                        'date_fields': date_fields,
                    })
            except Exception:
                continue

        return accessible

    def _get_widget_type_descriptions(self):
        """Get widget type descriptions for AI context."""
        return [
            {'type': 'chart_line', 'use_for': 'Trends over time, continuous data'},
            {'type': 'chart_bar', 'use_for': 'Comparisons across categories'},
            {'type': 'chart_pie', 'use_for': 'Distribution, proportions, market share'},
            {'type': 'chart_area', 'use_for': 'Cumulative trends, stacked comparisons'},
            {'type': 'kpi', 'use_for': 'Single key metrics with trend indicators'},
            {'type': 'table', 'use_for': 'Detailed record lists with sorting/filtering'},
            {'type': 'filter', 'use_for': 'User-controlled data filtering'},
            {'type': 'gauge', 'use_for': 'Progress toward targets, percentages'},
        ]

    def _get_sales_template(self):
        """Pre-built sales dashboard template."""
        return {
            'name': 'Sales Overview Dashboard',
            'description': 'Key sales metrics and trends',
            'widgets': [
                {
                    'name': 'Total Revenue',
                    'type': 'kpi',
                    'position': {'x': 0, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                        'measure_field': 'amount_total',
                        'aggregation': 'sum',
                    },
                    'config': {'format': 'currency'},
                },
                {
                    'name': 'Orders Count',
                    'type': 'kpi',
                    'position': {'x': 3, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Avg Order Value',
                    'type': 'kpi',
                    'position': {'x': 6, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                        'measure_field': 'amount_total',
                        'aggregation': 'avg',
                    },
                    'config': {'format': 'currency'},
                },
                {
                    'name': 'Customers',
                    'type': 'kpi',
                    'position': {'x': 9, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'res.partner',
                        'domain': [('customer_rank', '>', 0)],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Revenue Trend',
                    'type': 'chart_line',
                    'position': {'x': 0, 'y': 2},
                    'size': {'w': 8, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                        'group_by': 'date_order:month',
                        'measure_field': 'amount_total',
                        'aggregation': 'sum',
                    },
                    'config': {'showLegend': True, 'showGrid': True},
                },
                {
                    'name': 'Sales by Status',
                    'type': 'chart_pie',
                    'position': {'x': 8, 'y': 2},
                    'size': {'w': 4, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [],
                        'group_by': 'state',
                        'measure_field': 'amount_total',
                        'aggregation': 'sum',
                    },
                    'config': {'showLegend': True},
                },
                {
                    'name': 'Top Customers',
                    'type': 'chart_bar',
                    'position': {'x': 0, 'y': 6},
                    'size': {'w': 6, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                        'group_by': 'partner_id',
                        'measure_field': 'amount_total',
                        'aggregation': 'sum',
                    },
                    'config': {'showLegend': False},
                },
                {
                    'name': 'Recent Orders',
                    'type': 'table',
                    'position': {'x': 6, 'y': 6},
                    'size': {'w': 6, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'sale.order',
                        'domain': [('state', 'in', ['sale', 'done'])],
                    },
                    'config': {
                        'pageSize': 5,
                        'columns': [
                            {'field': 'name', 'label': 'Order'},
                            {'field': 'partner_id', 'label': 'Customer'},
                            {'field': 'amount_total', 'label': 'Amount'},
                            {'field': 'date_order', 'label': 'Date'},
                        ],
                    },
                },
            ],
            'filters': [
                {
                    'name': 'Date Range',
                    'field': 'date_order',
                    'type': 'date_range',
                    'affects_widgets': [0, 1, 2, 4, 5, 6, 7],
                }
            ],
        }

    def _get_inventory_template(self):
        """Pre-built inventory dashboard template."""
        return {
            'name': 'Inventory Dashboard',
            'description': 'Stock levels and warehouse operations',
            'widgets': [
                {
                    'name': 'Total Products',
                    'type': 'kpi',
                    'position': {'x': 0, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'product.product',
                        'domain': [('type', '=', 'product')],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Transfers Today',
                    'type': 'kpi',
                    'position': {'x': 3, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'stock.picking',
                        'domain': [('state', '=', 'done')],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Pending Deliveries',
                    'type': 'kpi',
                    'position': {'x': 6, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'stock.picking',
                        'domain': [('state', 'in', ['confirmed', 'waiting', 'assigned'])],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Transfers by Type',
                    'type': 'chart_bar',
                    'position': {'x': 0, 'y': 2},
                    'size': {'w': 6, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'stock.picking',
                        'domain': [],
                        'group_by': 'picking_type_id',
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'showLegend': False},
                },
                {
                    'name': 'Transfer Trends',
                    'type': 'chart_line',
                    'position': {'x': 6, 'y': 2},
                    'size': {'w': 6, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'stock.picking',
                        'domain': [('state', '=', 'done')],
                        'group_by': 'date_done:month',
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'showLegend': True},
                },
            ],
            'filters': [],
        }

    def _get_hr_template(self):
        """Pre-built HR dashboard template."""
        return {
            'name': 'HR Dashboard',
            'description': 'Employee metrics and HR operations',
            'widgets': [
                {
                    'name': 'Total Employees',
                    'type': 'kpi',
                    'position': {'x': 0, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'hr.employee',
                        'domain': [('active', '=', True)],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Employees by Department',
                    'type': 'chart_pie',
                    'position': {'x': 0, 'y': 2},
                    'size': {'w': 6, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'hr.employee',
                        'domain': [('active', '=', True)],
                        'group_by': 'department_id',
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'showLegend': True},
                },
                {
                    'name': 'Employee List',
                    'type': 'table',
                    'position': {'x': 6, 'y': 2},
                    'size': {'w': 6, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'hr.employee',
                        'domain': [('active', '=', True)],
                    },
                    'config': {
                        'pageSize': 10,
                        'columns': [
                            {'field': 'name', 'label': 'Name'},
                            {'field': 'department_id', 'label': 'Department'},
                            {'field': 'job_id', 'label': 'Job'},
                        ],
                    },
                },
            ],
            'filters': [],
        }

    def _get_crm_template(self):
        """Pre-built CRM dashboard template."""
        return {
            'name': 'CRM Dashboard',
            'description': 'Lead pipeline and sales opportunities',
            'widgets': [
                {
                    'name': 'Open Opportunities',
                    'type': 'kpi',
                    'position': {'x': 0, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'crm.lead',
                        'domain': [('type', '=', 'opportunity'), ('active', '=', True)],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Expected Revenue',
                    'type': 'kpi',
                    'position': {'x': 3, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'crm.lead',
                        'domain': [('type', '=', 'opportunity'), ('active', '=', True)],
                        'measure_field': 'expected_revenue',
                        'aggregation': 'sum',
                    },
                    'config': {'format': 'currency'},
                },
                {
                    'name': 'New Leads',
                    'type': 'kpi',
                    'position': {'x': 6, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'crm.lead',
                        'domain': [('type', '=', 'lead')],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Pipeline by Stage',
                    'type': 'chart_bar',
                    'position': {'x': 0, 'y': 2},
                    'size': {'w': 6, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'crm.lead',
                        'domain': [('type', '=', 'opportunity')],
                        'group_by': 'stage_id',
                        'measure_field': 'expected_revenue',
                        'aggregation': 'sum',
                    },
                    'config': {'showLegend': False},
                },
                {
                    'name': 'Leads Over Time',
                    'type': 'chart_line',
                    'position': {'x': 6, 'y': 2},
                    'size': {'w': 6, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'crm.lead',
                        'domain': [],
                        'group_by': 'create_date:month',
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'showLegend': True},
                },
            ],
            'filters': [],
        }

    def _get_purchase_template(self):
        """Pre-built purchase dashboard template."""
        return {
            'name': 'Purchase Dashboard',
            'description': 'Procurement and vendor management',
            'widgets': [
                {
                    'name': 'Total Spend',
                    'type': 'kpi',
                    'position': {'x': 0, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'purchase.order',
                        'domain': [('state', 'in', ['purchase', 'done'])],
                        'measure_field': 'amount_total',
                        'aggregation': 'sum',
                    },
                    'config': {'format': 'currency'},
                },
                {
                    'name': 'Purchase Orders',
                    'type': 'kpi',
                    'position': {'x': 3, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'purchase.order',
                        'domain': [('state', 'in', ['purchase', 'done'])],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
                {
                    'name': 'Spend Trend',
                    'type': 'chart_line',
                    'position': {'x': 0, 'y': 2},
                    'size': {'w': 8, 'h': 4},
                    'data_source': {
                        'type': 'model',
                        'model': 'purchase.order',
                        'domain': [('state', 'in', ['purchase', 'done'])],
                        'group_by': 'date_order:month',
                        'measure_field': 'amount_total',
                        'aggregation': 'sum',
                    },
                    'config': {'showLegend': True},
                },
            ],
            'filters': [],
        }

    def _get_generic_template(self):
        """Generic empty dashboard template."""
        return {
            'name': 'Custom Dashboard',
            'description': 'Start with a blank canvas',
            'widgets': [
                {
                    'name': 'Partners',
                    'type': 'kpi',
                    'position': {'x': 0, 'y': 0},
                    'size': {'w': 3, 'h': 2},
                    'data_source': {
                        'type': 'model',
                        'model': 'res.partner',
                        'domain': [],
                        'measure_field': 'id',
                        'aggregation': 'count',
                    },
                    'config': {'format': 'number'},
                },
            ],
            'filters': [],
        }
