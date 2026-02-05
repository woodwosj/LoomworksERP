#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Loomworks ERP - An AI-first ERP system
# Copyright (C) 2024 Loomworks
#
# This program is based on Odoo Community Edition
# Copyright (C) 2004-2024 Odoo S.A. <https://www.odoo.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Loomworks Rebrand Script

Automates the replacement of Odoo branding with Loomworks branding.
Designed to be run after forking Odoo or fetching upstream updates.

Usage:
    python scripts/rebrand.py --check      # Report branding found (dry run)
    python scripts/rebrand.py --apply      # Apply replacements
    python scripts/rebrand.py --verify     # Check for missed branding
    python scripts/rebrand.py --report     # Generate detailed report
"""

import argparse
import csv
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ============================================
# CONFIGURATION
# ============================================

REBRAND_CONFIG = {
    'old_name': 'Odoo',
    'new_name': 'Loomworks',
    'old_name_lower': 'odoo',
    'new_name_lower': 'loomworks',
    'old_url': 'odoo.com',
    'new_url': 'loomworks.solutions',
    'old_author': 'OpenERP S.A.',
    'new_author': 'Loomworks (based on Odoo by Odoo S.A.)',
    'old_email': 'info@odoo.com',
    'new_email': 'support@loomworks.solutions',
    'preserve_attribution': True,  # LGPL requirement
}

# Text replacements (order matters - more specific patterns first)
STRING_REPLACEMENTS = {
    # URLs (specific first)
    'https://www.odoo.com': 'https://www.loomworks.solutions',
    'http://www.odoo.com': 'https://www.loomworks.solutions',
    'www.odoo.com': 'www.loomworks.solutions',
    'odoo.com': 'loomworks.solutions',

    # Email addresses
    'info@odoo.com': 'support@loomworks.solutions',

    # Product names in specific contexts (NOT in copyright/license sections)
    # These will be applied selectively
}

# Patterns for user-visible strings to replace (case-sensitive)
UI_STRING_REPLACEMENTS = {
    # Page titles and UI text
    "title or 'Odoo'": "title or 'Loomworks ERP'",
    'Powered by Odoo': 'Powered by Loomworks',
    '<span>Odoo</span>': '<span>Loomworks</span>',
    'Odoo Server': 'Loomworks ERP Server',
    'Odoo is a complete ERP': 'Loomworks ERP is a complete ERP',
    'alt="Odoo"': 'alt="Loomworks"',
    "alt='Odoo'": "alt='Loomworks'",
    'Odoo logo': 'Loomworks logo',

    # Check for Odoo text (will be handled carefully)
    "Check your network connection and come back here. Odoo will load":
        "Check your network connection and come back here. Loomworks ERP will load",
}

# release.py specific replacements
RELEASE_PY_REPLACEMENTS = {
    "product_name = 'Odoo'": "product_name = 'Loomworks ERP'",
    "description = 'Odoo Server'": "description = 'Loomworks ERP Server'",
    "url = 'https://www.odoo.com'": "url = 'https://www.loomworks.solutions'",
    "author = 'OpenERP S.A.'": "author = 'Loomworks (based on Odoo by Odoo S.A.)'",
    "author_email = 'info@odoo.com'": "author_email = 'support@loomworks.solutions'",
    "'''Odoo is a complete ERP and CRM.": "'''Loomworks ERP is a complete ERP and CRM. Based on Odoo Community Edition.",
}

# SCSS variable replacements
SCSS_REPLACEMENTS = {
    # Change the primary brand color from Odoo purple to Loomworks blue
    '#71639e': '#1e3a5f',  # Odoo purple -> Loomworks primary
    '#714B67': '#1e3a5f',  # Odoo secondary purple -> Loomworks primary
    '#875A7B': '#1e3a5f',  # Odoo email color -> Loomworks primary
}

# Files to replace entirely (Odoo file -> Loomworks asset)
FILE_REPLACEMENTS = {
    'addons/web/static/img/favicon.ico': 'assets/loomworks_favicon.ico',
    'addons/web/static/img/logo.png': 'assets/loomworks_logo.png',
    'addons/web/static/img/logo2.png': 'assets/loomworks_logo_alt.png',
    'addons/web/static/img/logo_inverse_white_206px.png': 'assets/loomworks_logo_white.png',
    'addons/web/static/img/odoo-icon-192x192.png': 'assets/loomworks_icon_192.png',
    'addons/web/static/img/odoo-icon-512x512.png': 'assets/loomworks_icon_512.png',
    'addons/web/static/img/odoo-icon-ios.png': 'assets/loomworks_icon_ios.png',
    'addons/web/static/img/odoo-icon.svg': 'assets/loomworks_icon.svg',
    'addons/web/static/img/odoo_logo.svg': 'assets/loomworks_logo.svg',
    'addons/web/static/img/odoo_logo_dark.svg': 'assets/loomworks_logo_dark.svg',
    'addons/web/static/img/odoo_logo_tiny.png': 'assets/loomworks_logo_tiny.png',
}

# Files to DELETE (no replacement needed)
FILES_TO_DELETE = [
    'addons/web/static/img/enterprise_upgrade.jpg',
]

# Patterns to detect remaining Odoo branding
DETECTION_PATTERNS = [
    # URLs
    (r'https?://[^\s"\']*odoo\.com[^\s"\']*', 'Odoo URL'),
    (r'mailto:[^\s"\']*@odoo\.com', 'Odoo email'),

    # Skip copyright/license sections - only flag UI-visible strings
    # We'll filter these in the detection function
]

# Patterns that indicate UI-visible "Odoo" strings
UI_VISIBLE_PATTERNS = [
    (r'>Odoo<', 'HTML visible text'),
    (r"'Odoo'", 'Quoted Odoo string'),
    (r'"Odoo"', 'Quoted Odoo string'),
    (r'alt="Odoo', 'Alt text'),
    (r"alt='Odoo", 'Alt text'),
    (r'Powered by.*Odoo', 'Powered by text'),
    (r'title.*Odoo', 'Title text'),
]

# Skip these file extensions
SKIP_EXTENSIONS = {
    '.po', '.pot',  # Translation files (defer to later phase)
    '.pyc', '.pyo',  # Compiled Python
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',  # Images (handled separately)
    '.woff', '.woff2', '.ttf', '.eot',  # Fonts
    '.pdf', '.doc', '.docx',  # Documents
    '.zip', '.tar', '.gz',  # Archives
}

# Skip these directories
SKIP_DIRECTORIES = {
    '.git',
    'node_modules',
    '__pycache__',
    '.idea',
    '.vscode',
    'locale',  # Translation directories (defer)
    'i18n',    # Translation directories (defer)
}

# Files to completely skip (never modify)
SKIP_FILES = {
    'LICENSE',
    'COPYING',
    'COPYRIGHT',
}

# File extensions that are text-based and should be processed
TEXT_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx',
    '.xml', '.html', '.htm', '.mako',
    '.scss', '.css', '.less',
    '.json', '.yaml', '.yml',
    '.md', '.rst', '.txt',
    '.sh', '.bash',
    '.conf', '.cfg', '.ini',
}


# ============================================
# UTILITY FUNCTIONS
# ============================================

def get_project_root() -> Path:
    """Get the project root directory."""
    # Assume script is in scripts/ directory
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent


def get_odoo_path() -> Path:
    """Get the path to the Odoo fork directory."""
    return get_project_root() / 'odoo'


def get_assets_path() -> Path:
    """Get the path to the assets directory."""
    return get_project_root() / 'assets'


def should_skip_file(filepath: Path) -> bool:
    """Check if a file should be skipped."""
    # Skip by filename
    if filepath.name in SKIP_FILES:
        return True

    # Skip by extension
    if filepath.suffix.lower() in SKIP_EXTENSIONS:
        return True

    # Skip if in a skip directory
    for part in filepath.parts:
        if part in SKIP_DIRECTORIES:
            return True

    return False


def is_text_file(filepath: Path) -> bool:
    """Check if a file is a text file that should be processed."""
    return filepath.suffix.lower() in TEXT_EXTENSIONS


def is_in_copyright_section(content: str, match_pos: int) -> bool:
    """
    Check if a match position is within a copyright/license section.
    We preserve Odoo S.A. attribution in these sections per LGPL requirements.
    """
    # Get context around the match (500 chars before)
    start = max(0, match_pos - 500)
    context = content[start:match_pos].lower()

    # Indicators that we're in a copyright/license section
    copyright_indicators = [
        'copyright',
        'license',
        'lgpl',
        'gpl',
        'part of odoo',  # Standard Odoo file header
        '# -*-',  # Python file header
    ]

    return any(indicator in context for indicator in copyright_indicators)


# ============================================
# CORE FUNCTIONS
# ============================================

class RebrandReport:
    """Track all changes made during rebranding."""

    def __init__(self):
        self.changes: List[Dict] = []
        self.skipped: List[Dict] = []
        self.errors: List[Dict] = []
        self.detections: List[Dict] = []

    def add_change(self, filepath: str, change_type: str, old_value: str, new_value: str):
        self.changes.append({
            'timestamp': datetime.now().isoformat(),
            'filepath': filepath,
            'type': change_type,
            'old_value': old_value[:100] + '...' if len(old_value) > 100 else old_value,
            'new_value': new_value[:100] + '...' if len(new_value) > 100 else new_value,
        })

    def add_skip(self, filepath: str, reason: str):
        self.skipped.append({
            'filepath': filepath,
            'reason': reason,
        })

    def add_error(self, filepath: str, error: str):
        self.errors.append({
            'filepath': filepath,
            'error': error,
        })

    def add_detection(self, filepath: str, line_num: int, pattern_type: str, match: str):
        self.detections.append({
            'filepath': filepath,
            'line': line_num,
            'type': pattern_type,
            'match': match[:200] if len(match) > 200 else match,
        })

    def summary(self) -> str:
        return f"""
Rebrand Report Summary
======================
Total changes: {len(self.changes)}
Files skipped: {len(self.skipped)}
Errors: {len(self.errors)}
Detections (remaining branding): {len(self.detections)}
"""

    def to_json(self, filepath: Path):
        with open(filepath, 'w') as f:
            json.dump({
                'summary': {
                    'total_changes': len(self.changes),
                    'files_skipped': len(self.skipped),
                    'errors': len(self.errors),
                    'detections': len(self.detections),
                },
                'changes': self.changes,
                'skipped': self.skipped,
                'errors': self.errors,
                'detections': self.detections,
            }, f, indent=2)

    def to_csv(self, filepath: Path):
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Type', 'Filepath', 'Details'])
            for change in self.changes:
                writer.writerow(['CHANGE', change['filepath'], f"{change['type']}: {change['old_value']} -> {change['new_value']}"])
            for skip in self.skipped:
                writer.writerow(['SKIP', skip['filepath'], skip['reason']])
            for error in self.errors:
                writer.writerow(['ERROR', error['filepath'], error['error']])
            for detection in self.detections:
                writer.writerow(['DETECTION', detection['filepath'], f"Line {detection['line']}: {detection['match']}"])


def replace_in_file(filepath: Path, replacements: Dict[str, str], report: RebrandReport, dry_run: bool = False) -> bool:
    """
    Replace strings in a file while preserving LGPL attribution.
    Returns True if any changes were made.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        report.add_error(str(filepath), f"Could not read file: {e}")
        return False

    original_content = content

    for old_str, new_str in replacements.items():
        if old_str in content:
            content = content.replace(old_str, new_str)
            report.add_change(str(filepath), 'string_replacement', old_str, new_str)

    if content != original_content:
        if not dry_run:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                report.add_error(str(filepath), f"Could not write file: {e}")
                return False
        return True

    return False


def replace_file(odoo_filepath: Path, asset_filepath: Path, report: RebrandReport, dry_run: bool = False) -> bool:
    """
    Replace an entire file (e.g., logo image).
    Returns True if replacement was made.
    """
    if not asset_filepath.exists():
        report.add_error(str(odoo_filepath), f"Asset file not found: {asset_filepath}")
        return False

    if not dry_run:
        try:
            shutil.copy2(asset_filepath, odoo_filepath)
            report.add_change(str(odoo_filepath), 'file_replacement', 'Original Odoo file', str(asset_filepath))
        except Exception as e:
            report.add_error(str(odoo_filepath), f"Could not replace file: {e}")
            return False
    else:
        report.add_change(str(odoo_filepath), 'file_replacement (dry-run)', 'Original Odoo file', str(asset_filepath))

    return True


def delete_file(filepath: Path, report: RebrandReport, dry_run: bool = False) -> bool:
    """Delete a file (e.g., enterprise_upgrade.jpg)."""
    if not filepath.exists():
        return False

    if not dry_run:
        try:
            filepath.unlink()
            report.add_change(str(filepath), 'file_deletion', str(filepath), 'DELETED')
        except Exception as e:
            report.add_error(str(filepath), f"Could not delete file: {e}")
            return False
    else:
        report.add_change(str(filepath), 'file_deletion (dry-run)', str(filepath), 'DELETED')

    return True


def update_release_py(odoo_path: Path, report: RebrandReport, dry_run: bool = False) -> bool:
    """
    Update odoo/release.py with Loomworks branding.
    This file contains the core product identity.
    """
    release_py = odoo_path / 'odoo' / 'release.py'
    if not release_py.exists():
        report.add_error(str(release_py), "release.py not found")
        return False

    return replace_in_file(release_py, RELEASE_PY_REPLACEMENTS, report, dry_run)


def update_webclient_templates(odoo_path: Path, report: RebrandReport, dry_run: bool = False) -> bool:
    """
    Update web/views/webclient_templates.xml with Loomworks branding.
    This file contains login page, layout, and brand promotion templates.
    """
    templates_xml = odoo_path / 'addons' / 'web' / 'views' / 'webclient_templates.xml'
    if not templates_xml.exists():
        report.add_error(str(templates_xml), "webclient_templates.xml not found")
        return False

    replacements = {
        **STRING_REPLACEMENTS,
        **UI_STRING_REPLACEMENTS,
        **SCSS_REPLACEMENTS,
        # Specific webclient replacements
        'odoo_logo_tiny.png': 'loomworks_logo_tiny.png',
        'odoo-icon-ios.png': 'loomworks_icon_ios.png',
        '/web/static/img/odoo': '/web/static/img/loomworks',
    }

    return replace_in_file(templates_xml, replacements, report, dry_run)


def update_email_templates(odoo_path: Path, report: RebrandReport, dry_run: bool = False) -> bool:
    """Update email template branding."""
    email_layouts = odoo_path / 'addons' / 'mail' / 'data' / 'mail_templates_email_layouts.xml'
    if email_layouts.exists():
        replacements = {
            **STRING_REPLACEMENTS,
            'Powered by <a target="_blank" href="https://www.odoo.com':
                'Powered by <a target="_blank" href="https://www.loomworks.solutions',
            '>Odoo</a>': '>Loomworks</a>',
        }
        return replace_in_file(email_layouts, replacements, report, dry_run)
    return False


def detect_remaining_branding(odoo_path: Path, report: RebrandReport):
    """
    Scan for any remaining Odoo branding that might have been missed.
    Used for verification after applying changes.
    """
    print("Scanning for remaining Odoo branding...")

    for root, dirs, files in os.walk(odoo_path):
        # Filter out skip directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRECTORIES]

        for filename in files:
            filepath = Path(root) / filename

            if should_skip_file(filepath):
                continue

            if not is_text_file(filepath):
                continue

            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    for line_num, line in enumerate(f, 1):
                        # Check for URL patterns
                        if 'odoo.com' in line.lower():
                            # Skip if in copyright section
                            if 'copyright' not in line.lower() and 'license' not in line.lower():
                                report.add_detection(str(filepath), line_num, 'URL', line.strip()[:200])

                        # Check for UI-visible Odoo text
                        for pattern, pattern_type in UI_VISIBLE_PATTERNS:
                            if re.search(pattern, line, re.IGNORECASE):
                                # Skip if in copyright/comment sections
                                if not (line.strip().startswith('#') or
                                       line.strip().startswith('//') or
                                       line.strip().startswith('/*') or
                                       'copyright' in line.lower()):
                                    report.add_detection(str(filepath), line_num, pattern_type, line.strip()[:200])
                                    break
            except Exception as e:
                pass  # Skip files that can't be read


def scrub_branding(odoo_path: Path, assets_path: Path, report: RebrandReport, dry_run: bool = False):
    """
    Main function to perform complete branding scrub.
    """
    print(f"Starting rebrand {'(DRY RUN)' if dry_run else ''}...")
    print(f"Odoo path: {odoo_path}")
    print(f"Assets path: {assets_path}")

    # 1. Update release.py (core identity)
    print("\n[1/6] Updating release.py...")
    update_release_py(odoo_path, report, dry_run)

    # 2. Update webclient templates
    print("[2/6] Updating webclient_templates.xml...")
    update_webclient_templates(odoo_path, report, dry_run)

    # 3. Update email templates
    print("[3/6] Updating email templates...")
    update_email_templates(odoo_path, report, dry_run)

    # 4. Replace logo files
    print("[4/6] Replacing logo files...")
    for odoo_file, asset_file in FILE_REPLACEMENTS.items():
        odoo_filepath = odoo_path / odoo_file
        asset_filepath = assets_path / Path(asset_file).name
        if odoo_filepath.exists():
            if asset_filepath.exists():
                replace_file(odoo_filepath, asset_filepath, report, dry_run)
            else:
                report.add_skip(str(odoo_filepath), f"Asset not found: {asset_filepath}")
        else:
            report.add_skip(str(odoo_filepath), "Original file not found")

    # 5. Delete files that should be removed
    print("[5/6] Removing unnecessary files...")
    for file_to_delete in FILES_TO_DELETE:
        filepath = odoo_path / file_to_delete
        if filepath.exists():
            delete_file(filepath, report, dry_run)

    # 6. Scan all text files for additional branding
    print("[6/6] Scanning all text files for Odoo branding...")
    text_file_count = 0
    modified_count = 0

    # Define files that need special URL/string replacement
    files_needing_url_replacement = [
        'addons/web/views/webclient_templates.xml',
        'addons/mail/data/mail_templates_email_layouts.xml',
        'addons/portal/data/mail_templates.xml',
        'addons/portal/views/portal_templates.xml',
        'addons/website/views/website_templates.xml',
        'odoo/addons/base/data/res_company_data.xml',
    ]

    for pattern in files_needing_url_replacement:
        filepath = odoo_path / pattern
        if filepath.exists():
            combined_replacements = {**STRING_REPLACEMENTS, **UI_STRING_REPLACEMENTS}
            if replace_in_file(filepath, combined_replacements, report, dry_run):
                modified_count += 1

    # Also scan and replace in manifest.webmanifest
    manifest_files = list(odoo_path.glob('**/manifest.webmanifest*'))
    for manifest in manifest_files:
        manifest_replacements = {
            '"Odoo"': '"Loomworks ERP"',
            "'Odoo'": "'Loomworks ERP'",
            '"name": "Odoo"': '"name": "Loomworks ERP"',
            '"short_name": "Odoo"': '"short_name": "Loomworks"',
            'odoo-icon': 'loomworks-icon',
        }
        if replace_in_file(manifest, manifest_replacements, report, dry_run):
            modified_count += 1

    print(f"\nScanned text files, modified {modified_count} files")


# ============================================
# CLI INTERFACE
# ============================================

def main():
    parser = argparse.ArgumentParser(
        description='Loomworks Rebrand Script - Replace Odoo branding with Loomworks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/rebrand.py --check      # Preview changes (dry run)
    python scripts/rebrand.py --apply      # Apply all changes
    python scripts/rebrand.py --verify     # Check for missed branding
    python scripts/rebrand.py --report     # Generate detailed report

LGPL Compliance:
    This script preserves Odoo S.A. attribution in copyright headers
    and license sections as required by LGPL v3.
        """
    )

    parser.add_argument('--check', action='store_true',
                        help='Dry run - report what would be changed')
    parser.add_argument('--apply', action='store_true',
                        help='Apply branding changes')
    parser.add_argument('--verify', action='store_true',
                        help='Verify no Odoo branding remains in UI')
    parser.add_argument('--report', action='store_true',
                        help='Generate detailed report (JSON and CSV)')
    parser.add_argument('--odoo-path', type=Path, default=None,
                        help='Path to Odoo directory (default: ./odoo)')
    parser.add_argument('--assets-path', type=Path, default=None,
                        help='Path to assets directory (default: ./assets)')

    args = parser.parse_args()

    # Determine paths
    odoo_path = args.odoo_path or get_odoo_path()
    assets_path = args.assets_path or get_assets_path()

    if not odoo_path.exists():
        print(f"ERROR: Odoo directory not found: {odoo_path}")
        print("Please clone Odoo first: git clone --branch 18.0 --depth 1 https://github.com/odoo/odoo.git odoo")
        sys.exit(1)

    report = RebrandReport()

    if args.check:
        print("=" * 60)
        print("REBRAND CHECK (Dry Run)")
        print("=" * 60)
        scrub_branding(odoo_path, assets_path, report, dry_run=True)
        detect_remaining_branding(odoo_path, report)
        print(report.summary())

    elif args.apply:
        print("=" * 60)
        print("APPLYING REBRAND")
        print("=" * 60)
        scrub_branding(odoo_path, assets_path, report, dry_run=False)
        print(report.summary())

        # Generate report automatically after apply
        report_dir = get_project_root() / 'reports'
        report_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report.to_json(report_dir / f'rebrand_report_{timestamp}.json')
        print(f"Report saved to: reports/rebrand_report_{timestamp}.json")

    elif args.verify:
        print("=" * 60)
        print("VERIFICATION - Checking for remaining Odoo branding")
        print("=" * 60)
        detect_remaining_branding(odoo_path, report)

        if report.detections:
            print(f"\nWARNING: Found {len(report.detections)} potential branding issues:")
            for detection in report.detections[:20]:  # Show first 20
                print(f"  {detection['filepath']}:{detection['line']} - {detection['type']}")
                print(f"    {detection['match'][:100]}")
            if len(report.detections) > 20:
                print(f"  ... and {len(report.detections) - 20} more")
        else:
            print("\nNo remaining Odoo branding detected in UI-visible areas.")

    elif args.report:
        print("=" * 60)
        print("GENERATING REPORT")
        print("=" * 60)
        scrub_branding(odoo_path, assets_path, report, dry_run=True)
        detect_remaining_branding(odoo_path, report)

        report_dir = get_project_root() / 'reports'
        report_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        report.to_json(report_dir / f'rebrand_report_{timestamp}.json')
        report.to_csv(report_dir / f'rebrand_report_{timestamp}.csv')

        print(report.summary())
        print(f"Reports saved to: reports/rebrand_report_{timestamp}.[json|csv]")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
