"""UI panels and page styling for the Streamlit app."""

from __future__ import annotations

import html
from datetime import datetime

import streamlit as st


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 10% 15%, rgba(16, 185, 129, 0.16) 0%, rgba(16, 185, 129, 0) 30%),
                radial-gradient(circle at 85% 20%, rgba(59, 130, 246, 0.16) 0%, rgba(59, 130, 246, 0) 35%),
                linear-gradient(180deg, #08111f 0%, #0b1220 45%, #09101a 100%);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(8, 17, 31, 0.92) 0%, rgba(10, 18, 31, 0.96) 100%);
        }
        .app-hero {
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 22px;
            padding: 1.4rem 1.4rem 1.1rem 1.4rem;
            background: linear-gradient(145deg, rgba(15, 23, 42, 0.82) 0%, rgba(30, 41, 59, 0.64) 100%);
            box-shadow: 0 18px 40px rgba(2, 6, 23, 0.35);
            margin-bottom: 1rem;
            backdrop-filter: blur(12px);
        }
        .session-card {
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 20px;
            padding: 1rem 1rem 0.9rem 1rem;
            background: linear-gradient(180deg, rgba(10, 17, 30, 0.9) 0%, rgba(15, 23, 42, 0.72) 100%);
            box-shadow: 0 14px 35px rgba(2, 6, 23, 0.24);
            backdrop-filter: blur(12px);
            min-height: 100%;
        }
        .settings-card,
        .help-card {
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 20px;
            padding: 1rem 1rem 1rem 1rem;
            background: linear-gradient(180deg, rgba(10, 17, 30, 0.9) 0%, rgba(15, 23, 42, 0.72) 100%);
            box-shadow: 0 14px 35px rgba(2, 6, 23, 0.24);
            backdrop-filter: blur(12px);
            min-height: 100%;
            margin-bottom: 0.75rem;
        }
        .card-label {
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: #94a3b8;
            font-size: 0.72rem;
            margin-bottom: 0.3rem;
        }
        .card-title {
            margin: 0;
            color: #f8fafc;
            font-size: 1.08rem;
            font-weight: 700;
        }
        .card-copy {
            color: #cbd5e1;
            font-size: 0.94rem;
            line-height: 1.5;
        }
        .session-eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: #94a3b8;
            font-size: 0.72rem;
            margin-bottom: 0.25rem;
        }
        .session-title {
            margin: 0;
            color: #f8fafc;
            font-size: 1.1rem;
            font-weight: 700;
        }
        .session-meta {
            color: #cbd5e1;
            font-size: 0.92rem;
            line-height: 1.45;
        }
        div[data-testid="stTextInput"] input,
        div[data-testid="stSelectbox"] div[role="combobox"],
        div[data-testid="stNumberInput"] input {
            border-radius: 14px !important;
            background: rgba(15, 23, 42, 0.9) !important;
        }
        div.stButton > button {
            border-radius: 14px;
            border: 0;
            background: linear-gradient(135deg, #fb7185 0%, #f97316 100%);
            color: white;
            font-weight: 700;
            box-shadow: 0 14px 30px rgba(249, 115, 22, 0.24);
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        div.stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 18px 36px rgba(249, 115, 22, 0.3);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
        <div class="app-hero">
            <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.35rem;">
                <div style="width:12px;height:12px;border-radius:999px;background:linear-gradient(135deg,#34d399,#60a5fa);"></div>
                <h1 style="margin:0;color:#f8fafc;font-size:2rem;line-height:1.1;">README Upgrade Studio</h1>
            </div>
            <p style="margin:0.25rem 0 0;color:#cbd5e1;max-width:100%;">
                Turn any public GitHub repository into a clean, professional, and ready-to-share README.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_help_panel() -> None:
    st.markdown(
        """
        <div class="help-card">
            <div class="card-label">Helper Guide</div>
            <p class="card-title">How to use this platform</p>
            <div class="card-copy" style="margin-top:0.75rem;">
                <ol style="margin:0;padding-left:1.1rem;display:grid;gap:0.45rem;">
                    <li>Enter a GitHub username.</li>
                    <li>Select one of the public repositories that appears.</li>
                    <li>(Optional) Add LinkedIn profile URL and email for the Author section.</li>
                    <li>Click Generate README.</li>
                    <li>Review output in Rendered/Raw mode, edit if needed, then Save Changes.</li>
                    <li>Use Update README.md to push to GitHub or Download README.md.</li>
                </ol>
                </div>
                <div style="margin-top:0.55rem;">
                    Tip: if output misses details, regenerate once and compare versions from history.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_session_panel(started_at: datetime) -> None:
    st.markdown(
        f"""
        <div class="session-card">
            <div class="session-eyebrow">Session</div>
            <p class="session-title">Active run details</p>
            <div class="session-meta" style="margin-top:0.8rem;">
                <div><strong style="color:#f8fafc;">Started:</strong> {html.escape(started_at.strftime('%Y-%m-%d %H:%M:%S IST'))}</div>
                <div style="margin-top:0.55rem;">Output can be edited, saved, downloaded, and pushed to GitHub.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
