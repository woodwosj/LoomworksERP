# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
Tests for Spreadsheet Document Model.
"""

import json
from odoo.tests.common import TransactionCase


class TestSpreadsheetDocument(TransactionCase):
    """Test cases for spreadsheet.document model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Document = cls.env['spreadsheet.document']

    def test_create_document(self):
        """Test creating a new spreadsheet document."""
        doc = self.Document.create({
            'name': 'Test Spreadsheet',
            'description': 'A test spreadsheet',
        })

        self.assertTrue(doc.id)
        self.assertEqual(doc.name, 'Test Spreadsheet')
        self.assertEqual(doc.description, 'A test spreadsheet')
        self.assertTrue(doc.active)
        self.assertFalse(doc.is_template)
        self.assertFalse(doc.is_published)

    def test_default_spreadsheet_data(self):
        """Test that new documents have default spreadsheet structure."""
        doc = self.Document.create({'name': 'Default Data Test'})

        data = doc.get_data_for_univer()

        self.assertIsInstance(data, dict)
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('sheets', data)
        self.assertEqual(len(data.get('sheets', [])), 1)

    def test_save_and_load_data(self):
        """Test saving and loading spreadsheet data."""
        doc = self.Document.create({'name': 'Save Test'})

        # Custom data
        test_data = {
            'id': 'test_workbook',
            'name': 'Test Workbook',
            'sheets': [{
                'id': 'sheet1',
                'name': 'Sheet 1',
                'cellData': {
                    '0:0': {'v': 'Hello'},
                    '0:1': {'v': 'World'},
                }
            }]
        }

        doc.save_from_univer(test_data)

        # Reload data
        loaded_data = doc.get_data_for_univer()

        self.assertEqual(loaded_data['name'], 'Test Workbook')
        self.assertEqual(len(loaded_data['sheets']), 1)
        self.assertEqual(loaded_data['sheets'][0]['id'], 'sheet1')

    def test_sheet_count(self):
        """Test sheet count computation."""
        doc = self.Document.create({'name': 'Sheet Count Test'})

        # Default should be 1
        self.assertEqual(doc.sheet_count, 1)

        # Add more sheets
        data = doc.get_data_for_univer()
        data['sheets'].append({
            'id': 'sheet2',
            'name': 'Sheet 2',
            'cellData': {}
        })
        doc.save_from_univer(data)

        # Refresh and check
        doc.invalidate_recordset()
        self.assertEqual(doc.sheet_count, 2)

    def test_duplicate_document(self):
        """Test duplicating a document."""
        original = self.Document.create({
            'name': 'Original',
            'description': 'Original document',
        })

        # Add some data
        data = original.get_data_for_univer()
        data['sheets'][0]['cellData'] = {'0:0': {'v': 'Test'}}
        original.save_from_univer(data)

        # Duplicate
        copy = original.action_duplicate()
        copy_doc = self.Document.browse(copy['res_id'])

        self.assertEqual(copy_doc.name, 'Original (copy)')
        self.assertNotEqual(copy_doc.id, original.id)

        # Check data was copied
        copy_data = copy_doc.get_data_for_univer()
        self.assertEqual(
            copy_data['sheets'][0]['cellData'].get('0:0', {}).get('v'),
            'Test'
        )

    def test_template_document(self):
        """Test template functionality."""
        template = self.Document.create({
            'name': 'Template',
            'is_template': True,
        })

        # Add template content
        data = template.get_data_for_univer()
        data['sheets'][0]['cellData'] = {
            '0:0': {'v': 'Header 1'},
            '0:1': {'v': 'Header 2'},
        }
        template.save_from_univer(data)

        # Create from template would copy this data
        self.assertTrue(template.is_template)

    def test_document_search(self):
        """Test searching documents."""
        self.Document.create({'name': 'Sales Report 2024'})
        self.Document.create({'name': 'Inventory Analysis'})
        self.Document.create({'name': 'Sales Summary'})

        # Search for sales documents
        sales_docs = self.Document.search([('name', 'ilike', 'sales')])
        self.assertEqual(len(sales_docs), 2)

    def test_archive_document(self):
        """Test archiving a document."""
        doc = self.Document.create({'name': 'Archive Test'})
        self.assertTrue(doc.active)

        doc.active = False

        # Should not appear in default search
        visible = self.Document.search([('name', '=', 'Archive Test')])
        self.assertEqual(len(visible), 0)

        # Should appear when including archived
        all_docs = self.Document.search([
            ('name', '=', 'Archive Test'),
            ('active', '=', False)
        ])
        self.assertEqual(len(all_docs), 1)
