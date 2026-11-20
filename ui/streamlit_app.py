"""Streamlit dashboard for researching and fact-checking topics."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
import streamlit as st

from core.documents import extract_pdf_text
from core.reporting import report_filename, report_to_markdown
from core.trust import confidence_assessment, source_diversity
from ui.authentication import authenticate_user, sign_out

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "mars_logo.png"

st.set_page_config(
    page_title="M.A.R.S. | Multi-Agent Research System",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_API_URL = os.getenv("FACT_CHECK_API_URL", "https://fact-checker-agent.onrender.com").rstrip("/")
STEPS = {
    "planner": "Planning research",
    "searcher": "Searching trusted sources",
    "conflict": "Comparing claims",
    "critic": "Reviewing evidence",
    "synthesizer": "Writing your report",
    "fact_checker": "Verifying key claims",
}

for key, default in {
    "api_url": DEFAULT_API_URL,
    "reports": [],
    "dark_mode": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

theme = {
    "ink": "#eef3ff" if st.session_state.dark_mode else "#122347",
    "muted": "#a6b4cf" if st.session_state.dark_mode else "#6b7896",
    "blue": "#8db4ff" if st.session_state.dark_mode else "#2463eb",
    "line": "#2b3a56" if st.session_state.dark_mode else "#e3eaf8",
    "panel": "#151f32" if st.session_state.dark_mode else "#ffffff",
    "canvas": "#0b1322" if st.session_state.dark_mode else "#f5f7fc",
    "canvas_glow": "rgba(46,92,170,.15)" if st.session_state.dark_mode else "rgba(226,235,255,.72)",
    "sidebar_start": "#080f1c" if st.session_state.dark_mode else "#ffffff",
    "sidebar_end": "#0b1424" if st.session_state.dark_mode else "#f0f4fb",
    "sidebar_text": "#d7e2fb" if st.session_state.dark_mode else "#1b2b4a",
    "sidebar_muted": "#90a4ca" if st.session_state.dark_mode else "#70809d",
    "sidebar_border": "rgba(255,255,255,.07)" if st.session_state.dark_mode else "#dfe6f2",
    "sidebar_hover": "rgba(255,255,255,.08)" if st.session_state.dark_mode else "rgba(36,99,235,.08)",
    "sidebar_brand": "#ffffff" if st.session_state.dark_mode else "#142849",
    "sidebar_tagline": "#9db1d7" if st.session_state.dark_mode else "#70809d",
    "sidebar_status_bg": "rgba(255,255,255,.07)" if st.session_state.dark_mode else "#e8eef8",
    "sidebar_status_text": "#c9d7f0" if st.session_state.dark_mode else "#42536f",
    "panel_tint": "rgba(21,31,50,.96)" if st.session_state.dark_mode else "rgba(255,255,255,.94)",
    "field": "#101a2b" if st.session_state.dark_mode else "#ffffff",
    "placeholder": "#91a0ba" if st.session_state.dark_mode else "#8491ad",
    "shadow": "rgba(0,0,0,.24)" if st.session_state.dark_mode else "rgba(38,76,151,.08)",
    "step_blue_fg": "#9cc0ff" if st.session_state.dark_mode else "#1d63e9",
    "step_blue_bg": "#1b3153" if st.session_state.dark_mode else "#e0ebff",
    "step_green_fg": "#66ddb1" if st.session_state.dark_mode else "#07966a",
    "step_green_bg": "#153b35" if st.session_state.dark_mode else "#dcf8ed",
    "step_purple_fg": "#c0a3ff" if st.session_state.dark_mode else "#7444df",
    "step_purple_bg": "#30264d" if st.session_state.dark_mode else "#eee5ff",
    "step_orange_fg": "#ffbd83" if st.session_state.dark_mode else "#ec741b",
    "step_orange_bg": "#482f28" if st.session_state.dark_mode else "#fff0e2",
    "metric_blue_fg": "#9cc0ff" if st.session_state.dark_mode else "#1d63e9",
    "metric_blue_bg": "#1b3153" if st.session_state.dark_mode else "#e5eeff",
    "metric_green_fg": "#66ddb1" if st.session_state.dark_mode else "#0c9d70",
    "metric_green_bg": "#153b35" if st.session_state.dark_mode else "#e0f8ef",
    "metric_orange_fg": "#ffbd83" if st.session_state.dark_mode else "#e86b25",
    "metric_orange_bg": "#482f28" if st.session_state.dark_mode else "#fff0e4",
    "expander": "rgba(21,31,50,.78)" if st.session_state.dark_mode else "rgba(255,255,255,.75)",
}

st.markdown(
    """
    <style>
    :root {
        --ink: __INK__;
        --muted: __MUTED__;
        --blue: __BLUE__;
        --line: __LINE__;
        --panel: __PANEL__;
        --canvas: __CANVAS__;
        --canvas-glow: __CANVAS_GLOW__;
        --panel-tint: __PANEL_TINT__;
        --field: __FIELD__;
        --placeholder: __PLACEHOLDER__;
        --shadow: __SHADOW__;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', 'Segoe UI', sans-serif;
        color: var(--ink);
    }
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse at 75% 0%, var(--canvas-glow), transparent 35%),
            var(--canvas);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
        background: linear-gradient(165deg, __SIDEBAR_START__ 0%, __SIDEBAR_END__ 100%);
        border-right: 1px solid __SIDEBAR_BORDER__;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.4rem; }
    [data-testid="stImage"] img {
        display: block;
        margin: 0 auto;
        object-fit: contain;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        color: __SIDEBAR_TEXT__;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] > label {
        color: __SIDEBAR_MUTED__ !important;
        font-size: .72rem;
        font-weight: 700;
        letter-spacing: .12em;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] [data-testid="stToggle"] label {
        color: __SIDEBAR_TEXT__ !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: .35rem;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label {
        padding: .62rem .72rem;
        border-radius: 12px;
        transition: background .15s ease;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
        background: __SIDEBAR_HOVER__;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(100deg, #1760f5, #3478ff);
        color: #fff !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label p {
        font-weight: 600;
    }
    [data-testid="stMain"] .block-container {
        width: 100%;
        max-width: 1180px;
        margin-left: auto;
        margin-right: auto;
        padding: 2.5rem clamp(1rem, 3.5vw, 3.6rem) 4rem;
    }
    [data-testid="stMain"] .block-container:has([data-testid="stTabs"]),
    [data-testid="stMain"] .block-container:has([data-testid="stCode"]) {
        min-height: calc(100vh - 2rem);
        display: flex;
        flex-direction: column;
    }
    [data-testid="stMain"] .block-container:has([data-testid="stTabs"]) > [data-testid="stVerticalBlock"],
    [data-testid="stMain"] .block-container:has([data-testid="stCode"]) > [data-testid="stVerticalBlock"] {
        width: 100%;
        margin-top: auto;
        margin-bottom: auto;
    }
    [data-testid="stMain"] { color: var(--ink); }
    [data-testid="stMain"] h1 { text-align: center; }
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] p {
        color: var(--ink);
    }
    [data-testid="stMain"] [data-testid="stCaptionContainer"] p,
    [data-testid="stMain"] [data-testid="stWidgetLabel"] p,
    [data-testid="stMain"] [data-testid="stMetricLabel"] {
        color: var(--muted);
    }
    [data-testid="stMain"] [data-testid="stMetricValue"] {
        color: var(--ink);
    }
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--line) !important;
        background: var(--panel);
        border-radius: 18px;
    }
    [data-testid="stMain"] .st-key-auth-card,
    [data-testid="stMain"] .st-key-auth-setup-card {
        width: 100%;
        max-width: 620px;
        margin: 0 auto;
        padding: clamp(1rem, 4vw, 2rem);
    }
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stTabs"]),
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stCode"]) {
        width: 100%;
        max-width: 620px;
        margin-left: auto;
        margin-right: auto;
    }
    [data-testid="stMain"] [data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stTabs"]) [data-testid="stCaptionContainer"] p {
        text-align: center;
    }
    h1, h2, h3, h4 {
        font-family: 'Manrope', 'Segoe UI', sans-serif !important;
        color: var(--ink) !important;
        letter-spacing: -.035em;
    }
    h1 { font-size: clamp(2rem, 3vw, 2.8rem) !important; }
    h2 { font-size: 1.45rem !important; }
    h3 { font-size: 1.12rem !important; }
    .eyebrow {
        color: var(--blue);
        font-size: .73rem;
        font-weight: 700;
        letter-spacing: .13em;
        text-transform: uppercase;
        text-align: center;
        margin-bottom: .35rem;
    }
    .welcome-subtitle {
        color: var(--muted);
        font-size: 1.08rem;
        text-align: center;
        margin-top: -.5rem;
    }
    .blue-rule {
        width: 58px;
        height: 5px;
        border-radius: 8px;
        background: linear-gradient(90deg, #1d5ff3, #5295ff);
        margin: 1rem auto 1.55rem;
    }
    .brand-mark {
        font-family: 'Manrope', sans-serif;
        font-size: 1.55rem;
        font-weight: 800;
        letter-spacing: -.06em;
        color: __SIDEBAR_BRAND__;
        text-align: center;
        margin: 0 0 .1rem;
    }
    .brand-tagline {
        color: __SIDEBAR_TAGLINE__;
        font-size: .76rem;
        text-align: center;
        margin: 0 0 2rem;
    }
    .sidebar-status {
        margin-top: 1.6rem;
        padding: .68rem .8rem;
        border-radius: 999px;
        background: __SIDEBAR_STATUS_BG__;
        color: __SIDEBAR_STATUS_TEXT__;
        font-size: .78rem;
        text-align: center;
    }
    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        margin-right: .45rem;
        border-radius: 50%;
        background: #20c997;
        box-shadow: 0 0 0 4px rgba(32,201,151,.14);
    }
    .status-dot.offline {
        background: #ff8c72;
        box-shadow: 0 0 0 4px rgba(255,140,114,.14);
    }
    [data-testid="stForm"] {
        padding: .85rem;
        border: 1px solid var(--line);
        border-radius: 20px;
        background: var(--panel-tint);
        box-shadow: 0 14px 36px var(--shadow);
    }
    [data-testid="stTextInput"] input {
        min-height: 3.1rem;
        border-radius: 14px;
        border: 1px solid var(--line) !important;
        background: var(--field);
        color: var(--ink) !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: var(--placeholder) !important;
        opacity: 1;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: #4a83f5;
        box-shadow: 0 0 0 3px rgba(36,99,235,.12);
    }
    [data-testid="stFileUploader"] section {
        border: 1px dashed var(--line) !important;
        border-radius: 14px;
        background: var(--field) !important;
        color: var(--ink) !important;
    }
    [data-testid="stFileUploader"] section button {
        border: 1px solid var(--line) !important;
        background: var(--panel) !important;
        color: var(--ink) !important;
    }
    [data-testid="stButton"] button,
    [data-testid="stFormSubmitButton"] button {
        min-height: 2.9rem;
        border-radius: 12px;
        font-weight: 700;
        transition: transform .15s ease, box-shadow .15s ease;
    }
    [data-testid="stFormSubmitButton"] button,
    [data-testid="stButton"] button[kind="primary"] {
        border: 0 !important;
        color: #fff !important;
        background: linear-gradient(110deg, #1558ed, #3379ff) !important;
        box-shadow: 0 8px 18px rgba(36,99,235,.2) !important;
    }
    [data-testid="stFormSubmitButton"] button p,
    [data-testid="stFormSubmitButton"] button span {
        color: #fff !important;
    }
    [data-testid="stFormSubmitButton"] button:hover,
    [data-testid="stButton"] button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 22px rgba(36,99,235,.16);
    }
    .step-card {
        text-align: center;
        padding: .45rem .25rem 1.1rem;
    }
    .step-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 58px;
        height: 58px;
        margin-bottom: .55rem;
        border-radius: 50%;
        font-size: 1.45rem;
        font-weight: 700;
    }
    .step-blue { color: __STEP_BLUE_FG__; background: __STEP_BLUE_BG__; }
    .step-green { color: __STEP_GREEN_FG__; background: __STEP_GREEN_BG__; }
    .step-purple { color: __STEP_PURPLE_FG__; background: __STEP_PURPLE_BG__; }
    .step-orange { color: __STEP_ORANGE_FG__; background: __STEP_ORANGE_BG__; }
    .step-title { color: var(--ink); font-weight: 700; font-size: .92rem; }
    .step-caption { color: var(--muted); font-size: .73rem; margin-top: .13rem; }
    .metric-card {
        display: flex;
        align-items: center;
        gap: .9rem;
        min-height: 104px;
        padding: 1.05rem;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: var(--panel-tint);
        box-shadow: 0 7px 22px var(--shadow);
    }
    .metric-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 54px;
        width: 54px;
        height: 54px;
        border-radius: 16px;
        font-size: 1.35rem;
    }
    .metric-blue { color: __METRIC_BLUE_FG__; background: __METRIC_BLUE_BG__; }
    .metric-green { color: __METRIC_GREEN_FG__; background: __METRIC_GREEN_BG__; }
    .metric-orange { color: __METRIC_ORANGE_FG__; background: __METRIC_ORANGE_BG__; }
    .metric-value {
        color: var(--ink);
        font-family: 'Manrope', sans-serif;
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .metric-label { color: var(--muted); font-size: .8rem; margin-top: .22rem; }
    .section-heading {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        margin: 1.7rem 0 .75rem;
    }
    .report-card {
        padding: 1.1rem 1.25rem;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: var(--panel);
        box-shadow: 0 8px 24px var(--shadow);
    }
    .report-meta { color: var(--muted); font-size: .82rem; }
    .verdict-supported { color: #05855f; }
    .verdict-unsupported { color: #c53c4a; }
    .verdict-uncertain { color: #a26a08; }
    [data-testid="stExpander"] {
        border-color: var(--line);
        border-radius: 14px;
        background: __EXPANDER__;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p {
        color: var(--ink) !important;
    }
    [data-testid="stProgressBar"] > div > div {
        background: linear-gradient(90deg, #1760f5, #64a2ff);
    }
    @media (max-width: 850px) {
        [data-testid="stMain"] .block-container { padding: 1.4rem 1rem 3rem; }
    }
    </style>
    """.replace("__INK__", theme["ink"])
    .replace("__MUTED__", theme["muted"])
    .replace("__BLUE__", theme["blue"])
    .replace("__LINE__", theme["line"])
    .replace("__PANEL__", theme["panel"])
    .replace("__CANVAS__", theme["canvas"])
    .replace("__CANVAS_GLOW__", theme["canvas_glow"])
    .replace("__PANEL_TINT__", theme["panel_tint"])
    .replace("__FIELD__", theme["field"])
    .replace("__PLACEHOLDER__", theme["placeholder"])
    .replace("__SHADOW__", theme["shadow"])
    .replace("__SIDEBAR_START__", theme["sidebar_start"])
    .replace("__SIDEBAR_END__", theme["sidebar_end"])
    .replace("__SIDEBAR_TEXT__", theme["sidebar_text"])
    .replace("__SIDEBAR_MUTED__", theme["sidebar_muted"])
    .replace("__SIDEBAR_BORDER__", theme["sidebar_border"])
    .replace("__SIDEBAR_HOVER__", theme["sidebar_hover"])
    .replace("__SIDEBAR_BRAND__", theme["sidebar_brand"])
    .replace("__SIDEBAR_TAGLINE__", theme["sidebar_tagline"])
    .replace("__SIDEBAR_STATUS_BG__", theme["sidebar_status_bg"])
    .replace("__SIDEBAR_STATUS_TEXT__", theme["sidebar_status_text"])
    .replace("__STEP_BLUE_FG__", theme["step_blue_fg"])
    .replace("__STEP_BLUE_BG__", theme["step_blue_bg"])
    .replace("__STEP_GREEN_FG__", theme["step_green_fg"])
    .replace("__STEP_GREEN_BG__", theme["step_green_bg"])
    .replace("__STEP_PURPLE_FG__", theme["step_purple_fg"])
    .replace("__STEP_PURPLE_BG__", theme["step_purple_bg"])
    .replace("__STEP_ORANGE_FG__", theme["step_orange_fg"])
    .replace("__STEP_ORANGE_BG__", theme["step_orange_bg"])
    .replace("__METRIC_BLUE_FG__", theme["metric_blue_fg"])
    .replace("__METRIC_BLUE_BG__", theme["metric_blue_bg"])
    .replace("__METRIC_GREEN_FG__", theme["metric_green_fg"])
    .replace("__METRIC_GREEN_BG__", theme["metric_green_bg"])
    .replace("__METRIC_ORANGE_FG__", theme["metric_orange_fg"])
    .replace("__METRIC_ORANGE_BG__", theme["metric_orange_bg"])
    .replace("__EXPANDER__", theme["expander"]),
    unsafe_allow_html=True,
)

auth_context = authenticate_user()
if auth_context is None:
    st.stop()
supabase_client, auth_session = auth_context


def api_is_online() -> bool:
    try:
        response = requests.get(f"{st.session_state.api_url}/", timeout=2)
        return response.ok
    except requests.exceptions.RequestException:
        return False


def render_sidebar() -> tuple[str, bool]:
    with st.sidebar:
        st.image(str(LOGO_PATH), width=72)
        st.markdown(
            "<div class='brand-mark'>M.A.R.S.</div>"
            "<div class='brand-tagline'>Multi-Agent Research System</div>",
            unsafe_allow_html=True,
        )
        page = st.radio(
            "Workspace",
            ["⌂  Dashboard", "▤  My Reports", "▥  Agent Activity", "⚙  Settings"],
            label_visibility="visible",
            key="navigation",
        )
        st.toggle("Dark mode", key="dark_mode")
        st.caption(f"Signed in as {auth_session.user.email or 'M.A.R.S. user'}")
        if st.button("Sign out", key="sign_out", use_container_width=True):
            if sign_out(supabase_client):
                st.rerun()
        online = api_is_online()
        status_class = "" if online else "offline"
        status_text = "System online" if online else "API offline"
        st.markdown(
            f"<div class='sidebar-status'><span class='status-dot {status_class}'></span>"
            f"{status_text}</div>",
            unsafe_allow_html=True,
        )
    return page, online


def metric_card(icon: str, value: str, label: str, color: str) -> str:
    return (
        "<div class='metric-card'>"
        f"<div class='metric-icon {color}'>{icon}</div>"
        "<div>"
        f"<div class='metric-value'>{value}</div>"
        f"<div class='metric-label'>{label}</div>"
        "</div></div>"
    )


def aggregate_metrics() -> tuple[int, str, int]:
    reports = st.session_state.reports
    checks = [
        check
        for report in reports
        for check in report.get("fact_checks", [])
    ]
    supported = sum(check.get("verdict") == "Supported" for check in checks)
    verified_rate = f"{supported / len(checks):.0%}" if checks else "—"
    conflicts = sum(len(report.get("conflicts", [])) for report in reports)
    return len(reports), verified_rate, conflicts


def render_trust_dashboard(checks: list[dict], sources: list[str]) -> None:
    st.subheader("Trust & Verification Dashboard")
    st.caption(
        "Confidence is the model's assessment of the available evidence, not a "
        "calibrated probability or a guarantee of accuracy."
    )

    verdicts = {
        "Supported": sum(check.get("verdict") == "Supported" for check in checks),
        "Uncertain": sum(check.get("verdict") == "Uncertain" for check in checks),
        "Unsupported": sum(
            check.get("verdict") == "Unsupported" for check in checks
        ),
    }
    columns = st.columns(3)
    for column, (verdict, count) in zip(columns, verdicts.items()):
        column.metric(f"{verdict} claims", count)

    for check in checks:
        level, explanation, score = confidence_assessment(check.get("confidence"))
        badge = {
            "High confidence": "🟢",
            "Medium confidence": "🟡",
            "Low confidence": "🔴",
        }.get(level, "⚪")
        st.markdown(f"**{badge} {level}** · {check.get('claim', 'Claim')}")
        if score is not None:
            st.progress(score, text=f"{score:.0%} confidence")
        st.caption(explanation)

    if sources:
        st.markdown("#### Source diversity")
        diversity = source_diversity(sources)
        populated = {
            category: count for category, count in diversity.items() if count
        }
        source_columns = st.columns(len(diversity))
        for column, (category, count) in zip(source_columns, diversity.items()):
            column.metric(category, count)
        if populated:
            st.bar_chart(
                {
                    "Domain type": list(populated),
                    "Sources": list(populated.values()),
                },
                x="Domain type",
                y="Sources",
            )
        else:
            st.info("No source URLs were available to categorize.")
        st.caption(
            "Domain extensions describe URL categories; they do not prove source "
            "accuracy or independence."
        )


def render_report(
    report: dict,
    show_details: bool = True,
    download_slot: str = "report",
) -> None:
    title_column, download_column = st.columns([5, 1.5])
    title_column.markdown(f"### {report['topic']}")
    download_column.download_button(
        "Download report",
        data=report_to_markdown(report),
        file_name=report_filename(report["topic"]),
        mime="text/markdown",
        key=f"download-{report.get('id', 'report')}-{download_slot}",
        use_container_width=True,
    )
    st.caption(f"Completed {report.get('created_at', 'recently')}")
    if report.get("document_name"):
        st.caption(
            f"Context document: {report['document_name']} · "
            "provided context; not independently verified"
        )

    checks = report.get("fact_checks", [])
    supported = sum(check.get("verdict") == "Supported" for check in checks)
    left, middle, right = st.columns(3)
    left.metric("Claims checked", len(checks))
    middle.metric("Supported", supported)
    right.metric("Conflicting claims", len(report.get("conflicts", [])))

    sources = report.get("sources", [])
    if checks or sources:
        render_trust_dashboard(checks, sources)

    draft = report.get("research_draft", "").strip()
    if draft:
        st.markdown(draft)

    if not show_details:
        return

    conflicts = report.get("conflicts", [])
    if conflicts:
        with st.expander(f"Conflicting claims · {len(conflicts)}"):
            for conflict in conflicts:
                st.markdown(f"**{conflict.get('claim', 'Disagreement')}**")
                col_a, col_b = st.columns(2)
                col_a.write(conflict.get("source_a_says", ""))
                source_a = conflict.get("source_a_url")
                if source_a == "[D1]":
                    col_a.caption(
                        f"Uploaded document · {report.get('document_name', 'PDF')}"
                    )
                elif source_a:
                    col_a.markdown(f"[Source A]({source_a})")
                col_b.write(conflict.get("source_b_says", ""))
                source_b = conflict.get("source_b_url")
                if source_b == "[D1]":
                    col_b.caption(
                        f"Uploaded document · {report.get('document_name', 'PDF')}"
                    )
                elif source_b:
                    col_b.markdown(f"[Source B]({source_b})")

    if checks:
        with st.expander(f"Claim-by-claim verification · {len(checks)}"):
            for check in checks:
                verdict = check.get("verdict", "Uncertain")
                st.markdown(f"**{verdict}:** {check.get('claim', '')}")
                st.caption(f"Confidence · {check.get('confidence', 0):.0%}")
                evidence_url = check.get("evidence_url")
                if evidence_url:
                    st.markdown(f"[Open evidence source]({evidence_url})")
                if check.get("reason"):
                    st.caption(check["reason"])
                st.divider()
    elif report.get("fact_check_reason"):
        st.info(report["fact_check_reason"])

    if sources:
        with st.expander(f"Sources used · {len(sources)}"):
            for index, source in enumerate(sources, start=1):
                st.markdown(f"[S{index}]({source})")

    search_errors = report.get("search_errors", [])
    if search_errors:
        st.warning("Some searches were incomplete: " + "; ".join(search_errors))


def run_research(
    topic: str,
    access_token: str,
    document_context: str = "",
    document_name: str = "",
) -> dict:
    report = {
        "id": uuid4().hex,
        "topic": topic,
        "document_name": document_name,
        "created_at": datetime.now().strftime("%b %d, %Y at %I:%M %p"),
        "research_draft": "",
        "sources": [],
        "conflicts": [],
        "fact_checks": [],
        "fact_check_reason": "",
        "search_errors": [],
        "activity": [],
    }
    progress_bar = st.progress(0, text="Preparing research agents")

    with st.status("Preparing research agents...", expanded=True) as status:
        with requests.post(
            f"{st.session_state.api_url}/research/stream",
            json={
                "topic": topic,
                "document_name": document_name,
                "document_context": document_context,
            },
            headers={"Authorization": f"Bearer {access_token}"},
            stream=True,
            timeout=(10, 300),
        ) as response:
            response.raise_for_status()
            completed = False

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode("utf-8")
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                if payload == "[DONE]":
                    completed = True
                    break

                try:
                    event = json.loads(payload)
                except json.JSONDecodeError as exc:
                    raise RuntimeError("The API returned an invalid event.") from exc

                if "error" in event:
                    raise RuntimeError(event["error"])

                node = event.get("node")
                if not node or not isinstance(event.get("data"), dict):
                    raise RuntimeError("The API returned an unexpected event.")

                update = event["data"]
                label = STEPS.get(node, node.replace("_", " ").title())
                status.update(label=label, state="running")
                status.write(f"✓ {label}")
                report["activity"].append(label)

                if node == "planner":
                    report["research_questions"] = update.get("research_questions", [])
                elif node == "searcher":
                    report["source_count"] = len(update.get("search_results", []))
                    report["search_errors"] = update.get("search_errors", [])
                elif node == "conflict":
                    report["conflicts"] = update.get("conflicts", [])
                elif node == "critic":
                    report["critic_feedback"] = update.get("critic_feedback", "")
                    report["critic_score"] = update.get("critic_score")
                elif node == "synthesizer":
                    report["research_draft"] = update.get("research_draft", "")
                    report["sources"] = update.get("sources", [])
                    report["search_errors"] = update.get("search_errors", [])
                elif node == "fact_checker":
                    check_report = update.get("fact_check_report", {})
                    report["fact_checks"] = check_report.get("checks", [])
                    report["fact_check_reason"] = check_report.get("reason", "")

                progress = min((len(report["activity"]) / 8), 1.0)
                progress_bar.progress(progress, text=f"{label} · in progress")

            if not completed:
                raise RuntimeError("The research stream ended before completion.")

        progress_bar.progress(1.0, text="Research complete")
        status.update(label="Research complete", state="complete", expanded=False)

    return report


def render_dashboard(is_online: bool) -> None:
    st.image(str(LOGO_PATH), width=72)
    st.markdown("<div class='eyebrow'>Your research workspace</div>", unsafe_allow_html=True)
    st.title("M.A.R.S.", anchor="mars")
    st.markdown(
        "<div class='welcome-subtitle'>Explore complex topics with AI agents that "
        "research, verify, and report.</div><div class='blue-rule'></div>",
        unsafe_allow_html=True,
    )

    with st.form("research_form"):
        topic_column, button_column = st.columns([5, 1.5], vertical_alignment="bottom")
        with topic_column:
            topic = st.text_input(
                "Research topic",
                placeholder="Ask a question or enter a topic to investigate...",
                label_visibility="collapsed",
            )
        uploaded_pdf = st.file_uploader(
            "Attach a research PDF (optional)",
            type=["pdf"],
            help="Up to 10 MB and 100 pages. Text-only PDFs are supported; scanned PDFs need OCR.",
        )
        with button_column:
            submitted = st.form_submit_button(
                "▶  Start research",
                type="primary",
                use_container_width=True,
            )
    if submitted:
        if not topic.strip():
            st.warning("Enter a research topic to get started.")
        elif not is_online:
            st.error("The API is offline. Start the FastAPI server and try again.")
        else:
            document_context = ""
            document_name = ""
            if uploaded_pdf is not None:
                document_name = Path(uploaded_pdf.name).name[:255]
                try:
                    document_context, was_truncated = extract_pdf_text(
                        uploaded_pdf.getvalue()
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    if was_truncated:
                        st.warning(
                            "The PDF text was truncated to fit the research context limit."
                        )
                    st.caption(
                        f"Added {len(document_context):,} characters from "
                        f"{document_name} as context."
                    )
            if uploaded_pdf is None or document_context:
                try:
                    report = run_research(
                        topic.strip(),
                        access_token=auth_session.access_token,
                        document_context=document_context,
                        document_name=document_name,
                    )
                    st.session_state.reports.insert(0, report)
                    st.success("Your evidence-backed report is ready.")
                except requests.exceptions.RequestException as exc:
                    st.error(f"Could not connect to the research API: {exc}")
                except RuntimeError as exc:
                    st.error(str(exc))

    st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)
    step_columns = st.columns(4)
    workflow = [
        ("🔎", "Research", "Find relevant evidence", "step-blue"),
        ("✓", "Verify", "Check important claims", "step-green"),
        ("⚖", "Analyse", "Compare source claims", "step-purple"),
        ("▤", "Report", "Read a cited report", "step-orange"),
    ]
    for column, (icon, title, caption, color) in zip(step_columns, workflow):
        with column:
            st.markdown(
                f"<div class='step-card'><div class='step-icon {color}'>{icon}</div>"
                f"<div class='step-title'>{title}</div>"
                f"<div class='step-caption'>{caption}</div></div>",
                unsafe_allow_html=True,
            )

    total_reports, verification_rate, total_conflicts = aggregate_metrics()
    reports_column, checks_column, conflicts_column = st.columns(3)
    reports_column.markdown(
        metric_card("▤", str(total_reports), "Total reports", "metric-blue"),
        unsafe_allow_html=True,
    )
    checks_column.markdown(
        metric_card("✓", verification_rate, "Claims supported", "metric-green"),
        unsafe_allow_html=True,
    )
    conflicts_column.markdown(
        metric_card("⚠", str(total_conflicts), "Conflicts found", "metric-orange"),
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='section-heading'><h3>Recent report</h3>"
        "<span class='report-meta'>Saved in this session</span></div>",
        unsafe_allow_html=True,
    )
    if st.session_state.reports:
        latest = st.session_state.reports[0]
        with st.container(border=True):
            st.markdown(f"**{latest['topic']}**")
            st.caption(
                f"Completed · {latest.get('created_at', 'recently')} · "
                f"{len(latest.get('sources', []))} sources"
            )
            with st.expander("Open report"):
                render_report(latest, download_slot="dashboard-card")
    else:
        with st.container(border=True):
            st.markdown("**Your first research report will appear here**")
            st.caption(
                "Enter a topic above to begin. Your session summary updates as "
                "reports and verified claims are added."
            )

    if st.session_state.reports:
        st.markdown("<div class='section-heading'><h3>Latest findings</h3></div>", unsafe_allow_html=True)
        render_report(st.session_state.reports[0], download_slot="dashboard-latest")


page, api_online = render_sidebar()
if page.startswith("⌂"):
    render_dashboard(api_online)
elif page.startswith("▤"):
    st.markdown("<div class='eyebrow'>Research library</div>", unsafe_allow_html=True)
    st.title("My Reports")
    st.caption("Reports are kept in your current Streamlit session.")
    if not st.session_state.reports:
        st.info("No reports yet. Start a research run from the Dashboard.")
    for index, report in enumerate(st.session_state.reports):
        with st.expander(
            f"{report['topic']}  ·  {report.get('created_at', 'recently')}",
            expanded=index == 0,
        ):
            render_report(report, download_slot=f"library-{index}")
elif page.startswith("▥"):
    st.markdown("<div class='eyebrow'>Live and recent runs</div>", unsafe_allow_html=True)
    st.title("Agent Activity")
    st.caption("Follow the stages completed for each research report.")
    if not st.session_state.reports:
        st.info("Agent activity will appear here after your first research run.")
    for report in st.session_state.reports:
        with st.container(border=True):
            st.markdown(f"**{report['topic']}**")
            st.caption(f"Completed · {report.get('created_at', 'recently')}")
            for activity in report.get("activity", []):
                st.markdown(f"✓  {activity}")
            if report.get("critic_feedback"):
                score = report.get("critic_score")
                label = f"Coverage review · {score:.0%}" if score is not None else "Coverage review"
                st.caption(f"{label}: {report['critic_feedback']}")
elif page.startswith("⚙"):
    st.markdown("<div class='eyebrow'>Workspace preferences</div>", unsafe_allow_html=True)
    st.title("Settings")
    st.caption("Configure the FastAPI endpoint used by this dashboard.")
    with st.form("settings_form"):
        api_url = st.text_input(
            "API base URL",
            value=st.session_state.api_url,
            help="The live API is https://fact-checker-agent.onrender.com",
        )
        save_settings = st.form_submit_button("Save settings", type="primary")
    if save_settings:
        st.session_state.api_url = api_url.strip().rstrip("/")
        st.success("API endpoint saved for this session.")
    st.caption(
        "Your API keys stay on the backend; the dashboard only sends research topics."
    )
