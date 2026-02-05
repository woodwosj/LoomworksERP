# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SignAuditLog(models.Model):
    """Signature Audit Log

    Provides tamper-evident audit trail for signature requests.
    Each entry is chained to the previous using cryptographic hashes,
    creating a blockchain-style integrity verification system.
    """
    _name = 'sign.audit.log'
    _description = 'Signature Audit Log'
    _order = 'timestamp desc'
    _rec_name = 'action'

    request_id = fields.Many2one(
        'sign.request',
        string='Request',
        required=True,
        ondelete='cascade',
        index=True
    )
    signer_id = fields.Many2one(
        'sign.request.signer',
        string='Signer',
        help='Signer associated with this action (if applicable)'
    )

    # Event Details
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        required=True,
        index=True
    )
    action = fields.Selection([
        ('create', 'Request Created'),
        ('send', 'Request Sent'),
        ('view', 'Document Viewed'),
        ('sign', 'Signature Applied'),
        ('complete', 'Document Completed'),
        ('refuse', 'Signature Refused'),
        ('cancel', 'Request Cancelled'),
        ('expire', 'Request Expired'),
        ('download', 'Document Downloaded'),
        ('resend', 'Request Resent'),
    ], string='Action', required=True)

    description = fields.Char(
        string='Description',
        help='Human-readable description of the action'
    )

    # Context Information
    ip_address = fields.Char(
        string='IP Address',
        help='IP address of the client'
    )
    user_agent = fields.Char(
        string='User Agent',
        help='Browser/client identification'
    )
    geo_location = fields.Char(
        string='Location',
        help='Geographic location if available'
    )

    # Integrity Verification
    hash_value = fields.Char(
        string='Entry Hash',
        required=True,
        help='SHA-256 hash of this log entry'
    )
    previous_hash = fields.Char(
        string='Previous Hash',
        required=True,
        help='Hash of previous log entry (blockchain-style chain)'
    )

    # Related fields
    request_name = fields.Char(
        related='request_id.name',
        string='Request Reference'
    )
    signer_name = fields.Char(
        related='signer_id.partner_id.name',
        string='Signer Name'
    )

    def verify_chain_integrity(self):
        """Verify the integrity of the audit log chain.

        Returns True if the chain is valid, False otherwise.
        """
        import hashlib

        logs = self.sorted('timestamp')
        previous_hash = '0' * 64

        for log in logs:
            # Verify previous hash matches
            if log.previous_hash != previous_hash:
                return False

            # Verify current hash
            log_content = f'{log.request_id.id}|{log.action}|{log.description}|{log.timestamp}|{log.previous_hash}'
            expected_hash = hashlib.sha256(log_content.encode()).hexdigest()

            if log.hash_value != expected_hash:
                return False

            previous_hash = log.hash_value

        return True

    @api.model
    def verify_request_integrity(self, request_id):
        """Verify integrity of all logs for a specific request."""
        logs = self.search([('request_id', '=', request_id)], order='timestamp')
        return logs.verify_chain_integrity()

    @api.model
    def _cron_verify_integrity(self):
        """Cron job to verify audit log chain integrity for recent requests."""
        import logging
        _logger = logging.getLogger(__name__)
        # Check integrity of logs for recently active requests
        recent_requests = self.env['sign.request'].search([
            ('state', 'in', ['sent', 'signing', 'done']),
        ], limit=100, order='write_date desc')
        for req in recent_requests:
            logs = self.search([('request_id', '=', req.id)], order='timestamp')
            if logs and not logs.verify_chain_integrity():
                _logger.warning(
                    "Audit log integrity check FAILED for request %s (ID: %s)",
                    req.name, req.id
                )
