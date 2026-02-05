# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
Tests for Spreadsheet Pivot Table Model.
"""

from odoo.tests.common import TransactionCase


class TestSpreadsheetPivot(TransactionCase):
    """Test cases for spreadsheet.pivot model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['spreadsheet.document']
        cls.Pivot = cls.env['spreadsheet.pivot']
        cls.PivotMeasure = cls.env['spreadsheet.pivot.measure']
        cls.IrModel = cls.env['ir.model']
        cls.IrModelFields = cls.env['ir.model.fields']

        # Create a test document
        cls.test_doc = cls.Document.create({'name': 'Pivot Test Document'})

        # Get res.partner model
        cls.partner_model = cls.IrModel.search([('model', '=', 'res.partner')], limit=1)

        # Get partner fields
        cls.country_field = cls.IrModelFields.search([
            ('model', '=', 'res.partner'),
            ('name', '=', 'country_id'),
        ], limit=1)

        cls.state_field = cls.IrModelFields.search([
            ('model', '=', 'res.partner'),
            ('name', '=', 'state_id'),
        ], limit=1)

    def test_create_pivot(self):
        """Test creating a pivot table."""
        pivot = self.Pivot.create({
            'name': 'Partner by Country',
            'document_id': self.test_doc.id,
            'model_id': self.partner_model.id,
            'row_field_ids': [(6, 0, [self.country_field.id])] if self.country_field else [],
        })

        self.assertTrue(pivot.id)
        self.assertEqual(pivot.model_name, 'res.partner')
        self.assertTrue(pivot.show_totals)

    def test_compute_pivot_count(self):
        """Test computing pivot with count measure."""
        pivot = self.Pivot.create({
            'name': 'Count Pivot',
            'document_id': self.test_doc.id,
            'model_id': self.partner_model.id,
            'row_field_ids': [(6, 0, [self.country_field.id])] if self.country_field else [],
        })

        # No measures means count by default
        result = pivot.compute_pivot()

        self.assertIn('rows', result)
        self.assertIn('columns', result)
        self.assertIn('measures', result)

        # Default measure should be count
        self.assertEqual(result['measures'][0]['aggregator'], 'count')

    def test_pivot_with_domain(self):
        """Test pivot with filter domain."""
        pivot = self.Pivot.create({
            'name': 'Filtered Pivot',
            'document_id': self.test_doc.id,
            'model_id': self.partner_model.id,
            'domain': "[('is_company', '=', True)]",
            'row_field_ids': [(6, 0, [self.country_field.id])] if self.country_field else [],
        })

        result = pivot.compute_pivot()

        # Should complete without error
        self.assertNotIn('error', result)

    def test_pivot_cached_data(self):
        """Test pivot data caching."""
        pivot = self.Pivot.create({
            'name': 'Cache Test',
            'document_id': self.test_doc.id,
            'model_id': self.partner_model.id,
        })

        # Compute to populate cache
        pivot.compute_pivot()

        self.assertTrue(pivot.cached_data)
        self.assertTrue(pivot.last_computed)

    def test_pivot_refresh(self):
        """Test refreshing pivot data."""
        pivot = self.Pivot.create({
            'name': 'Refresh Test',
            'document_id': self.test_doc.id,
            'model_id': self.partner_model.id,
        })

        # First compute
        pivot.compute_pivot()
        first_computed = pivot.last_computed

        # Refresh
        result = pivot.action_refresh()

        # Should show notification
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_pivot_totals(self):
        """Test pivot totals computation."""
        pivot = self.Pivot.create({
            'name': 'Totals Test',
            'document_id': self.test_doc.id,
            'model_id': self.partner_model.id,
            'row_field_ids': [(6, 0, [self.country_field.id])] if self.country_field else [],
            'show_totals': True,
        })

        result = pivot.compute_pivot()

        if result.get('rows', {}).get('values'):
            # Should have totals
            self.assertIn('totals', result)
            self.assertIn('grand', result['totals'])

    def test_pivot_measure(self):
        """Test creating pivot measures."""
        pivot = self.Pivot.create({
            'name': 'Measure Test',
            'document_id': self.test_doc.id,
            'model_id': self.partner_model.id,
        })

        # Find a numeric field
        numeric_field = self.IrModelFields.search([
            ('model', '=', 'res.partner'),
            ('ttype', 'in', ['integer', 'float']),
            ('store', '=', True),
        ], limit=1)

        if numeric_field:
            measure = self.PivotMeasure.create({
                'pivot_id': pivot.id,
                'field_id': numeric_field.id,
                'aggregator': 'sum',
            })

            self.assertTrue(measure.id)
            self.assertEqual(measure.aggregator, 'sum')

    def test_pivot_no_model_error(self):
        """Test pivot with invalid model."""
        pivot = self.Pivot.create({
            'name': 'Error Test',
            'document_id': self.test_doc.id,
            'model_id': self.partner_model.id,
        })

        # Manually set invalid model (bypass constraints)
        pivot.write({'model_name': 'invalid.model.name'})

        result = pivot.compute_pivot()

        # Should return error
        self.assertIn('error', result)


class TestSpreadsheetChart(TransactionCase):
    """Test cases for spreadsheet.chart model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['spreadsheet.document']
        cls.Chart = cls.env['spreadsheet.chart']
        cls.IrModel = cls.env['ir.model']
        cls.IrModelFields = cls.env['ir.model.fields']

        # Create a test document
        cls.test_doc = cls.Document.create({'name': 'Chart Test Document'})

        # Get res.partner model
        cls.partner_model = cls.IrModel.search([('model', '=', 'res.partner')], limit=1)

        # Get partner fields
        cls.country_field = cls.IrModelFields.search([
            ('model', '=', 'res.partner'),
            ('name', '=', 'country_id'),
        ], limit=1)

    def test_create_chart(self):
        """Test creating a chart."""
        chart = self.Chart.create({
            'name': 'Partners by Country',
            'document_id': self.test_doc.id,
            'chart_type': 'bar',
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'groupby_field_id': self.country_field.id if self.country_field else None,
        })

        self.assertTrue(chart.id)
        self.assertEqual(chart.chart_type, 'bar')
        self.assertTrue(chart.show_legend)

    def test_chart_types(self):
        """Test various chart types."""
        chart_types = ['bar', 'line', 'pie', 'doughnut', 'area']

        for ctype in chart_types:
            chart = self.Chart.create({
                'name': f'{ctype.title()} Chart',
                'document_id': self.test_doc.id,
                'chart_type': ctype,
                'source_type': 'model',
                'model_id': self.partner_model.id,
                'groupby_field_id': self.country_field.id if self.country_field else None,
            })

            self.assertEqual(chart.chart_type, ctype)

    def test_get_chart_data(self):
        """Test getting chart data."""
        chart = self.Chart.create({
            'name': 'Data Test',
            'document_id': self.test_doc.id,
            'chart_type': 'bar',
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'groupby_field_id': self.country_field.id if self.country_field else None,
        })

        data = chart.get_chart_data()

        if self.country_field:
            self.assertIn('labels', data)
            self.assertIn('datasets', data)
        else:
            # Without groupby field, should return error
            self.assertIn('error', data)

    def test_get_echarts_option(self):
        """Test generating ECharts configuration."""
        chart = self.Chart.create({
            'name': 'ECharts Test',
            'document_id': self.test_doc.id,
            'chart_type': 'bar',
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'groupby_field_id': self.country_field.id if self.country_field else None,
        })

        option = chart.get_echarts_option()

        if self.country_field:
            self.assertIn('tooltip', option)
            self.assertIn('series', option)
        else:
            self.assertIn('error', option)

    def test_chart_colors(self):
        """Test chart color schemes."""
        chart = self.Chart.create({
            'name': 'Color Test',
            'document_id': self.test_doc.id,
            'chart_type': 'pie',
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'color_scheme': 'vibrant',
        })

        colors = chart._get_colors()

        self.assertIsInstance(colors, list)
        self.assertGreater(len(colors), 0)

    def test_custom_colors(self):
        """Test custom color palette."""
        chart = self.Chart.create({
            'name': 'Custom Color Test',
            'document_id': self.test_doc.id,
            'chart_type': 'bar',
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'color_scheme': 'custom',
            'custom_colors': '#FF0000, #00FF00, #0000FF',
        })

        colors = chart._get_colors()

        self.assertEqual(len(colors), 3)
        self.assertEqual(colors[0], '#FF0000')
