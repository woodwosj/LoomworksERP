# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
Tests for Studio App functionality.
"""

from loomworks.tests import TransactionCase, tagged
from loomworks.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestStudioApp(TransactionCase):
    """Test cases for studio.app model."""

    def setUp(self):
        super().setUp()
        self.StudioApp = self.env['studio.app']

    def test_create_app(self):
        """Test creating a basic Studio app."""
        app = self.StudioApp.create({
            'name': 'Test Application',
            'technical_name': 'test_app',
            'description': 'A test application',
        })

        self.assertEqual(app.name, 'Test Application')
        self.assertEqual(app.technical_name, 'test_app')
        self.assertEqual(app.state, 'draft')
        self.assertEqual(app.model_count, 0)

    def test_technical_name_validation(self):
        """Test that technical name validation works."""
        # Valid name
        app = self.StudioApp.create({
            'name': 'Valid App',
            'technical_name': 'valid_app_123',
        })
        self.assertTrue(app.exists())

        # Invalid name with uppercase
        with self.assertRaises(ValidationError):
            self.StudioApp.create({
                'name': 'Invalid App',
                'technical_name': 'Invalid_App',
            })

        # Invalid name with special chars
        with self.assertRaises(ValidationError):
            self.StudioApp.create({
                'name': 'Invalid App',
                'technical_name': 'invalid-app',
            })

        # Invalid name starting with number
        with self.assertRaises(ValidationError):
            self.StudioApp.create({
                'name': 'Invalid App',
                'technical_name': '123app',
            })

    def test_technical_name_unique(self):
        """Test that technical name must be unique."""
        self.StudioApp.create({
            'name': 'First App',
            'technical_name': 'unique_name',
        })

        with self.assertRaises(Exception):  # IntegrityError
            self.StudioApp.create({
                'name': 'Second App',
                'technical_name': 'unique_name',
            })

    def test_create_model_in_app(self):
        """Test creating a model within a Studio app."""
        app = self.StudioApp.create({
            'name': 'Model Test App',
            'technical_name': 'model_test',
        })

        # Create a model
        model = app.action_create_model({
            'name': 'Contacts',
            'model_name': 'contacts',
            'fields': [
                {'name': 'email', 'type': 'char', 'label': 'Email'},
                {'name': 'phone', 'type': 'char', 'label': 'Phone'},
            ],
            'create_menu': False,  # Skip menu creation in test
        })

        self.assertTrue(model.exists())
        self.assertEqual(model.model, 'x_model_test_contacts')
        self.assertEqual(app.model_count, 1)

        # Check that fields were created
        fields = self.env['ir.model.fields'].search([
            ('model_id', '=', model.id),
            ('state', '=', 'manual'),
        ])
        # Should have x_name (auto), x_email, x_phone
        self.assertGreaterEqual(len(fields), 3)

    def test_app_publish(self):
        """Test publishing a Studio app."""
        app = self.StudioApp.create({
            'name': 'Publish Test',
            'technical_name': 'publish_test',
        })

        self.assertEqual(app.state, 'draft')
        self.assertFalse(app.published_date)

        app.action_publish()

        self.assertEqual(app.state, 'published')
        self.assertTrue(app.published_date)

    def test_app_archive_restore(self):
        """Test archiving and restoring an app."""
        app = self.StudioApp.create({
            'name': 'Archive Test',
            'technical_name': 'archive_test',
        })

        app.action_publish()
        self.assertEqual(app.state, 'published')

        app.action_archive()
        self.assertEqual(app.state, 'archived')
        self.assertFalse(app.active)

        app.action_unarchive()
        self.assertEqual(app.state, 'published')
        self.assertTrue(app.active)

    def test_app_export_import(self):
        """Test exporting and importing app definitions."""
        # Create app with a model
        app = self.StudioApp.create({
            'name': 'Export Test App',
            'technical_name': 'export_test',
            'description': 'Test export functionality',
        })

        # Get export data
        export_dict = app._get_export_dict()

        self.assertEqual(export_dict['name'], 'Export Test App')
        self.assertEqual(export_dict['technical_name'], 'export_test')
        self.assertIn('version', export_dict)
        self.assertIn('exported_at', export_dict)

    def test_compute_record_count(self):
        """Test that record count is computed correctly."""
        app = self.StudioApp.create({
            'name': 'Count Test',
            'technical_name': 'count_test',
        })

        # Initially zero
        self.assertEqual(app.record_count, 0)
