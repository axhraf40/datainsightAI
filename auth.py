"""Authentification : inscription, connexion, mot de passe oublié."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

import bcrypt
import streamlit as st

from browser_auth import ensure_browser_id, get_browser_id
from database import (
    clear_client_session_cache,
    create_session,
    create_user,
    get_user_by_email,
    get_user_by_username,
    load_client_session_cache,
    reset_password,
    revoke_session,
    save_client_session_cache,
    set_reset_token,
    verify_session,
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def login_user(email: str, password: str) -> dict | None:
    user = get_user_by_email(email)
    if user and verify_password(password, user["password_hash"]):
        return {"id": user["id"], "email": user["email"], "username": user["username"]}
    return None


def register_user(email: str, username: str, password: str) -> tuple[bool, str]:
    if len(password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    if get_user_by_email(email):
        return False, "Cet email est déjà utilisé."
    if get_user_by_username(username):
        return False, "Ce nom d'utilisateur est déjà pris."
    user_id = create_user(email, username, hash_password(password))
    if not user_id:
        return False, "Impossible de créer le compte."
    return True, "Compte créé avec succès. Connectez-vous."


def request_password_reset(email: str) -> tuple[bool, str]:
    user = get_user_by_email(email)
    if not user:
        return False, "Aucun compte associé à cet email."
    token = secrets.token_hex(4).upper()
    expires = (datetime.now() + timedelta(hours=1)).isoformat()
    set_reset_token(email, token, expires)
    return True, (
        f"Code de réinitialisation (valide 1h) : **{token}**\n\n"
        "En production, ce code serait envoyé par email."
    )


def apply_password_reset(email: str, token: str, new_password: str) -> tuple[bool, str]:
    if len(new_password) < 6:
        return False, "Le mot de passe doit contenir au moins 6 caractères."
    if reset_password(email, token.strip().upper(), hash_password(new_password)):
        return True, "Mot de passe mis à jour. Vous pouvez vous connecter."
    return False, "Code invalide ou expiré."


def update_user_profile(user_id: int, email: str, username: str, password: str | None = None) -> tuple[bool, str]:
    from database import update_user_profile_db
    p_hash = None
    if password and password.strip():
        if len(password) < 6:
            return False, "Le mot de passe doit contenir au moins 6 caractères."
        p_hash = hash_password(password)
    return update_user_profile_db(user_id, email, username, p_hash)


def get_streamlit_session_id() -> str | None:
    """Compatibilité — identifiant navigateur via cookie."""
    return get_browser_id()


def _persist_client_cache(token: str, binding: str, user_id: int) -> None:
    browser_id = get_browser_id() or st.session_state.get("browser_id")
    if browser_id:
        save_client_session_cache(browser_id, token, binding, user_id)
        st.session_state.pop("_pending_auth_cache", None)
    else:
        st.session_state._pending_auth_cache = {
            "token": token,
            "binding": binding,
            "user_id": user_id,
        }


def _flush_pending_auth_cache() -> None:
    pending = st.session_state.get("_pending_auth_cache")
    if not pending:
        return
    browser_id = get_browser_id()
    if not browser_id:
        return
    save_client_session_cache(
        browser_id,
        pending["token"],
        pending["binding"],
        pending["user_id"],
    )
    st.session_state.pop("_pending_auth_cache", None)


def establish_user_session(user: dict) -> None:
    """Lie la session au navigateur courant (token + secret jamais dans l'URL)."""
    token, binding = create_session(user["id"])
    st.session_state.user = user
    st.session_state.authenticated = True
    st.session_state.auth_token = token
    st.session_state.session_binding = binding
    _persist_client_cache(token, binding, user["id"])


def _apply_valid_session(token: str, binding: str) -> bool:
    user = verify_session(token, binding)
    if not user:
        return False
    st.session_state.auth_token = token
    st.session_state.session_binding = binding
    st.session_state.user = user
    st.session_state.authenticated = True
    _persist_client_cache(token, binding, user["id"])
    return True


def restore_session_from_state() -> bool:
    """Restaure depuis session_state ou cache serveur."""
    token = st.session_state.get("auth_token")
    binding = st.session_state.get("session_binding")

    if not token or not binding:
        cached = load_client_session_cache(get_browser_id())
        if cached:
            token, binding = cached

    if not token or not binding:
        return False

    if not _apply_valid_session(token, binding):
        clear_client_session_cache(get_browser_id())
        return False
    return True


def init_session_auth() -> None:
    """Restaure la connexion après F5 via cookie navigateur + cache serveur."""
    strip_legacy_session_url()

    browser_id = ensure_browser_id()
    _flush_pending_auth_cache()

    if st.session_state.get("authenticated") and st.session_state.get("auth_token"):
        return

    if browser_id is None:
        return

    if restore_session_from_state():
        return


def ensure_authenticated() -> None:
    """Vérifie que la session est toujours valide côté serveur."""
    token = st.session_state.get("auth_token")
    binding = st.session_state.get("session_binding")

    if not st.session_state.get("authenticated") or not token or not binding:
        if restore_session_from_state():
            return
        if st.session_state.get("authenticated"):
            logout()
        return

    user = verify_session(token, binding)
    if not user:
        logout()
        return
    st.session_state.user = user
    st.session_state.authenticated = True
    _persist_client_cache(token, binding, user["id"])


def strip_legacy_session_url() -> None:
    """Supprime les anciens liens ?session=... (faille de sécurité)."""
    if st.query_params.get("session"):
        del st.query_params["session"]


def logout() -> None:
    clear_client_session_cache(get_browser_id() or st.session_state.get("browser_id"))
    st.session_state.pop("browser_id", None)
    st.session_state.pop("_pending_auth_cache", None)
    token = st.session_state.get("auth_token")
    if token:
        try:
            revoke_session(token)
        except Exception:
            pass

    for key in (
        "user",
        "auth_token",
        "session_binding",
        "conversation_id",
        "active_file_id",
        "datasets",
        "messages",
    ):
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.authenticated = False

    if st.query_params.get("session"):
        del st.query_params["session"]


def save_guest_session_to_db(user_id: int) -> None:
    guest_file = st.session_state.get("guest_file")
    if guest_file:
        from database import save_user_file, create_conversation, add_message
        try:
            # 1. Enregistrer le fichier de l'invité dans la base
            file_id = save_user_file(
                user_id=user_id,
                filename=guest_file["filename"],
                file_bytes=guest_file["bytes"],
                row_count=guest_file["row_count"],
                col_count=guest_file["col_count"],
                columns=guest_file["columns"],
                rag_profile=guest_file["rag_profile"],
                cleaning_report=guest_file["cleaning_report"],
            )
            st.session_state.active_file_id = file_id
            
            # 2. Enregistrer la conversation et les messages en base
            if st.session_state.get("messages"):
                guest_prompt = "Analyse"
                for msg in st.session_state.messages:
                    if msg["role"] == "user":
                        guest_prompt = msg["content"]
                        break
                title = guest_prompt[:60] + ("..." if len(guest_prompt) > 60 else "")
                conv_id = create_conversation(user_id, file_id, title)
                st.session_state.conversation_id = conv_id
                
                for msg in st.session_state.messages:
                    display_df_json = msg["display_df"].to_json(orient="records", force_ascii=False) if msg.get("display_df") is not None else None
                    add_message(
                        conversation_id=conv_id,
                        role=msg["role"],
                        content=msg["content"],
                        display_df_json=display_df_json,
                        code=msg.get("code"),
                        chart_bytes=msg.get("chart_bytes"),
                        pdf_bytes=msg.get("pdf_bytes"),
                    )
            st.session_state.pop("guest_file", None)
        except Exception as exc:
            st.error(f"Erreur lors du transfert de la session invité : {exc}")


def render_auth_tabs(key_prefix: str = "", initial_tab: str | None = None) -> None:
    tab_names = ["Connexion", "Inscription", "Mot de passe oublié", "Réinitialiser"]
    state_key = f"auth_active_tab_{key_prefix}"

    if state_key not in st.session_state:
        st.session_state[state_key] = (
            initial_tab if initial_tab and initial_tab in tab_names else "Connexion"
        )

    tab_cols = st.columns([1, 1, 1.35, 1])
    for col, name in zip(tab_cols, tab_names):
        with col:
            is_active = st.session_state[state_key] == name
            if st.button(
                name,
                key=f"auth_tab_select_{key_prefix}_{name}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state[state_key] = name
                st.rerun()

    active = st.session_state[state_key]

    if active == "Connexion":
        with st.form(f"login_form_{key_prefix}"):
            email = st.text_input("Email", key=f"login_email_{key_prefix}")
            password = st.text_input("Mot de passe", type="password", key=f"login_pwd_{key_prefix}")
            if st.form_submit_button("Se connecter", use_container_width=True):
                user = login_user(email, password)
                if user:
                    save_guest_session_to_db(user["id"])
                    establish_user_session(user)
                    st.session_state.show_auth_modal = False
                    st.rerun()
                else:
                    st.error("Email ou mot de passe incorrect.")

    elif active == "Inscription":
        with st.form(f"register_form_{key_prefix}"):
            email = st.text_input("Email", key=f"reg_email_{key_prefix}")
            username = st.text_input("Nom d'utilisateur", key=f"reg_user_{key_prefix}")
            password = st.text_input("Mot de passe", type="password", key=f"reg_pwd_{key_prefix}")
            password2 = st.text_input("Confirmer le mot de passe", type="password", key=f"reg_pwd2_{key_prefix}")
            if st.form_submit_button("Créer un compte", use_container_width=True):
                if password != password2:
                    st.error("Les mots de passe ne correspondent pas.")
                else:
                    ok, msg = register_user(email, username, password)
                    if ok:
                        st.success("Compte créé avec succès ! Connexion automatique...")
                        user = login_user(email, password)
                        if user:
                            save_guest_session_to_db(user["id"])
                            establish_user_session(user)
                            st.session_state.show_auth_modal = False
                            st.rerun()
                    else:
                        st.error(msg)

    elif active == "Mot de passe oublié":
        with st.form(f"forgot_form_{key_prefix}"):
            email = st.text_input("Email du compte", key=f"forgot_email_{key_prefix}")
            if st.form_submit_button("Obtenir un code", use_container_width=True):
                ok, msg = request_password_reset(email)
                st.success(msg) if ok else st.error(msg)

    elif active == "Réinitialiser":
        with st.form(f"reset_form_{key_prefix}"):
            email = st.text_input("Email", key=f"reset_email_{key_prefix}")
            token = st.text_input("Code de réinitialisation", key=f"reset_token_{key_prefix}")
            new_pwd = st.text_input("Nouveau mot de passe", type="password", key=f"reset_new_pwd_{key_prefix}")
            if st.form_submit_button("Réinitialiser", use_container_width=True):
                ok, msg = apply_password_reset(email, token, new_pwd)
                st.success(msg) if ok else st.error(msg)


def render_auth_page() -> None:
    st.markdown(
        """
        <div class="main-header">
            <h1>📊 DataInsight AI</h1>
            <p>Connectez-vous pour analyser vos données e-commerce</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_auth_tabs("page")
