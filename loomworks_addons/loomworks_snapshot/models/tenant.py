# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Loomworks Tenant Model - Multi-Tenant Configuration

This module implements multi-tenant support using database-per-tenant architecture.
Each tenant has its own PostgreSQL database with complete data isolation.

Architecture:
- Each tenant has a unique subdomain (tenant.loomworks.app)
- Database routing uses Odoo's dbfilter with subdomain extraction
- Tenant metadata stored in management database (loomworks_mgmt)

References:
- Design document: openspec/changes/phase5-infrastructure/design.md
- Decision 1: Multi-Tenancy Architecture
- Decision 10: Multi-Tenant Architecture for Forked Core
"""

from loomworks import models, fields, api
from loomworks.exceptions import ValidationError, UserError
import re
import logging

_logger = logging.getLogger(__name__)


class LoomworksTenant(models.Model):
    """
    Tenant configuration for multi-tenant SaaS deployment.

    Each tenant represents a separate customer database with:
    - Unique subdomain for routing
    - Resource limits (users, storage, AI operations)
    - Subscription and billing configuration
    - Snapshot management
    """
    _name = 'loomworks.tenant'
    _description = 'Loomworks Tenant'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(
        string='Tenant Name',
        required=True,
        help='Display name for this tenant'
    )

    # Database configuration
    database_name = fields.Char(
        string='Database Name',
        required=True,
        readonly=True,
        copy=False,
        help='PostgreSQL database name for this tenant'
    )
    subdomain = fields.Char(
        string='Subdomain',
        required=True,
        index=True,
        copy=False,
        help='Subdomain for routing (e.g., "acme" for acme.loomworks.app)'
    )

    # State management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('provisioning', 'Provisioning'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('archived', 'Archived'),
    ], string='State', default='draft', required=True, tracking=True)

    # Resource limits
    max_users = fields.Integer(
        string='Max Users',
        default=10,
        help='Maximum number of active users'
    )
    max_storage_gb = fields.Float(
        string='Max Storage (GB)',
        default=5.0,
        help='Maximum storage in gigabytes'
    )
    max_ai_operations_daily = fields.Integer(
        string='Max AI Operations/Day',
        default=100,
        help='Maximum AI operations per day'
    )
    max_snapshots = fields.Integer(
        string='Max Snapshots',
        default=50,
        help='Maximum number of snapshots to retain'
    )

    # Current usage (computed/updated periodically)
    current_users = fields.Integer(
        string='Current Users',
        readonly=True,
        help='Current number of active users'
    )
    current_storage_gb = fields.Float(
        string='Current Storage (GB)',
        readonly=True,
        help='Current storage usage in gigabytes'
    )
    current_ai_operations_today = fields.Integer(
        string='AI Operations Today',
        readonly=True,
        help='AI operations used today'
    )

    # Billing and subscription
    tier = fields.Selection([
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Professional'),
        ('enterprise', 'Enterprise'),
    ], string='Subscription Tier', default='free', required=True)

    subscription_start = fields.Date(
        string='Subscription Start'
    )
    subscription_expires = fields.Date(
        string='Subscription Expires',
        help='When the current subscription period ends'
    )
    billing_email = fields.Char(
        string='Billing Email'
    )

    # Owner/Admin
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        help='Primary owner/administrator of this tenant'
    )
    admin_email = fields.Char(
        string='Admin Email',
        help='Primary admin contact email'
    )

    # Snapshots
    snapshot_ids = fields.One2many(
        'loomworks.snapshot',
        'tenant_id',
        string='Snapshots'
    )
    snapshot_count = fields.Integer(
        string='Snapshot Count',
        compute='_compute_snapshot_count'
    )
    last_snapshot_id = fields.Many2one(
        'loomworks.snapshot',
        string='Last Snapshot',
        compute='_compute_last_snapshot'
    )

    # Schedules and retention
    schedule_ids = fields.One2many(
        'loomworks.snapshot.schedule',
        'tenant_id',
        string='Snapshot Schedules'
    )
    retention_ids = fields.One2many(
        'loomworks.snapshot.retention',
        'tenant_id',
        string='Retention Policies'
    )

    # Timestamps
    created_at = fields.Datetime(
        string='Created At',
        default=fields.Datetime.now,
        readonly=True
    )
    provisioned_at = fields.Datetime(
        string='Provisioned At',
        readonly=True
    )
    activated_at = fields.Datetime(
        string='Activated At',
        readonly=True
    )
    suspended_at = fields.Datetime(
        string='Suspended At',
        readonly=True
    )
    last_accessed = fields.Datetime(
        string='Last Accessed',
        readonly=True
    )

    # Notes and metadata
    notes = fields.Text(
        string='Notes'
    )
    metadata = fields.Text(
        string='Metadata (JSON)',
        help='Additional tenant metadata in JSON format'
    )

    # SQL constraints
    _sql_constraints = [
        ('subdomain_unique', 'UNIQUE(subdomain)', 'Subdomain must be unique'),
        ('database_name_unique', 'UNIQUE(database_name)', 'Database name must be unique'),
    ]

    @api.constrains('subdomain')
    def _check_subdomain(self):
        """Validate subdomain format."""
        for tenant in self:
            if not tenant.subdomain:
                continue

            # Must be lowercase alphanumeric with hyphens, 3-63 chars, start with letter
            if not re.match(r'^[a-z][a-z0-9-]{2,62}$', tenant.subdomain):
                raise ValidationError(
                    "Subdomain must be lowercase alphanumeric with hyphens, "
                    "3-63 characters, starting with a letter"
                )

            # Reserved subdomains
            reserved = ['www', 'api', 'admin', 'app', 'mail', 'smtp', 'ftp',
                       'staging', 'production', 'dev', 'test', 'demo']
            if tenant.subdomain in reserved:
                raise ValidationError(f"Subdomain '{tenant.subdomain}' is reserved")

    @api.constrains('database_name')
    def _check_database_name(self):
        """Validate database name format."""
        for tenant in self:
            if not tenant.database_name:
                continue

            # PostgreSQL database name constraints
            if not re.match(r'^[a-z][a-z0-9_]{2,62}$', tenant.database_name):
                raise ValidationError(
                    "Database name must be lowercase alphanumeric with underscores, "
                    "3-63 characters, starting with a letter"
                )

    @api.model_create_multi
    def create(self, vals_list):
        """Generate database_name from subdomain if not provided."""
        for vals in vals_list:
            if 'database_name' not in vals and 'subdomain' in vals:
                # Convert subdomain to database name (hyphens to underscores)
                vals['database_name'] = 'lw_' + vals['subdomain'].replace('-', '_')
        return super().create(vals_list)

    def _compute_snapshot_count(self):
        for tenant in self:
            tenant.snapshot_count = len(tenant.snapshot_ids.filtered(
                lambda s: s.state == 'ready'
            ))

    def _compute_last_snapshot(self):
        for tenant in self:
            snapshots = tenant.snapshot_ids.filtered(
                lambda s: s.state == 'ready'
            ).sorted('create_date', reverse=True)
            tenant.last_snapshot_id = snapshots[0] if snapshots else False

    def action_provision(self):
        """
        Provision the tenant database.

        This initiates the database creation process:
        1. Creates PostgreSQL database
        2. Initializes Odoo base modules
        3. Creates admin user
        """
        self.ensure_one()

        if self.state != 'draft':
            raise UserError(f"Cannot provision tenant in state '{self.state}'")

        self.write({
            'state': 'provisioning',
        })

        # In production, this would:
        # 1. Create the PostgreSQL database
        # 2. Initialize Odoo schema
        # 3. Create initial admin user
        # This is typically handled by external orchestration

        _logger.info(
            "Tenant '%s' provisioning initiated for database '%s'",
            self.name, self.database_name
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Provisioning Started',
                'message': f"Database '{self.database_name}' is being created",
                'type': 'info',
            }
        }

    def action_activate(self):
        """
        Activate the tenant after provisioning.
        """
        self.ensure_one()

        if self.state not in ('provisioning', 'suspended'):
            raise UserError(f"Cannot activate tenant in state '{self.state}'")

        self.write({
            'state': 'active',
            'activated_at': fields.Datetime.now(),
            'suspended_at': False,
        })

        if self.state == 'provisioning':
            self.write({'provisioned_at': fields.Datetime.now()})

        _logger.info("Tenant '%s' activated", self.name)
        return True

    def action_suspend(self):
        """
        Suspend the tenant (e.g., for non-payment).
        """
        self.ensure_one()

        if self.state != 'active':
            raise UserError(f"Cannot suspend tenant in state '{self.state}'")

        self.write({
            'state': 'suspended',
            'suspended_at': fields.Datetime.now(),
        })

        _logger.warning("Tenant '%s' suspended", self.name)
        return True

    def action_archive(self):
        """
        Archive the tenant (soft delete).
        """
        self.ensure_one()

        if self.state == 'archived':
            return True

        self.write({
            'state': 'archived',
        })

        _logger.info("Tenant '%s' archived", self.name)
        return True

    def check_resource_limit(self, resource_type, current_value=None):
        """
        Check if a resource limit would be exceeded.

        Args:
            resource_type: 'users', 'storage', 'ai_operations', 'snapshots'
            current_value: Current value to check (if None, uses stored current)

        Returns:
            tuple: (is_within_limit, remaining, limit)
        """
        self.ensure_one()

        limits = {
            'users': (self.max_users, current_value or self.current_users),
            'storage': (self.max_storage_gb, current_value or self.current_storage_gb),
            'ai_operations': (self.max_ai_operations_daily,
                            current_value or self.current_ai_operations_today),
            'snapshots': (self.max_snapshots, current_value or self.snapshot_count),
        }

        if resource_type not in limits:
            raise ValueError(f"Unknown resource type: {resource_type}")

        limit, current = limits[resource_type]
        remaining = limit - current
        is_within = current < limit

        return (is_within, max(0, remaining), limit)

    def get_url(self, base_domain='loomworks.app'):
        """
        Get the full URL for this tenant.

        Args:
            base_domain: Base domain for the installation

        Returns:
            str: Full URL (e.g., https://acme.loomworks.app)
        """
        self.ensure_one()
        return f"https://{self.subdomain}.{base_domain}"

    @api.model
    def get_tenant_for_subdomain(self, subdomain):
        """
        Look up tenant by subdomain.

        Args:
            subdomain: Subdomain to look up

        Returns:
            loomworks.tenant record or False
        """
        return self.search([
            ('subdomain', '=', subdomain),
            ('state', '=', 'active'),
        ], limit=1)

    def update_usage_stats(self):
        """
        Update current usage statistics for this tenant.

        This should be called periodically to refresh usage data.
        In production, this would query the tenant's actual database.
        """
        self.ensure_one()

        # In a real implementation, this would:
        # 1. Connect to tenant database
        # 2. Query user count, storage usage, etc.
        # 3. Update the fields

        _logger.debug("Updated usage stats for tenant '%s'", self.name)
        return True

    @api.model
    def cleanup_expired_subscriptions(self):
        """
        Suspend tenants with expired subscriptions.

        Called by scheduled action.
        """
        today = fields.Date.today()
        expired = self.search([
            ('state', '=', 'active'),
            ('subscription_expires', '<', today),
        ])

        for tenant in expired:
            tenant.action_suspend()
            _logger.warning(
                "Tenant '%s' suspended due to expired subscription",
                tenant.name
            )

        return len(expired)
