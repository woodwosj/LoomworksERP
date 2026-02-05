# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
AI Tool Provider Mixin - Enables any module to register AI tools dynamically.

This implements the M4 resolution from PATCH_NOTES_M1_M4.md, providing a standard
pattern for Phase 3+ modules to contribute AI tools without modifying loomworks_ai.

Usage:
    1. Create a model that inherits from 'loomworks.ai.tool.provider'
    2. Implement _get_tool_definitions() returning a list of tool dicts
    3. Tools are auto-registered on module installation

Example (in Phase 3.1 Studio module):
    class StudioToolProvider(models.AbstractModel):
        _name = 'studio.tool.provider'
        _inherit = 'loomworks.ai.tool.provider'

        @api.model
        def _get_tool_definitions(self):
            return [
                {
                    'name': 'Create Studio App',
                    'technical_name': 'studio_create_app',
                    'category': 'action',
                    'description': 'Create a new custom application via Studio',
                    'parameters_schema': {...},
                    'implementation_method': 'loomworks_studio.services.tools.create_app',
                    'risk_level': 'moderate',
                },
            ]

Research Sources:
- Odoo 18 Registries: https://www.odoo.com/documentation/18.0/developer/reference/frontend/registries.html
- A Guide to Registries in Odoo 18: https://bassaminfotech.com/odoo18-registries/
- Dynamic Tool Updates in MCP: https://spring.io/blog/2025/05/04/spring-ai-dynamic-tool-updates-with-mcp/
"""

from odoo import api, models, fields
import json
import logging

_logger = logging.getLogger(__name__)


class AIToolProvider(models.AbstractModel):
    """
    Abstract mixin for modules that provide AI tools.

    Inherit from this model and implement _get_tool_definitions() to register
    AI tools from your module. Tools are automatically discovered and registered
    when the AI tool registry refreshes.
    """
    _name = 'loomworks.ai.tool.provider'
    _description = 'AI Tool Provider Mixin'

    @api.model
    def _get_tool_definitions(self):
        """
        Override in inheriting models to return tool definitions.

        Returns:
            list: List of dicts, each defining an AI tool with keys:
                - name (str): Display name
                - technical_name (str): Unique snake_case identifier
                - category (str): 'data', 'action', 'report', or 'system'
                - description (str): Detailed description for AI
                - parameters_schema (dict): JSON Schema for parameters
                - implementation_method (str): Python method path or model method
                - risk_level (str): 'safe', 'moderate', 'high', or 'critical'
                - requires_confirmation (bool, optional): Default False
                - returns_description (str, optional): What the tool returns
                - sequence (int, optional): Ordering within category
        """
        return []

    @api.model
    def _register_tools(self):
        """
        Register all tools from this provider.
        Creates or updates loomworks.ai.tool records for each tool definition.
        """
        AITool = self.env['loomworks.ai.tool']
        definitions = self._get_tool_definitions()
        registered_count = 0

        for tool_def in definitions:
            technical_name = tool_def.get('technical_name')
            if not technical_name:
                _logger.warning(
                    "Tool definition missing technical_name in %s: %s",
                    self._name, tool_def.get('name', 'Unknown')
                )
                continue

            # Build tool values
            parameters_schema = tool_def.get('parameters_schema', {
                'type': 'object',
                'properties': {},
                'required': []
            })
            if isinstance(parameters_schema, dict):
                parameters_schema = json.dumps(parameters_schema)

            tool_vals = {
                'name': tool_def.get('name', technical_name),
                'technical_name': technical_name,
                'category': tool_def.get('category', 'data'),
                'description': tool_def.get('description', ''),
                'parameters_schema': parameters_schema,
                'implementation_method': tool_def.get('implementation_method', ''),
                'risk_level': tool_def.get('risk_level', 'safe'),
                'requires_confirmation': tool_def.get('requires_confirmation', False),
                'returns_description': tool_def.get('returns_description', ''),
                'sequence': tool_def.get('sequence', 10),
                'active': True,
            }

            # Check if tool already exists
            existing = AITool.search([
                ('technical_name', '=', technical_name)
            ], limit=1)

            try:
                if existing:
                    existing.write(tool_vals)
                    _logger.debug("Updated AI tool: %s", technical_name)
                else:
                    AITool.create(tool_vals)
                    _logger.info("Registered AI tool: %s from %s", technical_name, self._name)
                registered_count += 1
            except Exception as e:
                _logger.error(
                    "Failed to register AI tool %s from %s: %s",
                    technical_name, self._name, e
                )

        return registered_count

    @api.model
    def _unregister_tools(self):
        """
        Unregister all tools from this provider.
        Called on module uninstallation to clean up tool records.
        """
        AITool = self.env['loomworks.ai.tool']
        definitions = self._get_tool_definitions()
        unregistered_count = 0

        for tool_def in definitions:
            technical_name = tool_def.get('technical_name')
            if technical_name:
                tools = AITool.search([('technical_name', '=', technical_name)])
                if tools:
                    tools.unlink()
                    _logger.info("Unregistered AI tool: %s", technical_name)
                    unregistered_count += 1

        return unregistered_count


class AIToolRegistry(models.Model):
    """
    Registry for discovering and managing all tool providers across installed modules.

    This model maintains a central registry of all ToolProvider implementations
    and orchestrates tool registration/unregistration lifecycle.
    """
    _name = 'loomworks.ai.tool.registry'
    _description = 'AI Tool Registry'

    name = fields.Char(
        string='Registry Name',
        default='Default Tool Registry',
        required=True
    )
    last_refresh = fields.Datetime(
        string='Last Refresh',
        help='When tools were last discovered and registered'
    )
    provider_count = fields.Integer(
        string='Provider Count',
        compute='_compute_provider_count'
    )
    tool_count = fields.Integer(
        string='Tool Count',
        compute='_compute_tool_count'
    )

    def _compute_provider_count(self):
        for registry in self:
            registry.provider_count = len(self._discover_providers())

    def _compute_tool_count(self):
        for registry in self:
            registry.tool_count = self.env['loomworks.ai.tool'].search_count([])

    @api.model
    def _discover_providers(self):
        """
        Discover all models that inherit from loomworks.ai.tool.provider.

        Returns:
            list: Model names that are tool providers
        """
        provider_models = []

        for model_name, model_class in self.env.registry.items():
            if model_name == 'loomworks.ai.tool.provider':
                continue

            # Check if model inherits from tool provider
            parents = getattr(model_class, '_inherit', [])
            if isinstance(parents, str):
                parents = [parents]

            if 'loomworks.ai.tool.provider' in parents:
                provider_models.append(model_name)

        return provider_models

    @api.model
    def discover_and_register_all_tools(self):
        """
        Discover all ToolProvider implementations and register their tools.

        This method:
        1. Finds all models inheriting from loomworks.ai.tool.provider
        2. Calls _register_tools() on each provider
        3. Updates the registry timestamp

        Can be called:
        - On loomworks_ai module post_init_hook
        - When a new module with tools is installed
        - Manually via UI or scheduled action
        """
        provider_models = self._discover_providers()
        _logger.info(
            "Discovered %d AI tool providers: %s",
            len(provider_models), provider_models
        )

        total_registered = 0
        errors = []

        for model_name in provider_models:
            try:
                provider = self.env[model_name]
                count = provider._register_tools()
                total_registered += count
                _logger.info(
                    "Registered %d tools from provider: %s",
                    count, model_name
                )
            except Exception as e:
                error_msg = f"Failed to register tools from {model_name}: {e}"
                _logger.exception(error_msg)
                errors.append(error_msg)

        # Update registry timestamp
        registry = self.search([], limit=1)
        if not registry:
            registry = self.create({'name': 'Default Tool Registry'})
        registry.write({'last_refresh': fields.Datetime.now()})

        result = {
            'providers_found': len(provider_models),
            'tools_registered': total_registered,
            'errors': errors,
        }

        _logger.info(
            "Tool registration complete: %d providers, %d tools, %d errors",
            len(provider_models), total_registered, len(errors)
        )

        return result

    @api.model
    def refresh_tools(self):
        """
        Refresh all tool registrations.

        Alias for discover_and_register_all_tools().
        Useful for UI button action or scheduled refresh.
        """
        return self.discover_and_register_all_tools()

    def action_refresh_tools(self):
        """Button action to refresh tools from UI."""
        result = self.refresh_tools()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Tools Refreshed',
                'message': f"Registered {result['tools_registered']} tools from {result['providers_found']} providers.",
                'type': 'success' if not result['errors'] else 'warning',
                'sticky': False,
            }
        }


class CoreToolProvider(models.AbstractModel):
    """
    Core tool provider for loomworks_ai module's built-in tools.

    This demonstrates the tool provider pattern and registers the core
    MCP tools (search_records, create_record, etc.) that are also
    defined in ai_tool_data.xml.

    Note: The XML data file is the primary source; this provider can
    be used to programmatically verify/sync tool definitions.
    """
    _name = 'loomworks.ai.core.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Core AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """
        Return core tool definitions.

        Note: These are also defined in data/ai_tool_data.xml.
        This method can be used for validation or programmatic access.
        """
        # Core tools are defined in XML; returning empty to avoid duplicates
        # If XML is removed, uncomment the tool definitions below
        return []

        # Uncomment if you want programmatic tool registration instead of XML:
        # return [
        #     {
        #         'name': 'Search Records',
        #         'technical_name': 'search_records',
        #         'category': 'data',
        #         'risk_level': 'safe',
        #         'description': 'Search for records in any Odoo model.',
        #         'parameters_schema': {...},
        #         'implementation_method': 'loomworks_ai.services.odoo_mcp_tools.search_records',
        #     },
        #     # ... other tools
        # ]
