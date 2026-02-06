/** @loomworks-module **/
// Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
//
// This file is part of Loomworks ERP, a fork of Odoo Community.
// Original software copyright: Odoo S.A.
// Loomworks modifications copyright: Loomworks
// License: LGPL-3

import { registry } from "@web/core/registry";

/**
 * Override the default title service so the browser tab shows
 * "Loomworks ERP" instead of "Odoo" when no other title part is set.
 */
const loomworksTitleService = {
    start() {
        const titleCounters = {};
        const titleParts = {};

        function getParts() {
            return Object.assign({}, titleParts);
        }

        function setCounters(counters) {
            for (const key in counters) {
                const val = counters[key];
                if (!val) {
                    delete titleCounters[key];
                } else {
                    titleCounters[key] = val;
                }
            }
            updateTitle();
        }

        function setParts(parts) {
            for (const key in parts) {
                const val = parts[key];
                if (!val) {
                    delete titleParts[key];
                } else {
                    titleParts[key] = val;
                }
            }
            updateTitle();
        }

        function updateTitle() {
            const counter = Object.values(titleCounters).reduce((acc, count) => acc + count, 0);
            const name = Object.values(titleParts).join(" - ") || "Loomworks ERP";
            if (!counter) {
                document.title = name;
            } else {
                document.title = `(${counter}) ${name}`;
            }
        }

        return {
            get current() {
                return document.title;
            },
            getParts,
            setCounters,
            setParts,
        };
    },
};

// Replace the existing "title" service with our Loomworks-branded version.
// Using force: true so it overrides the original registration from web module.
registry.category("services").add("title", loomworksTitleService, { force: true });
