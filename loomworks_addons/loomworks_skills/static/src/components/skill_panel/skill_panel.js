/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Skill Panel Component
 *
 * Displays available skills in a sidebar panel, allowing users to
 * browse, search, and execute skills directly.
 */
export class SkillPanel extends Component {
    static template = "loomworks_skills.SkillPanel";
    static props = {
        onSkillSelect: { type: Function, optional: true },
        category: { type: String, optional: true },
        compact: { type: Boolean, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.skillIntent = useService("skillIntent");
        this.notification = useService("notification");

        this.state = useState({
            skills: [],
            loading: true,
            searchQuery: "",
            selectedCategory: this.props.category || null,
            expandedSkillId: null,
        });

        onWillStart(async () => {
            await this.loadSkills();
        });
    }

    get categories() {
        return [
            { value: null, label: "All" },
            { value: "sales", label: "Sales" },
            { value: "purchase", label: "Purchasing" },
            { value: "inventory", label: "Inventory" },
            { value: "accounting", label: "Accounting" },
            { value: "hr", label: "HR" },
            { value: "crm", label: "CRM" },
            { value: "project", label: "Project" },
            { value: "custom", label: "Custom" },
        ];
    }

    get filteredSkills() {
        let skills = this.state.skills;

        if (this.state.selectedCategory) {
            skills = skills.filter(s => s.category === this.state.selectedCategory);
        }

        if (this.state.searchQuery) {
            const query = this.state.searchQuery.toLowerCase();
            skills = skills.filter(s =>
                s.name.toLowerCase().includes(query) ||
                (s.description && s.description.toLowerCase().includes(query))
            );
        }

        return skills;
    }

    async loadSkills() {
        this.state.loading = true;

        try {
            const domain = [['state', '=', 'active']];
            const skills = await this.orm.searchRead(
                'loomworks.skill',
                domain,
                ['name', 'technical_name', 'category', 'description', 'is_builtin', 'success_rate', 'execution_count'],
                { order: 'category, name' }
            );
            this.state.skills = skills;
        } catch (e) {
            console.error("Failed to load skills:", e);
            this.notification.add("Failed to load skills", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    onCategoryChange(ev) {
        this.state.selectedCategory = ev.target.value || null;
    }

    toggleSkillExpanded(skillId) {
        if (this.state.expandedSkillId === skillId) {
            this.state.expandedSkillId = null;
        } else {
            this.state.expandedSkillId = skillId;
        }
    }

    async onSkillClick(skill) {
        if (this.props.onSkillSelect) {
            this.props.onSkillSelect(skill);
        } else {
            await this.executeSkill(skill);
        }
    }

    async executeSkill(skill) {
        try {
            const result = await this.skillIntent.executeSkill(skill.id, {});

            if (result.type === 'skill.input_required') {
                // Show input dialog or pass to chat
                this.notification.add(`Skill "${skill.name}" needs more information`, {
                    type: "info",
                });
            }
        } catch (e) {
            console.error("Skill execution failed:", e);
        }
    }

    getCategoryIcon(category) {
        const icons = {
            sales: 'fa-shopping-cart',
            purchase: 'fa-truck',
            inventory: 'fa-cubes',
            accounting: 'fa-calculator',
            hr: 'fa-users',
            manufacturing: 'fa-industry',
            crm: 'fa-handshake-o',
            project: 'fa-tasks',
            custom: 'fa-puzzle-piece',
        };
        return icons[category] || 'fa-magic';
    }

    formatSuccessRate(rate) {
        if (rate === undefined || rate === null) return '-';
        return `${Math.round(rate * 100)}%`;
    }
}
