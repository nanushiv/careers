"""
Resume Rewriter — AI rewrites resume sections based on analysis gaps.
Generates a clean ATS-safe DOCX and PDF for download. Pro-only feature.
"""
import io
import json
import logging
import uuid
from typing import Optional

from docx import Document
from docx.shared import Pt, RGBColor

from app.ai.llm_client import llm_client
from app.ai.prompt_templates import get_prompt
from app.ai.cost_governor import cost_governor

logger = logging.getLogger(__name__)


class RewriteResult:
    def __init__(self):
        self.docx_url: str = ""
        self.pdf_url: str = ""
        self.sections_changed: list = []
        self.changes_summary: str = ""
        self.model_used: str = ""
        self.tokens_used: int = 0
        self.cost_usd: float = 0.0
        self.improved_text: str = ""   # flat text of improved resume for ATS re-scoring
        self.projected_ats_score: float = 0.0
        self.error: Optional[str] = None


class ResumeRewriter:

    async def rewrite(
        self,
        resume: dict,
        analyses: list,
        user_id: str,
    ) -> RewriteResult:
        result = RewriteResult()

        # Check budget
        budget_check = await cost_governor.can_use_llm(user_id, "pro", "rewrite")
        if not budget_check.get("allowed", True):
            result.error = "AI budget exhausted for this month"
            return result

        # Build context from existing analyses
        gaps_context = self._build_gaps_context(analyses)
        recommended_changes = self._build_recommended_changes(analyses)
        missing_keywords = self._build_missing_keywords(analyses)

        # Use raw_text if structured_data is sparse (< 3 sections)
        structured = resume.get("structured_data") or {}
        raw_text = resume.get("raw_text", "")
        if len(structured) < 3 and raw_text:
            original_sections_text = raw_text
        else:
            original_sections_text = json.dumps(structured, indent=2)

        # Build prompt
        prompt_template = get_prompt("rewrite")
        prompt = prompt_template.format(
            original_sections=original_sections_text,
            missing_keywords=missing_keywords,
            gaps_context=gaps_context,
            recommended_changes=recommended_changes,
        )

        # LLM call — 8192 tokens needed: full resume sections can be 4-6k tokens
        try:
            response = await llm_client.complete(
                prompt=prompt,
                model="gemini-2.5-flash-lite",
                max_tokens=8192,
                temperature=0.4,
            )
        except Exception as e:
            logger.error(f"LLM rewrite API call failed: {e}")
            result.error = f"AI rewrite failed: {str(e)}"
            return result

        try:
            rewritten = response.as_json()
        except Exception as json_err:
            raw_preview = (response.text or "")[:800]
            logger.error(f"Rewrite JSON parse failed: {json_err} | Raw response: {raw_preview}")
            result.error = f"AI response parse failed: {str(json_err)}"
            return result

        result.model_used = response.model
        result.tokens_used = response.tokens
        result.cost_usd = response.cost_usd
        result.sections_changed = rewritten.get("sections_changed", [])
        result.changes_summary = rewritten.get("changes_summary", "")

        # Record spend
        try:
            await cost_governor.record_spend(user_id, response.cost_usd)
        except Exception as e:
            logger.warning(f"Cost recording failed (non-fatal): {e}")

        # Merge: start from structured data (or empty), overlay LLM rewrites
        # LLM output takes priority — it's the optimized version
        merged = {}
        # First put structured data as fallback
        if isinstance(structured, dict):
            merged.update(structured)
        # Then overlay ALL LLM rewrites (skip metadata keys)
        skip_keys = {"sections_changed", "changes_summary"}
        for key, val in rewritten.items():
            if key in skip_keys:
                continue
            if val and isinstance(val, str) and val.strip():
                merged[key] = val

        raw_text = resume.get("raw_text", "")

        # Build improved_text (flat) for projected ATS scoring
        result.improved_text = "\n".join(
            str(v) for k, v in merged.items()
            if k not in ("sections_changed", "changes_summary") and v and isinstance(v, str)
        )
        # Projected ATS: check how many previously-missing keywords now appear
        result.projected_ats_score = self._compute_projected_score(
            result.improved_text, analyses
        )

        # Build DOCX
        try:
            docx_bytes = self._build_docx(merged, raw_text)
        except Exception as e:
            logger.error(f"DOCX build failed: {e}")
            result.error = f"Document generation failed: {str(e)}"
            return result

        # Build PDF
        try:
            pdf_bytes = self._build_pdf(merged, raw_text)
        except Exception as e:
            logger.warning(f"PDF build failed (non-fatal): {e}")
            pdf_bytes = None

        # Upload to R2
        try:
            from app.api.v1.resumes import upload_to_r2
            file_id = uuid.uuid4()
            result.docx_url = await upload_to_r2(
                docx_bytes,
                f"{user_id}/improved_{file_id}.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            if pdf_bytes:
                result.pdf_url = await upload_to_r2(
                    pdf_bytes,
                    f"{user_id}/improved_{file_id}.pdf",
                    "application/pdf",
                )
        except Exception as e:
            logger.error(f"R2 upload failed: {e}")
            result.error = f"File upload failed: {str(e)}"
            return result

        return result

    def _compute_projected_score(self, improved_text: str, analyses: list) -> float:
        """Estimate new ATS score by checking keyword coverage in the improved resume text."""
        from app.ai.rule_engine import rule_engine
        text_lower = improved_text.lower()

        for analysis in analyses:
            if analysis.get("analysis_type") == "ats":
                kw = analysis.get("keyword_analysis") or {}
                required_found_before = kw.get("required_found") or []
                required_missing_before = kw.get("required_missing") or []
                preferred_found_before = kw.get("preferred_found") or []
                preferred_missing_before = kw.get("preferred_missing") or []

                all_required = required_found_before + required_missing_before
                all_preferred = preferred_found_before + preferred_missing_before

                if not all_required:
                    break

                now_required = [kw for kw in all_required if kw.lower() in text_lower]
                now_preferred = [kw for kw in all_preferred if kw.lower() in text_lower]

                req_pct = len(now_required) / len(all_required)
                pref_pct = len(now_preferred) / max(len(all_preferred), 1)
                keyword_score = round((req_pct * 85) + (pref_pct * 15), 1)

                # Format score from original (unchanged), semantic score assumed 70
                original_format = analysis.get("format_score") or 75.0
                overall = round(
                    keyword_score * 0.40
                    + 70.0 * 0.25  # semantic (estimated)
                    + original_format * 0.20
                    + 70.0 * 0.15,  # experience (estimated)
                    1
                )
                return min(98.0, overall)

        return 0.0

    def _build_missing_keywords(self, analyses: list) -> str:
        for analysis in analyses:
            if analysis.get("analysis_type") == "ats":
                kw = analysis.get("keyword_analysis") or {}
                required_missing = kw.get("required_missing") or []
                preferred_missing = kw.get("preferred_missing") or []
                lines = []
                if required_missing:
                    lines.append("REQUIRED (must add): " + ", ".join(required_missing))
                if preferred_missing:
                    lines.append("PREFERRED (add if natural): " + ", ".join(preferred_missing))
                if lines:
                    return "\n".join(lines)
        return "No specific keywords identified — improve overall quality."

    def _build_gaps_context(self, analyses: list) -> str:
        lines = []
        for analysis in analyses:
            atype = analysis.get("analysis_type", "")
            if atype == "ats":
                gaps = analysis.get("gaps") or []
                improvements = analysis.get("improvements") or []
                quick_fixes = analysis.get("quick_fixes") or []
                if gaps:
                    lines.append("ATS GAPS:")
                    for g in gaps[:8]:
                        sev = g.get("severity", "")
                        desc = g.get("description", g.get("keyword", ""))
                        fix = g.get("fix", "")
                        lines.append(f"  [{sev.upper()}] {desc}" + (f" → Fix: {fix}" if fix else ""))
                if quick_fixes:
                    lines.append("QUICK FIXES:")
                    for qf in quick_fixes[:5]:
                        lines.append(f"  • {qf.get('action', '')} (impact: {qf.get('impact', '')})")
                if improvements:
                    lines.append("IMPROVEMENTS:")
                    for imp in improvements[:5]:
                        lines.append(f"  • {imp.get('action', '')} in {imp.get('section', 'resume')}")
        return "\n".join(lines) if lines else "No specific gaps identified — general quality improvement."

    def _build_recommended_changes(self, analyses: list) -> str:
        lines = []
        for analysis in analyses:
            if analysis.get("analysis_type") == "recruiter":
                signals = analysis.get("recruiter_signals") or {}
                changes = signals.get("recommended_changes") or signals.get("recommended_resume_changes") or []
                for c in changes[:5]:
                    before = c.get("before_example", "")
                    after = c.get("after_example", "")
                    change = c.get("change", "")
                    if before and after:
                        lines.append(f"• {change}\n  BEFORE: {before}\n  AFTER: {after}")
                    elif change:
                        lines.append(f"• {change}")
        return "\n".join(lines) if lines else "No specific before/after examples available."

    def _build_docx(self, sections: dict, raw_text: str) -> bytes:
        doc = Document()
        for section in doc.sections:
            section.top_margin = Pt(72)
            section.bottom_margin = Pt(72)
            section.left_margin = Pt(72)
            section.right_margin = Pt(72)

        if not sections or len(sections) < 2:
            for line in raw_text.split("\n"):
                line = line.strip()
                if line:
                    doc.add_paragraph(line).paragraph_format.space_after = Pt(2)
        else:
            order = ["header", "summary", "core_competencies", "experience", "education",
                     "skills", "projects", "certifications", "awards"]
            written = set()
            for key in order:
                if key in sections and sections[key]:
                    if key == "header":
                        # Header: no heading line, just render the text directly
                        self._docx_body(doc, sections[key])
                    else:
                        self._docx_heading(doc, key.replace("_", " ").upper())
                        self._docx_body(doc, sections[key])
                    written.add(key)
            for key, val in sections.items():
                if key not in written and val:
                    self._docx_heading(doc, key.replace("_", " ").upper())
                    self._docx_body(doc, val)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    def _docx_heading(self, doc: Document, title: str):
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        p = doc.add_paragraph()
        run = p.add_run(title)
        run.bold = True
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0x1a, 0x1a, 0x2e)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "4")
        bottom.set(qn("w:space"), "1")
        bottom.set(qn("w:color"), "AAAAAA")
        pBdr.append(bottom)
        pPr.append(pBdr)

    def _docx_body(self, doc: Document, text: str):
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            p = doc.add_paragraph(line)
            p.paragraph_format.space_after = Pt(1)
            if p.runs:
                p.runs[0].font.size = Pt(10)

    def _build_pdf(self, sections: dict, raw_text: str) -> bytes:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.enums import TA_LEFT

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=inch,
            rightMargin=inch,
            topMargin=inch,
            bottomMargin=inch,
        )

        styles = getSampleStyleSheet()
        heading_style = ParagraphStyle(
            "Heading",
            parent=styles["Normal"],
            fontSize=11,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=4,
            spaceBefore=12,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            fontName="Helvetica",
            leading=14,
            spaceAfter=2,
        )

        story = []
        order = ["header", "summary", "core_competencies", "experience", "education",
                 "skills", "projects", "certifications", "awards"]
        written = set()

        def add_section(title: str, text: str):
            story.append(Paragraph(title.upper(), heading_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#AAAAAA"), spaceAfter=4))
            for line in text.split("\n"):
                line = line.strip()
                if line:
                    line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(line, body_style))
            story.append(Spacer(1, 6))

        if not sections or len(sections) < 2:
            for line in raw_text.split("\n"):
                line = line.strip()
                if line:
                    line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    story.append(Paragraph(line, body_style))
        else:
            for key in order:
                if key in sections and sections[key]:
                    if key == "header":
                        for line in sections[key].split("\n"):
                            line = line.strip()
                            if line:
                                line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                story.append(Paragraph(line, body_style))
                        story.append(Spacer(1, 4))
                    else:
                        add_section(key.replace("_", " "), sections[key])
                    written.add(key)
            for key, val in sections.items():
                if key not in written and val:
                    add_section(key.replace("_", " "), val)

        doc.build(story)
        return buf.getvalue()


resume_rewriter = ResumeRewriter()
