/** @loomworks-module **/
// Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
//
// This file is part of Loomworks ERP, a fork of Odoo Community.
// Original software copyright: Odoo S.A.
// Loomworks modifications copyright: Loomworks
// License: LGPL-3

import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";

/**
 * Patch the Dialog component to use "Loomworks ERP" as the default
 * title instead of "Odoo".
 */
patch(Dialog, {
    defaultProps: {
        ...Dialog.defaultProps,
        title: "Loomworks ERP",
    },
});
