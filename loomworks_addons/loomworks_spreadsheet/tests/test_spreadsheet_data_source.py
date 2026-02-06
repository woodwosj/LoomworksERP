# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
Tests for Spreadsheet Data Source Model.
"""

from loomworks.tests.common import TransactionCase
from loomworks.exceptions import UserError


class TestSpreadsheetDataSource(TransactionCase):
    """Test cases for spreadsheet.data.source model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['spreadsheet.document']
        cls.DataSource = cls.env['spreadsheet.data.source']
        cls.IrModel = cls.env['ir.model']
        cls.IrModelFields = cls.env['ir.model.fields']

        # Create a test document
        cls.test_doc = cls.Document.create({'name': 'Test Document'})

        # Get res.partner model
        cls.partner_model = cls.IrModel.search([('model', '=', 'res.partner')], limit=1)

        # Get some partner fields
        cls.partner_fields = cls.IrModelFields.search([
            ('model', '=', 'res.partner'),
            ('name', 'in', ['name', 'email', 'phone']),
        ])

    def test_create_data_source(self):
        """Test creating a data source."""
        ds = self.DataSource.create({
            'name': 'Partner Data',
            'document_id': self.test_doc.id,
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'field_ids': [(6, 0, self.partner_fields.ids)],
        })

        self.assertTrue(ds.id)
        self.assertEqual(ds.model_name, 'res.partner')
        self.assertEqual(ds.target_cell, 'A1')
        self.assertTrue(ds.include_headers)

    def test_fetch_data(self):
        """Test fetching data from a data source."""
        # Create some test partners
        self.env['res.partner'].create([
            {'name': 'Test Partner 1', 'email': 'test1@example.com'},
            {'name': 'Test Partner 2', 'email': 'test2@example.com'},
        ])

        ds = self.DataSource.create({
            'name': 'Partner Fetch Test',
            'document_id': self.test_doc.id,
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'field_ids': [(6, 0, self.partner_fields.ids)],
            'domain': "[('name', 'like', 'Test Partner')]",
            'limit': 10,
        })

        data = ds.fetch_data()

        self.assertIn('headers', data)
        self.assertIn('rows', data)
        self.assertIn('record_count', data)
        self.assertGreaterEqual(data['record_count'], 2)

    def test_invalid_domain(self):
        """Test that invalid domain raises error."""
        ds = self.DataSource.create({
            'name': 'Invalid Domain Test',
            'document_id': self.test_doc.id,
            'source_type': 'model',
            'model_id': self.partner_model.id,
        })

        with self.assertRaises(UserError):
            ds.domain = "not a valid domain"

    def test_parse_cell_reference(self):
        """Test cell reference parsing."""
        ds = self.DataSource.create({
            'name': 'Cell Ref Test',
            'document_id': self.test_doc.id,
            'source_type': 'model',
            'model_id': self.partner_model.id,
        })

        # Test various cell references
        self.assertEqual(ds._parse_cell_ref('A1'), (0, 0))
        self.assertEqual(ds._parse_cell_ref('B2'), (1, 1))
        self.assertEqual(ds._parse_cell_ref('Z10'), (25, 9))
        self.assertEqual(ds._parse_cell_ref('AA1'), (26, 0))
        self.assertEqual(ds._parse_cell_ref('AB5'), (27, 4))

    def test_record_count_computed(self):
        """Test record count computation."""
        ds = self.DataSource.create({
            'name': 'Count Test',
            'document_id': self.test_doc.id,
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'domain': '[]',
        })

        # Should count all partners
        self.assertGreater(ds.record_count, 0)

    def test_data_source_with_order(self):
        """Test data source with sort order."""
        ds = self.DataSource.create({
            'name': 'Ordered Data',
            'document_id': self.test_doc.id,
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'field_ids': [(6, 0, self.partner_fields.ids)],
            'order': 'name desc',
            'limit': 5,
        })

        data = ds.fetch_data()

        # Should have data sorted by name descending
        self.assertIn('rows', data)
        if len(data['rows']) > 1:
            # Check names are in descending order
            names = [row[0] for row in data['rows'] if row[0]]  # Assuming name is first
            self.assertEqual(names, sorted(names, reverse=True))

    def test_insert_into_spreadsheet(self):
        """Test inserting data source data into spreadsheet."""
        # Create partners
        self.env['res.partner'].create([
            {'name': 'Insert Test 1'},
            {'name': 'Insert Test 2'},
        ])

        ds = self.DataSource.create({
            'name': 'Insert Test',
            'document_id': self.test_doc.id,
            'source_type': 'model',
            'model_id': self.partner_model.id,
            'field_ids': [(6, 0, self.partner_fields.ids)],
            'domain': "[('name', 'like', 'Insert Test')]",
            'target_cell': 'B2',
            'include_headers': True,
        })

        # Insert data
        ds.insert_into_spreadsheet()

        # Check spreadsheet data
        data = self.test_doc.get_data_for_univer()
        # Data should be inserted starting at B2 (column 1, row 1)
        # This verifies the method runs without error
        self.assertIsNotNone(data)
