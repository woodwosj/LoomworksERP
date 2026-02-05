# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
PDF Service for Signature Workflows

Handles PDF manipulation for signature embedding, field placement,
and document finalization.
"""

import base64
import hashlib
import logging
from io import BytesIO

_logger = logging.getLogger(__name__)

# Optional imports - graceful degradation
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    _logger.warning("PyMuPDF not installed. PDF signature operations will be limited.")


class PDFService:
    """Service for PDF manipulation in signature workflows."""

    def __init__(self, env):
        self.env = env

    def check_dependencies(self):
        """Check if required dependencies are available."""
        return {
            'pymupdf': HAS_PYMUPDF,
        }

    def get_document_hash(self, pdf_content):
        """Generate SHA-256 hash of PDF content.

        Args:
            pdf_content: bytes or base64 string

        Returns:
            str: Hex string of SHA-256 hash
        """
        if isinstance(pdf_content, str):
            pdf_content = base64.b64decode(pdf_content)
        return hashlib.sha256(pdf_content).hexdigest()

    def get_page_count(self, pdf_content):
        """Get number of pages in PDF.

        Args:
            pdf_content: bytes or base64 string

        Returns:
            int: Page count
        """
        if not HAS_PYMUPDF:
            _logger.warning("PyMuPDF required for page count")
            return 0

        if isinstance(pdf_content, str):
            pdf_content = base64.b64decode(pdf_content)

        doc = fitz.open(stream=pdf_content, filetype='pdf')
        count = len(doc)
        doc.close()
        return count

    def generate_preview(self, pdf_content, page=0, dpi=72):
        """Generate PNG preview of a PDF page.

        Args:
            pdf_content: bytes or base64 string
            page: Page number (0-indexed)
            dpi: Resolution for rendering

        Returns:
            str: Base64 encoded PNG
        """
        if not HAS_PYMUPDF:
            return False

        if isinstance(pdf_content, str):
            pdf_content = base64.b64decode(pdf_content)

        doc = fitz.open(stream=pdf_content, filetype='pdf')
        if page >= len(doc):
            doc.close()
            return False

        page_obj = doc[page]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page_obj.get_pixmap(matrix=mat)

        output = BytesIO()
        pix.save(output, 'png')
        doc.close()

        return base64.b64encode(output.getvalue()).decode()

    def prepare_document(self, template):
        """Prepare PDF with signature field placeholders.

        Args:
            template: sign.template record

        Returns:
            str: Base64 encoded PDF with placeholders
        """
        if not HAS_PYMUPDF:
            # Return original without modification
            return template.attachment_id.datas

        pdf_content = base64.b64decode(template.attachment_id.datas)
        doc = fitz.open(stream=pdf_content, filetype='pdf')

        # Add visual placeholders for each field
        for item in template.item_ids:
            if item.page > len(doc):
                continue

            page = doc[item.page - 1]  # 0-indexed
            rect = self._get_rect_from_position(page, item)

            # Draw placeholder rectangle with role color
            colors = [
                (0.8, 0.8, 0.8),   # Gray
                (0.8, 0.9, 1.0),   # Light blue
                (0.8, 1.0, 0.8),   # Light green
                (1.0, 0.9, 0.8),   # Light orange
                (1.0, 0.8, 0.9),   # Light pink
            ]
            color = colors[item.role_id.id % len(colors)] if item.role_id else colors[0]

            page.draw_rect(rect, color=color, fill=color, width=0.5)

            # Add placeholder text
            placeholder_text = item.placeholder or item.type_id.name or 'Field'
            fontsize = min(10, rect.height * 0.6)

            try:
                page.insert_text(
                    rect.tl + fitz.Point(5, fontsize + 2),
                    placeholder_text[:30],  # Truncate long text
                    fontsize=fontsize,
                    color=(0.4, 0.4, 0.4)
                )
            except Exception as e:
                _logger.debug("Could not insert placeholder text: %s", e)

        output = BytesIO()
        doc.save(output)
        doc.close()

        return base64.b64encode(output.getvalue()).decode()

    def embed_field(self, pdf_content, value, template_item):
        """Embed a field value into the PDF.

        Args:
            pdf_content: bytes or base64 string
            value: Field value (text or base64 signature image)
            template_item: sign.template.item record

        Returns:
            str: Base64 encoded modified PDF
        """
        if not HAS_PYMUPDF:
            return pdf_content if isinstance(pdf_content, str) else base64.b64encode(pdf_content).decode()

        if isinstance(pdf_content, str):
            pdf_content = base64.b64decode(pdf_content)

        doc = fitz.open(stream=pdf_content, filetype='pdf')

        if template_item.page > len(doc):
            doc.close()
            return base64.b64encode(pdf_content).decode()

        page = doc[template_item.page - 1]
        rect = self._get_rect_from_position(page, template_item)

        # Clear the placeholder area first
        page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

        # Embed based on field type
        if template_item.item_type in ('signature', 'initial'):
            # Embed signature image
            try:
                sig_image = base64.b64decode(value)
                page.insert_image(rect, stream=sig_image, keep_proportion=True)
            except Exception as e:
                _logger.error("Failed to embed signature: %s", e)
        else:
            # Embed text
            fontsize = min(12, rect.height * 0.7)
            try:
                page.insert_text(
                    rect.tl + fitz.Point(5, fontsize + 2),
                    str(value)[:200],  # Truncate very long text
                    fontsize=fontsize,
                    color=(0, 0, 0)
                )
            except Exception as e:
                _logger.error("Failed to embed text: %s", e)

        output = BytesIO()
        doc.save(output)
        doc.close()

        return base64.b64encode(output.getvalue()).decode()

    def finalize_document(self, request):
        """Finalize signed document with completion metadata.

        Args:
            request: sign.request record

        Returns:
            tuple: (final_pdf_bytes, document_hash)
        """
        pdf_content = base64.b64decode(request.attachment_id.datas)

        if HAS_PYMUPDF:
            doc = fitz.open(stream=pdf_content, filetype='pdf')

            # Add completion metadata (invisible to viewers but in PDF structure)
            metadata = doc.metadata or {}
            metadata['keywords'] = f"Signed via Loomworks Sign. Request: {request.name}"
            metadata['producer'] = "Loomworks ERP Sign Module"
            doc.set_metadata(metadata)

            # Add completion annotation on last page
            if len(doc) > 0:
                last_page = doc[-1]
                completion_text = (
                    f"Document signed electronically via Loomworks Sign.\n"
                    f"Request: {request.name}\n"
                    f"Completed: {request.completion_date or 'N/A'}\n"
                    f"Signers: {', '.join(s.partner_id.name for s in request.signer_ids)}"
                )

                # Add small text at bottom of page
                rect = fitz.Rect(50, last_page.rect.height - 100, last_page.rect.width - 50, last_page.rect.height - 20)
                try:
                    last_page.insert_textbox(
                        rect,
                        completion_text,
                        fontsize=8,
                        color=(0.5, 0.5, 0.5),
                        align=fitz.TEXT_ALIGN_LEFT
                    )
                except Exception as e:
                    _logger.debug("Could not add completion annotation: %s", e)

            output = BytesIO()
            doc.save(output)
            doc.close()
            pdf_content = output.getvalue()

        # Calculate final hash
        doc_hash = hashlib.sha256(pdf_content).hexdigest()

        return pdf_content, doc_hash

    def _get_rect_from_position(self, page, item):
        """Convert percentage-based position to PDF rectangle.

        Args:
            page: PyMuPDF page object
            item: sign.template.item record

        Returns:
            fitz.Rect: Rectangle for the field position
        """
        page_rect = page.rect

        x = page_rect.width * (item.pos_x / 100)
        y = page_rect.height * (item.pos_y / 100)
        w = page_rect.width * (item.width / 100)
        h = page_rect.height * (item.height / 100)

        return fitz.Rect(x, y, x + w, y + h)
