# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from . import models
from . import tools

# compatibility imports
from loomworks.addons.iap.tools.iap_tools import iap_jsonrpc as jsonrpc
from loomworks.addons.iap.tools.iap_tools import iap_authorize as authorize
from loomworks.addons.iap.tools.iap_tools import iap_cancel as cancel
from loomworks.addons.iap.tools.iap_tools import iap_capture as capture
from loomworks.addons.iap.tools.iap_tools import iap_charge as charge
from loomworks.addons.iap.tools.iap_tools import InsufficientCreditError
