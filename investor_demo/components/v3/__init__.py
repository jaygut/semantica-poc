"""MARIS v3 Intelligence Platform - component package.

Each module exposes a single render function consumed by streamlit_app_v3.py.
"""

from investor_demo.components.v3.shared import (  # noqa: F401
    COLORS,
    check_services,
    confidence_badge,
    fmt_pct,
    fmt_usd,
    get_case_study_path,
    get_site_data,
    render_service_health,
    tier_badge,
)
