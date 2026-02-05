# Loomworks ERP

**AI-First Open-Source ERP based on Odoo Community v18**

Loomworks ERP is a fork of [Odoo Community](https://github.com/odoo/odoo) that reimagines enterprise resource planning with artificial intelligence at its core. Users interact primarily with Claude AI agents rather than traditional forms and menus.

## Key Features

- **AI-Driven Operations**: Eliminate the need for developer labor by having AI perform all ERP operations
- **Database Snapshots**: Point-in-time recovery for AI rollback (undo mistakes)
- **Interactive Dashboards**: React-powered business intelligence dashboards
- **Skills Framework**: Workflow automation through natural language
- **Open Source**: Free software with optional hosted database services

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Odoo Community v18, Python 3.10+ |
| Database | PostgreSQL 15+ with WAL archiving |
| AI | Claude Agent SDK, MCP (Model Context Protocol) |
| Frontend | Owl.js (Odoo), React 18+ (Dashboards) |
| Caching | Redis 7+ |

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 15+
- Node.js 20+ (LTS)
- Redis 7+

### Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/woodwosj/LoomworksERP.git
   cd LoomworksERP
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Odoo with the Loomworks addons path:
   ```bash
   ./odoo-bin -d loomworks --addons-path=addons,loomworks_addons -i loomworks_core
   ```

4. Access at `http://localhost:8069`

## Project Structure

```
LoomworksERP/
├── loomworks_addons/          # Custom Loomworks modules
│   └── loomworks_core/        # Branding and core configuration
├── openspec/                  # Project specifications
├── docs/                      # Documentation
├── LICENSE                    # LGPL v3
└── README.md
```

## Modules

### loomworks_core (Phase 1)

Foundation module providing:
- Loomworks branding (logos, colors, favicon)
- Custom SCSS theme with color palette
- QWeb template overrides
- Base configuration for all Loomworks modules

## Development

### Code Style

- **Python**: Follow [Odoo Coding Guidelines](https://www.odoo.com/documentation/18.0/contributing/development/coding_guidelines.html)
- **SCSS**: Variables in `primary_variables.scss`, custom styles in `loomworks_backend.scss`
- **XML**: 4-space indentation, descriptive IDs

### Running Tests

```bash
python -m pytest loomworks_addons/*/tests/
```

### Commit Convention

```
[module] type: description

Types: feat, fix, refactor, docs, test, chore
Example: [loomworks_core] feat: add custom color palette
```

## License

Loomworks ERP is licensed under the [GNU Lesser General Public License v3 (LGPL-3)](LICENSE).

This software is a fork of Odoo Community v18. Original software copyright: Odoo S.A.

### LGPL-3 Compliance

- All source code is available under LGPL-3
- Modifications are clearly marked
- Copyright notices are preserved
- No code from Odoo Enterprise is included

## Attribution

- **Odoo Community**: [github.com/odoo/odoo](https://github.com/odoo/odoo) - Original ERP framework
- **Odoo S.A.**: Original copyright holder of Odoo Community

## Contributing

Contributions are welcome! Please read our contributing guidelines and ensure all code:
- Follows the coding style guide
- Includes appropriate tests
- Has proper LGPL-3 headers
- Does not include any Enterprise code

## Support

- **Website**: [loomworks.app](https://loomworks.app)
- **GitHub Issues**: [github.com/woodwosj/LoomworksERP/issues](https://github.com/woodwosj/LoomworksERP/issues)

---

Copyright (c) 2024-2026 Loomworks. Licensed under LGPL-3.
