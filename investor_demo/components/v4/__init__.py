"""Nereus v4 Natural Capital Intelligence - component package.

Registry-driven, multi-site dashboard. Each module exposes a single render
function consumed by streamlit_app_v4.py.  All site lists are discovered
dynamically from ``examples/*_case_study.json`` - no hardcoded site names.
"""

from investor_demo.components.v4.shared import (  # noqa: F401
    COLORS,
    check_services,
    confidence_badge,
    fmt_pct,
    fmt_usd,
    get_all_sites,
    get_site_data,
    get_site_names,
    get_site_summary,
    get_site_tier,
    is_feature_available,
    render_service_health,
    tier_badge,
)
from investor_demo.components.v4.site_intelligence import (  # noqa: F401
    render_site_intelligence,
)
