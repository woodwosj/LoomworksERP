# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import http
from loomworks.http import request
from loomworks.addons.web.controllers.webclient import WebClient


class WebsiteWebClient(WebClient):
    @http.route()
    def bundle(self, bundle_name, **bundle_params):
        if 'website_id' in bundle_params:
            request.update_context(website_id=int(bundle_params['website_id']))
        return super().bundle(bundle_name, **bundle_params)
