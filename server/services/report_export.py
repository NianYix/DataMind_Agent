from __future__ import annotations

import logging
from io import BytesIO

import markdown as md
from xhtml2pdf import pisa

logger = logging.getLogger("datamind.report")


def markdown_to_pdf(markdown_text: str) -> bytes:
    html_body = md.markdown(markdown_text or "", extensions=["tables", "fenced_code"])
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 12px; color: #111; }}
h1,h2,h3 {{ color: #0f766e; }}
pre,code {{ font-size: 10px; }}
</style></head><body>{html_body}</body></html>"""
    out = BytesIO()
    result = pisa.CreatePDF(html, dest=out, encoding="utf-8")
    if result.err:
        logger.error("PDF generation failed")
        raise RuntimeError("Failed to generate PDF")
    return out.getvalue()
