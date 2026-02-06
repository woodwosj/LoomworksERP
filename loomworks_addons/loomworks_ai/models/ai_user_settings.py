# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
AI User Settings Model

Stores user preferences for proactive AI assistance.
Simple controls: suggestions on/off, frequency, and notification style.

Privacy Note: Vision/screenshot analysis consent is covered in the EULA
at signup. Anthropic has strict data privacy policies - user data is not
used for AI training.

Based on: FEATURE_CONTEXTUAL_AI_NAVBAR.md
"""

from loomworks import models, fields, api


class AIUserSettings(models.Model):
    """
    User-specific AI assistant preferences.

    Each user can customize how the AI assistant behaves:
    - Enable/disable proactive suggestions
    - Set suggestion frequency (minimal, normal, frequent)
    - Choose notification style (badge or popup)
    """
    _name = 'loomworks.ai.user.settings'
    _description = 'AI User Preferences'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.user,
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    # =========================================================================
    # CORE SETTINGS (Simple)
    # =========================================================================

    enable_suggestions = fields.Boolean(
        string='Enable Proactive Suggestions',
        default=True,
        help="Allow AI to offer helpful suggestions based on your actions"
    )

    suggestion_frequency = fields.Selection([
        ('minimal', 'Minimal - Only critical issues'),
        ('normal', 'Normal - Helpful suggestions'),
        ('frequent', 'Frequent - More proactive'),
    ], string='Suggestion Frequency', default='normal', required=True,
       help="""How often the AI offers suggestions:
       - Minimal: Only critical issues like errors or overdue payments
       - Normal: Helpful suggestions without being intrusive
       - Frequent: More proactive assistance""")

    notification_style = fields.Selection([
        ('badge', 'Badge only'),
        ('popup', 'Popup notification'),
    ], string='Notification Style', default='popup', required=True,
       help="""How suggestions appear:
       - Badge: Unobtrusive dot on AI button
       - Popup: Brief popup notification""")

    # =========================================================================
    # ADVANCED SETTINGS
    # =========================================================================

    show_context_indicator = fields.Boolean(
        string='Show Context Indicator',
        default=True,
        help="Display what the AI understands about your current context"
    )

    enable_quick_actions = fields.Boolean(
        string='Enable Quick Actions',
        default=True,
        help="Show context-specific quick action buttons in AI dropdown"
    )

    auto_expand_chat = fields.Boolean(
        string='Auto-expand Chat on Error',
        default=False,
        help="Automatically open AI chat when an error occurs"
    )

    keyboard_shortcut = fields.Selection([
        ('ctrl_space', 'Ctrl + Space'),
        ('ctrl_k', 'Ctrl + K'),
        ('alt_a', 'Alt + A'),
        ('disabled', 'Disabled'),
    ], string='Keyboard Shortcut', default='ctrl_space',
       help="Keyboard shortcut to open AI assistant")

    # =========================================================================
    # RATE LIMITING PREFERENCES
    # =========================================================================

    max_suggestions_per_session = fields.Integer(
        string='Max Suggestions per Session',
        default=10,
        help="Maximum number of proactive suggestions per browser session"
    )

    cooldown_seconds = fields.Integer(
        string='Suggestion Cooldown (seconds)',
        default=60,
        help="Minimum time between proactive suggestions"
    )

    # =========================================================================
    # CONSTRAINTS
    # =========================================================================

    _sql_constraints = [
        ('user_company_uniq', 'UNIQUE(user_id, company_id)',
         'Settings already exist for this user in this company'),
    ]

    @api.constrains('max_suggestions_per_session')
    def _check_max_suggestions(self):
        for settings in self:
            if settings.max_suggestions_per_session < 0:
                from loomworks.exceptions import ValidationError
                raise ValidationError('Max suggestions cannot be negative')

    @api.constrains('cooldown_seconds')
    def _check_cooldown(self):
        for settings in self:
            if settings.cooldown_seconds < 0:
                from loomworks.exceptions import ValidationError
                raise ValidationError('Cooldown cannot be negative')

    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    @api.model
    def get_user_settings(self, user_id=None):
        """
        Get settings for a user, creating defaults if needed.

        Args:
            user_id: User ID to get settings for (defaults to current user)

        Returns:
            loomworks.ai.user.settings record
        """
        user_id = user_id or self.env.uid

        settings = self.search([
            ('user_id', '=', user_id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not settings:
            settings = self.create({
                'user_id': user_id,
                'company_id': self.env.company.id,
            })

        return settings

    def get_settings_dict(self):
        """
        Return settings as a dictionary for frontend consumption.

        Returns:
            dict: Settings with camelCase keys for JavaScript
        """
        self.ensure_one()
        return {
            'enableSuggestions': self.enable_suggestions,
            'suggestionFrequency': self.suggestion_frequency,
            'notificationStyle': self.notification_style,
            'showContextIndicator': self.show_context_indicator,
            'enableQuickActions': self.enable_quick_actions,
            'autoExpandChatOnError': self.auto_expand_chat,
            'keyboardShortcut': self.keyboard_shortcut,
            'maxSuggestionsPerSession': self.max_suggestions_per_session,
            'cooldownSeconds': self.cooldown_seconds,
        }

    @api.model
    def update_user_settings(self, values):
        """
        Update settings for current user.

        Args:
            values: Dict with camelCase keys from frontend

        Returns:
            dict: Updated settings
        """
        settings = self.get_user_settings()

        # Map frontend keys to model fields
        field_map = {
            'enableSuggestions': 'enable_suggestions',
            'suggestionFrequency': 'suggestion_frequency',
            'notificationStyle': 'notification_style',
            'showContextIndicator': 'show_context_indicator',
            'enableQuickActions': 'enable_quick_actions',
            'autoExpandChatOnError': 'auto_expand_chat',
            'keyboardShortcut': 'keyboard_shortcut',
            'maxSuggestionsPerSession': 'max_suggestions_per_session',
            'cooldownSeconds': 'cooldown_seconds',
        }

        write_vals = {}
        for frontend_key, backend_field in field_map.items():
            if frontend_key in values:
                write_vals[backend_field] = values[frontend_key]

        if write_vals:
            settings.write(write_vals)

        return settings.get_settings_dict()

    @api.model
    def get_frequency_config(self, frequency=None):
        """
        Get rate limiting configuration for a frequency level.

        Args:
            frequency: 'minimal', 'normal', or 'frequent' (defaults to user setting)

        Returns:
            dict: Configuration with max_per_session and cooldown_ms
        """
        if not frequency:
            settings = self.get_user_settings()
            frequency = settings.suggestion_frequency

        configs = {
            'minimal': {
                'max_per_session': 5,
                'cooldown_ms': 120000,  # 2 minutes
                'triggers': ['error_occurred'],
            },
            'normal': {
                'max_per_session': 10,
                'cooldown_ms': 60000,  # 1 minute
                'triggers': ['error_occurred', 'view_loaded', 'record_created'],
            },
            'frequent': {
                'max_per_session': 20,
                'cooldown_ms': 30000,  # 30 seconds
                'triggers': [
                    'error_occurred', 'view_loaded', 'record_created',
                    'record_selected', 'action_executed', 'idle_threshold'
                ],
            },
        }

        return configs.get(frequency, configs['normal'])
