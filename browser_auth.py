"""Cookie navigateur persistant — survit au F5 (via CookieManager + st.context.cookies)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import extra_streamlit_components as stx
import streamlit as st

BROWSER_COOKIE = "di_browser_id"


_MANAGER_STATE_KEY = "_di_cookie_manager"


def mount_cookie_manager() -> "stx.CookieManager":
    """Render the cookie component once per script run.

    The CookieManager is a widget, so it must not live inside an
    ``st.cache_resource`` function (newer Streamlit versions warn about it).
    We render it once at the start of each run and reuse it for the rest of
    the run via session_state.
    """
    manager = stx.CookieManager(key="di_cookie_manager")
    st.session_state[_MANAGER_STATE_KEY] = manager
    return manager


def _cookie_manager() -> "stx.CookieManager":
    manager = st.session_state.get(_MANAGER_STATE_KEY)
    if manager is None:
        manager = mount_cookie_manager()
    return manager


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
    all_cookies = manager.cookies
    if all_cookies is None:
        return None

    bid = all_cookies.get(BROWSER_COOKIE) or manager.get(BROWSER_COOKIE)
    if bid:
        st.session_state.browser_id = bid
    return bid


def ensure_browser_id() -> str | None:
    """Crée le cookie navigateur si absent. Peut provoquer un rerun."""
    mount_cookie_manager()
    browser_id = get_browser_id()
    if browser_id:
        return browser_id

    manager = _cookie_manager()
    if manager.cookies is None:
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
