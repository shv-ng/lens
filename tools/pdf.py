import logging

import pymupdf

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path):
    try:
        with pymupdf.open(pdf_path) as doc:
            text = "\n\n".join([page.get_text() for page in doc])
            if text:
                return text

            text = "\n\n".join(
                page.get_textpage_ocr(language="eng").extractText() for page in doc
            )
            if text:
                return text

        return ""
    except Exception as e:
        logger.exception(f"Error extracting text from PDF: {pdf_path}, error: {e}")
        return ""
