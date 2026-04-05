"""PDF proof bundle export — generates a formatted PDF document from a proof bundle.

Compliance teams need PDF documents with headers, dates, and signature blocks.
"My legal counsel doesn't accept JSON files." — product_manager_dan, feedback round 4.

This module generates PDFs using only Python's standard library (no reportlab,
no weasyprint, no external dependencies). It writes raw PDF 1.4 commands to
produce a clean, professional document suitable for compliance evidence.

The PDF contains:
- Document header with Glass branding and generation timestamp
- Self-attestation disclosure (what the seal proves and does not prove)
- Query and response text
- Claims table with status and evidence
- Complete audit trail with timing and data flow
- Provenance seal with verification instructions
- Signature block for reviewer attestation
- EU AI Act Article 12 reference note
"""

import io
import textwrap
from datetime import datetime, timezone


def _pdf_escape(text: str) -> str:
    """Escape special PDF string characters."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_text(text: str, width: int = 90) -> list[str]:
    """Wrap text to fit within PDF page width."""
    lines = []
    for paragraph in text.split("\n"):
        if paragraph.strip() == "":
            lines.append("")
        else:
            wrapped = textwrap.wrap(paragraph, width=width)
            lines.extend(wrapped if wrapped else [""])
    return lines


class SimplePDFWriter:
    """Minimal PDF 1.4 writer — no external dependencies.

    Produces valid PDF documents with text content, headers, and page breaks.
    Uses Helvetica (built-in PDF font) for broad compatibility.
    """

    def __init__(self):
        self.objects: list[bytes] = []
        self.pages: list[int] = []
        self.page_contents: list[list[str]] = []
        self._current_page: list[str] = []
        self._y = 750  # current y position on page
        self._page_bottom = 60
        self._page_top = 750
        self._left_margin = 60
        self._line_height = 14
        self._font_size = 10

    def _new_page(self):
        if self._current_page:
            self.page_contents.append(self._current_page)
        self._current_page = []
        self._y = self._page_top

    def _check_page_break(self, lines_needed: int = 1):
        space_needed = lines_needed * self._line_height
        if self._y - space_needed < self._page_bottom:
            self._new_page()

    def add_title(self, text: str):
        self._check_page_break(3)
        self._current_page.append(f"BT /F1 18 Tf {self._left_margin} {self._y} Td ({_pdf_escape(text)}) Tj ET")
        self._y -= 28

    def add_heading(self, text: str):
        self._check_page_break(3)
        self._y -= 8  # extra spacing before heading
        self._current_page.append(f"BT /F1 12 Tf {self._left_margin} {self._y} Td ({_pdf_escape(text)}) Tj ET")
        self._y -= 20

    def add_text(self, text: str, indent: int = 0, font_size: int = 10):
        lines = _wrap_text(text, width=85 - indent // 5)
        for line in lines:
            self._check_page_break()
            x = self._left_margin + indent
            self._current_page.append(f"BT /F2 {font_size} Tf {x} {self._y} Td ({_pdf_escape(line)}) Tj ET")
            self._y -= self._line_height

    def add_mono(self, text: str, indent: int = 0, font_size: int = 8):
        lines = _wrap_text(text, width=95 - indent // 4)
        for line in lines:
            self._check_page_break()
            x = self._left_margin + indent
            self._current_page.append(f"BT /F3 {font_size} Tf {x} {self._y} Td ({_pdf_escape(line)}) Tj ET")
            self._y -= self._line_height - 2

    def add_separator(self):
        self._check_page_break(2)
        self._y -= 4
        y = self._y
        self._current_page.append(f"0.7 0.7 0.7 RG 0.5 w {self._left_margin} {y} m 535 {y} l S")
        self._y -= 12

    def add_blank_line(self):
        self._y -= self._line_height

    def build(self) -> bytes:
        """Compile the PDF and return the bytes."""
        # Finalize last page
        if self._current_page:
            self.page_contents.append(self._current_page)

        buf = io.BytesIO()
        offsets: list[int] = []

        # Header
        buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        # Object 1: Catalog
        offsets.append(buf.tell())
        buf.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # Object 2: Pages (placeholder — we'll know page count after building)
        pages_offset = buf.tell()
        offsets.append(pages_offset)
        # We'll fill this after building page objects

        # Fonts: 3=Helvetica-Bold, 4=Helvetica, 5=Courier
        offsets.append(buf.tell())
        buf.write(b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")

        offsets.append(buf.tell())
        buf.write(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

        offsets.append(buf.tell())
        buf.write(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")

        # Build page objects starting at object 6
        next_obj = 6
        page_obj_ids = []

        for page_lines in self.page_contents:
            content_stream = "\n".join(page_lines)
            content_bytes = content_stream.encode("latin-1", errors="replace")

            # Content stream object
            content_obj_id = next_obj
            offsets.append(buf.tell())
            buf.write(f"{content_obj_id} 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode())
            buf.write(content_bytes)
            buf.write(b"\nendstream\nendobj\n")
            next_obj += 1

            # Page object
            page_obj_id = next_obj
            page_obj_ids.append(page_obj_id)
            offsets.append(buf.tell())
            buf.write(
                f"{page_obj_id} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 595 842] "
                f"/Contents {content_obj_id} 0 R "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> "
                f">>\nendobj\n".encode()
            )
            next_obj += 1

        # Now go back and write the Pages object
        kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
        pages_content = f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(page_obj_ids)} >>\nendobj\n"

        # We need to rebuild the file because the Pages object has a fixed offset
        # Simpler approach: rebuild from scratch with known sizes
        buf2 = io.BytesIO()
        offsets2: list[int] = []

        buf2.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        # Obj 1: Catalog
        offsets2.append(buf2.tell())
        buf2.write(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # Obj 2: Pages
        offsets2.append(buf2.tell())
        buf2.write(pages_content.encode())

        # Obj 3-5: Fonts
        offsets2.append(buf2.tell())
        buf2.write(b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")
        offsets2.append(buf2.tell())
        buf2.write(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
        offsets2.append(buf2.tell())
        buf2.write(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")

        obj_num = 6
        for page_lines in self.page_contents:
            content_stream = "\n".join(page_lines)
            content_bytes = content_stream.encode("latin-1", errors="replace")

            # Content stream
            offsets2.append(buf2.tell())
            buf2.write(f"{obj_num} 0 obj\n<< /Length {len(content_bytes)} >>\nstream\n".encode())
            buf2.write(content_bytes)
            buf2.write(b"\nendstream\nendobj\n")
            content_id = obj_num
            obj_num += 1

            # Page
            offsets2.append(buf2.tell())
            buf2.write(
                f"{obj_num} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 595 842] "
                f"/Contents {content_id} 0 R "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> "
                f">>\nendobj\n".encode()
            )
            obj_num += 1

        # Cross-reference table
        xref_offset = buf2.tell()
        buf2.write(b"xref\n")
        buf2.write(f"0 {len(offsets2) + 1}\n".encode())
        buf2.write(b"0000000000 65535 f \n")
        for off in offsets2:
            buf2.write(f"{off:010d} 00000 n \n".encode())

        # Trailer
        buf2.write(
            f"trailer\n<< /Size {len(offsets2) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n".encode()
        )

        return buf2.getvalue()


def generate_proof_pdf(bundle: dict) -> bytes:
    """Generate a formatted PDF document from a proof bundle dict.

    Returns raw PDF bytes ready to be served as application/pdf.
    """
    pdf = SimplePDFWriter()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    response = bundle.get("response", {})
    seal_status = bundle.get("seal_status", {})
    seal_verification = bundle.get("seal_verification", {})

    # Title page header
    pdf.add_title("Glass Proof Bundle")
    pdf.add_text(f"Generated: {now}", font_size=9)
    pdf.add_text(f"Glass Version: {bundle.get('glass_version', 'unknown')}", font_size=9)
    pdf.add_text(f"Bundle Version: {bundle.get('proof_bundle_version', 'unknown')}", font_size=9)
    pdf.add_text(f"Response ID: {response.get('id', 'unknown')}", font_size=9)
    pdf.add_text(f"Response Timestamp: {response.get('timestamp', 'unknown')}", font_size=9)
    pdf.add_text(f"Backend: {response.get('backend', 'unknown')}", font_size=9)
    pdf.add_separator()

    # Self-attestation disclosure — the most important section
    pdf.add_heading("SELF-ATTESTATION DISCLOSURE")
    disclosure = bundle.get("self_attestation_disclosure", "")
    pdf.add_text(disclosure)
    pdf.add_blank_line()

    # EU AI Act reference
    pdf.add_heading("Regulatory Reference")
    pdf.add_text(
        "This document may serve as evidence under EU AI Act Article 12 (Record-keeping), "
        "which requires providers and deployers of high-risk AI systems to maintain logs that "
        "enable monitoring of system operation and traceability of outputs. Glass audit trails "
        "record every LLM invocation, data flow, and verification step in a tamper-evident "
        "hash chain, supporting the Article 12 requirement for automatic recording of events "
        "relevant to the identification of risks."
    )
    pdf.add_text(
        "Control references: SOC 2 CC7.2 (System Operations Monitoring), "
        "ISO 27001 A.12.4.1 (Event Logging), HIPAA 45 CFR 164.312(b) (Audit Controls).",
        font_size=9,
    )
    pdf.add_separator()

    # Query
    pdf.add_heading("Query")
    pdf.add_text(response.get("query", "(no query)"))
    pdf.add_separator()

    # Response
    pdf.add_heading("Response")
    pdf.add_text(response.get("raw_response", "(no response)"))
    pdf.add_separator()

    # Claims
    claims = response.get("claims", [])
    pdf.add_heading(f"Claims ({len(claims)})")
    if not claims:
        pdf.add_text("No factual claims extracted.")
    for i, claim in enumerate(claims):
        status = claim.get("status", "unverifiable").upper()
        text = claim.get("text", "")
        evidence = claim.get("evidence", "")
        pdf.add_text(f"[{status}] {text}")
        if evidence:
            pdf.add_text(f"  Evidence: {evidence}", indent=20, font_size=9)
        pdf.add_blank_line()
    pdf.add_separator()

    # Premise flags
    premise_flags = response.get("premise_flags", [])
    if premise_flags:
        pdf.add_heading("Premise Issues Detected")
        for flag in premise_flags:
            pdf.add_text(f"  - {flag}")
        pdf.add_separator()

    # Audit trail
    trail = bundle.get("audit_trail", [])
    pdf.add_heading(f"Audit Trail ({len(trail)} events)")
    for i, event in enumerate(trail):
        desc = event.get("description", "")
        dest = event.get("destination", "")
        latency = event.get("latency_ms", 0)
        sent = event.get("bytes_sent", 0)
        received = event.get("bytes_received", 0)
        ts = event.get("timestamp", "")
        chain = event.get("chain_hash", "")

        pdf.add_text(f"Event {i + 1}: {desc}")
        pdf.add_mono(f"  Time: {ts}  Latency: {latency}ms  Dest: {dest}", indent=10)
        pdf.add_mono(f"  Sent: {sent}B  Received: {received}B  Chain: {chain[:32]}...", indent=10)
        pdf.add_blank_line()
    pdf.add_separator()

    # Provenance seal
    pdf.add_heading("Provenance Seal")
    seal = bundle.get("provenance_seal", "")
    pdf.add_text(f"Seal value: {seal}")
    pdf.add_text(f"Algorithm: {seal_verification.get('algorithm', 'SHA-256 hash chain')}")
    pdf.add_text(f"Chain length: {seal_verification.get('chain_length', len(trail))} events")
    pdf.add_text(f"Genesis value: {seal_verification.get('genesis_value', 'genesis')}")
    pdf.add_blank_line()

    # Seal verification result
    chain_ok = seal_status.get("chain_intact", False)
    seal_msg = seal_status.get("message", "")
    events_checked = seal_status.get("events_checked", 0)
    status_str = "INTACT" if chain_ok else "BROKEN"
    pdf.add_text(f"Verification result: {status_str} ({events_checked} events checked)")
    if seal_msg:
        pdf.add_text(f"Detail: {seal_msg}", font_size=9)
    pdf.add_separator()

    # Verification instructions
    pdf.add_heading("Verification Instructions")
    instructions = bundle.get("verification_instructions", "")
    pdf.add_text(instructions, font_size=9)
    pdf.add_separator()

    # Signature block
    pdf.add_heading("Reviewer Attestation")
    pdf.add_blank_line()
    pdf.add_text("I have reviewed this proof bundle and the associated audit trail.")
    pdf.add_blank_line()
    pdf.add_blank_line()
    pdf.add_text("Reviewer Name: ________________________________________")
    pdf.add_blank_line()
    pdf.add_text("Reviewer Title: ________________________________________")
    pdf.add_blank_line()
    pdf.add_text("Date: ________________________________________")
    pdf.add_blank_line()
    pdf.add_text("Signature: ________________________________________")
    pdf.add_blank_line()
    pdf.add_blank_line()
    pdf.add_text(
        "Note: This PDF was generated from a Glass proof bundle. The canonical, "
        "machine-verifiable version is the JSON bundle. This PDF is a human-readable "
        "rendering for documentation and compliance purposes.",
        font_size=8,
    )

    return pdf.build()
