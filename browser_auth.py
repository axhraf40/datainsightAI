"""Cookie navigateur persistant — survit au F5 (via CookieManager + st.context.cookies)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import extra_streamlit_components as stx
import streamlit as st

BROWSER_COOKIE = "di_browser_id"


@st.cache_resource
def _cookie_manager():
    return stx.CookieManager()


def get_browser_id() -> str | None:
    """Retourne l'identifiant stable de ce navigateur."""
    if st.session_state.get("browser_id"):
        return st.session_state.browser_id

    try:
        bid = st.context.cookies.get(BROWSER_COOKIE)
        if bid:
            st.session_state.browser_id = bid
            return bid
    except Exception:
        pass

    manager = _cookie_manager()
    all_cookies = manager.get_all()
    if all_cookies is None:
        return None

    bid = all_cookies.get(BROWSER_COOKIE) or manager.get(BROWSER_COOKIE)
    if bid:
        st.session_state.browser_id = bid
    return bid


def ensure_browser_id() -> str | None:
    """Crée le cookie navigateur si absent. Peut provoquer un rerun."""
    browser_id = get_browser_id()
    if browser_id:
        return browser_id

    manager = _cookie_manager()
    if manager.get_all() is None:
        return None

    new_id = secrets.token_urlsafe(16)
    expires = datetime.now() + timedelta(days=365)
    manager.set(
        BROWSER_COOKIE,
        new_id,
        expires_at=expires,
        key="di_set_browser_cookie",
        same_site="lax",
    )
    st.session_state.browser_id = new_id
    st.rerun()
    return new_id
