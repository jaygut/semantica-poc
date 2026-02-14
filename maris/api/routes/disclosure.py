"""TNFD LEAP disclosure endpoint - automated TNFD disclosure generation."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from maris.api.auth import rate_limit_default

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["disclosure"], dependencies=[Depends(rate_limit_default)])

# Lazy singleton
_generator = None
_scorer = None


def _get_generator():
    """Get or create the LEAPGenerator singleton."""
    global _generator
    if _generator is None:
        from maris.disclosure.leap_generator import LEAPGenerator
        _generator = LEAPGenerator()
    return _generator


def _get_scorer():
    """Get or create the AlignmentScorer singleton."""
    global _scorer
    if _scorer is None:
        from maris.disclosure.alignment_scorer import AlignmentScorer
        _scorer = AlignmentScorer()
    return _scorer


class DisclosureRequest(BaseModel):
    site_name: str = Field(..., min_length=1, max_length=200)
    format: str = Field(default="json", pattern=r"^(json|markdown|summary)$")


@router.post("/disclosure/tnfd-leap")
def generate_tnfd_leap(request: DisclosureRequest):
    """Generate a TNFD LEAP disclosure for an MPA site.

    Accepts a site name and output format (json, markdown, or summary).
    Returns the generated disclosure with alignment scoring.
    """
    generator = _get_generator()
    scorer = _get_scorer()

    try:
        disclosure = generator.generate(request.site_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("TNFD disclosure generation failed for %s", request.site_name)
        raise HTTPException(status_code=500, detail="Disclosure generation failed")

    alignment = scorer.score(disclosure)

    if request.format == "markdown":
        from maris.disclosure.renderers import render_markdown
        return {
            "site_name": request.site_name,
            "format": "markdown",
            "content": render_markdown(disclosure),
            "alignment": alignment.to_dict(),
        }
    elif request.format == "summary":
        from maris.disclosure.renderers import render_summary
        return {
            "site_name": request.site_name,
            "format": "summary",
            "content": render_summary(disclosure),
            "alignment": alignment.to_dict(),
        }
    else:
        return {
            "site_name": request.site_name,
            "format": "json",
            "disclosure": disclosure.model_dump(),
            "alignment": alignment.to_dict(),
        }
