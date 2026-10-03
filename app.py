import json
import os
from datetime import datetime
from io import StringIO

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from auth import ensure_authenticated, init_session_auth, logout, update_user_profile, render_auth_tabs
from dataset_loader import load_dataset_from_bytes
from data_analyst import (
    ask_data_question,
    dataset_overview,
    generate_insights,
    load_dataset,
    select_best_model,
    summarize_for_pdf,
)
from data_cleaner import clean_dataset
from database import (
    add_message,
    create_conversation,
    delete_user_file,
    get_conversation,
    get_messages,
    get_user_file,
    get_user_file_bytes,
    init_db,
    list_conversations,
    list_user_files,
    rename_conversation,
    save_user_file,
    touch_conversation,
)
from pdf_report import build_pdf_report
from rag.rag_engine import analyze_dataset, get_rag_context_from_profile
from ui_styles import (
    CUSTOM_CSS,
    FEATURE_CARDS,
    HERO_HTML,
    NAVBAR_HTML,
    empty_box_html,
    feature_card_html,
    guest_badge_html,
    guest_card_html,
    sidebar_section,
    user_chip_html,
)

load_dotenv()

st.set_page_config(
    page_title="IA DataInsight",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

def init_session_state() -> None:
    defaults = {
        "authenticated": False,
        "user": None,
        "groq_key": os.getenv("GROQ_API_KEY", ""),
        "active_file_id": None,
        "conversation_id": None,
        "datasets": {},
        "rag_profile": {},
        "suggested_questions": [],
        "cleaning_reports": {},
        "messages": [],
        "chart_bytes_list": [],
        "upload_signature": None,
        "last_code": None,
        "renaming_conv_id": None,
        "show_auth_modal": False,
        "show_profile_modal": False,
        "auth_modal_tab": "Connexion",
        "auth_token": None,
        "session_binding": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_user_workspace(user: dict) -> None:
    """Charge le dernier fichier / conversation de l'utilisateur connecté."""
    if st.session_state.get("datasets"):
        return
    files = list_user_files(user["id"])
    if files:
        load_file_into_session(files[0])
        convs = list_conversations(user["id"], files[0]["id"])
        if convs:
            load_conversation_into_session(convs[0]["id"])


def get_rag_context() -> str:
    if st.session_state.rag_profile:
        return get_rag_context_from_profile(st.session_state.rag_profile)
    return ""


def get_active_model() -> str:
    return select_best_model(st.session_state.datasets)


def reset_chat_state() -> None:
    st.session_state.messages = []
    st.session_state.chart_bytes_list = []
    st.session_state.last_code = None
    st.session_state.pdf_download = None


def load_file_into_session(file_record: dict) -> None:
    name = os.path.splitext(file_record["filename"])[0]
    file_bytes = get_user_file_bytes(file_record["id"], file_record["user_id"])
    if not file_bytes:
        raise ValueError("Fichier introuvable en base de données.")
    df = load_dataset_from_bytes(file_bytes, file_record["filename"])
    rag_profile = json.loads(file_record["rag_profile_json"] or "{}")
    cleaning = json.loads(file_record["cleaning_json"] or "{}")

    st.session_state.active_file_id = file_record["id"]
    st.session_state.datasets = {name: df}
    st.session_state.rag_profile = rag_profile
    st.session_state.suggested_questions = rag_profile.get("suggested_questions", [])
    st.session_state.cleaning_reports = {name: cleaning}


def load_conversation_into_session(conversation_id: int) -> None:
    st.session_state.conversation_id = conversation_id
    db_messages = get_messages(conversation_id, include_blobs=True)
    messages = []
    chart_bytes_list: list[bytes] = []
    for row in db_messages:
        display_df = None
        if row.get("display_df_json"):
            try:
                display_df = pd.read_json(StringIO(row["display_df_json"]))
            except Exception:
                display_df = None
        chart_bytes = bytes(row["chart_data"]) if row.get("chart_data") else None
        pdf_bytes = bytes(row["pdf_data"]) if row.get("pdf_data") else None
        if chart_bytes:
            chart_bytes_list.append(chart_bytes)
        messages.append(
            {
                "role": row["role"],
                "content": row["content"],
                "chart_bytes": chart_bytes,
                "display_df": display_df,
                "code": row.get("code"),
                "pdf_bytes": pdf_bytes,
            }
        )
    st.session_state.messages = messages
    st.session_state.chart_bytes_list = chart_bytes_list


def process_upload(uploaded_file, user_id: int | None) -> None:
    try:
        name = os.path.splitext(uploaded_file.name)[0]
        file_bytes = uploaded_file.getvalue()
        raw_df = load_dataset(uploaded_file)
        cleaned_df, report = clean_dataset(raw_df, filename=uploaded_file.name)
        rag_profile = analyze_dataset(cleaned_df, uploaded_file.name)

        if user_id is not None:
            file_id = save_user_file(
                user_id=user_id,
                filename=uploaded_file.name,
                file_bytes=file_bytes,
                row_count=len(cleaned_df),
                col_count=len(cleaned_df.columns),
                columns=list(cleaned_df.columns),
                rag_profile=rag_profile,
                cleaning_report=report.to_dict(),
            )

            conv_id = create_conversation(
                user_id, file_id, f"Analyse — {uploaded_file.name}"
            )

            st.session_state.active_file_id = file_id
            st.session_state.conversation_id = conv_id
            st.session_state.datasets = {name: cleaned_df}
            st.session_state.rag_profile = rag_profile
            st.session_state.suggested_questions = rag_profile.get("suggested_questions", [])
            st.session_state.cleaning_reports = {name: report.to_dict()}
            reset_chat_state()
            st.sidebar.success(f"✅ {uploaded_file.name} enregistré et analysé (RAG)")
        else:
            st.session_state.active_file_id = None
            st.session_state.conversation_id = None
            st.session_state.datasets = {name: cleaned_df}
            st.session_state.rag_profile = rag_profile
            st.session_state.suggested_questions = rag_profile.get("suggested_questions", [])
            st.session_state.cleaning_reports = {name: report.to_dict()}
            st.session_state.guest_file = {
                "filename": uploaded_file.name,
                "bytes": file_bytes,
                "row_count": len(cleaned_df),
                "col_count": len(cleaned_df.columns),
                "columns": list(cleaned_df.columns),
                "rag_profile": rag_profile,
                "cleaning_report": report.to_dict(),
            }
            reset_chat_state()
            st.sidebar.success(f"✅ {uploaded_file.name} analysé temporairement en mémoire.")
    except Exception as exc:
        st.sidebar.error(f"Erreur : {uploaded_file.name} — {exc}")


def handle_user_message(prompt: str) -> None:
    user = st.session_state.user
    user_id = user["id"] if user else None
    conv_id = st.session_state.conversation_id

    if user_id:
        if not conv_id:
            file_id = st.session_state.active_file_id
            title = prompt[:60] + ("..." if len(prompt) > 60 else "")
            conv_id = create_conversation(user_id, file_id, title)
            st.session_state.conversation_id = conv_id
        add_message(conv_id, "user", prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    chart_bytes = None
    display_df = None
    last_code = None
    pdf_bytes = None
    pdf_keywords = ("pdf", "rapport", "document", "report")
    wants_pdf = any(word in prompt.lower() for word in pdf_keywords)

    if wants_pdf:
        with st.spinner("Génération du rapport PDF..."):
            try:
                overview = dataset_overview(st.session_state.datasets)
                summary = summarize_for_pdf(
                    st.session_state.groq_key,
                    st.session_state.datasets,
                    st.session_state.messages,
                    get_active_model(),
                )
                insights = generate_insights(
                    st.session_state.groq_key,
                    st.session_state.datasets,
                    get_active_model(),
                )
                pdf_bytes = build_pdf_report(
                    overview, summary, insights, st.session_state.chart_bytes_list,
                )
                answer = "✅ Rapport PDF prêt !"
            except Exception as exc:
                answer = f"❌ Erreur PDF : {exc}"
                pdf_bytes = None
    else:
        with st.spinner("Llama 3 analyse vos données..."):
            try:
                response = ask_data_question(
                    st.session_state.groq_key,
                    st.session_state.datasets,
                    prompt,
                    get_active_model(),
                    rag_context=get_rag_context(),
                    chat_history=st.session_state.messages[:-1],
                )
                answer = response["answer"]
                chart_bytes = response.get("chart_bytes")
                display_df = response.get("display_df")
                last_code = response.get("code")
                st.session_state.last_code = last_code
                if chart_bytes:
                    st.session_state.chart_bytes_list.append(chart_bytes)
            except Exception as exc:
                answer = f"❌ Erreur : {exc}"

    df_json = display_df.to_json(orient="records", force_ascii=False) if display_df is not None else None

    if user_id and conv_id:
        add_message(
            conv_id,
            "assistant",
            answer,
            display_df_json=df_json,
            code=last_code,
            chart_bytes=chart_bytes,
            pdf_bytes=pdf_bytes,
        )
        touch_conversation(conv_id)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "chart_bytes": chart_bytes,
            "display_df": display_df,
            "code": last_code,
            "pdf_bytes": pdf_bytes,
        }
    )



def render_sidebar() -> None:
    user = st.session_state.user
    with st.sidebar:
        st.markdown(sidebar_section("📤 Télécharger des données"), unsafe_allow_html=True)
        st.markdown(
            '<p style="font-size:0.72rem;color:#94a3b8;margin:-0.25rem 0 0.5rem 0;">CSV, Excel — max. 50 Mo</p>',
            unsafe_allow_html=True,
        )
        if user:
            uploaded = st.file_uploader(
                "Uploader un nouveau fichier",
                type=["csv", "xlsx", "xls", "json", "parquet"],
                help="Nettoyage automatique et analyse intelligente des colonnes",
                key="user_file_uploader",
                label_visibility="collapsed"
            )
            if uploaded:
                sig = (uploaded.name, uploaded.size)
                if sig != st.session_state.upload_signature:
                    st.session_state.upload_signature = sig
                    process_upload(uploaded, user["id"])
                    st.rerun()
        else:
            uploaded = st.file_uploader(
                "Uploader un nouveau fichier",
                type=["csv", "xlsx", "xls", "json", "parquet"],
                help="Analyse temporaire en mémoire",
                key="guest_file_uploader",
                label_visibility="collapsed"
            )
            if uploaded:
                sig = (uploaded.name, uploaded.size)
                if sig != st.session_state.upload_signature:
                    st.session_state.upload_signature = sig
                    process_upload(uploaded, None)
                    st.rerun()

        st.divider()

        st.markdown(
            sidebar_section("📄 Fichiers", "session uniquement" if not user else ""),
            unsafe_allow_html=True,
        )
        if user:
            user_files = list_user_files(user["id"])
            if user_files:
                file_options = {f"{f['filename']} ({f['row_count']:,} lignes)": f["id"] for f in user_files}
                selected_label = st.selectbox(
                    "Sélectionner un fichier",
                    options=list(file_options.keys()),
                    index=0 if st.session_state.active_file_id is None else next(
                        (i for i, (_, fid) in enumerate(file_options.items()) if fid == st.session_state.active_file_id),
                        0,
                    ),
                    label_visibility="collapsed"
                )
                selected_id = file_options[selected_label]
                if selected_id != st.session_state.active_file_id:
                    record = get_user_file(selected_id, user["id"])
                    if record:
                        load_file_into_session(record)
                        convs = list_conversations(user["id"], selected_id)
                        if convs:
                            load_conversation_into_session(convs[0]["id"])
                        else:
                            reset_chat_state()
                            st.session_state.conversation_id = create_conversation(
                                user["id"], selected_id, f"Analyse — {record['filename']}"
                            )
                        st.rerun()

                active = get_user_file(st.session_state.active_file_id, user["id"])
                if active and st.button("🗑️ Supprimer ce fichier", use_container_width=True):
                    delete_user_file(active["id"], user["id"])
                    st.session_state.active_file_id = None
                    st.session_state.datasets = {}
                    reset_chat_state()
                    st.rerun()
            else:
                st.markdown(empty_box_html("Aucun fichier pour l'instant. Téléchargez-en un pour commencer."), unsafe_allow_html=True)
        else:
            guest_file = st.session_state.get("guest_file")
            if guest_file:
                st.markdown(
                    f'<div style="font-size: 0.8rem; color: #0f172a; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.8rem; display: flex; justify-content: space-between; align-items: center;"><span>📄 {guest_file["filename"]}</span></div>',
                    unsafe_allow_html=True
                )
                if st.button("🗑️ Supprimer ce fichier", use_container_width=True):
                    st.session_state.guest_file = None
                    st.session_state.datasets = {}
                    st.session_state.rag_profile = {}
                    st.session_state.suggested_questions = []
                    reset_chat_state()
                    st.rerun()
            else:
                st.markdown(empty_box_html("Aucun fichier pour l'instant. Téléchargez-en un pour commencer."), unsafe_allow_html=True)

        if st.session_state.rag_profile:
            with st.expander("🔍 Colonnes détectées", expanded=False):
                mappings = st.session_state.rag_profile.get("column_mappings", [])
                for m in mappings:
                    st.caption(f"**{m['column']}** → {m['label']} ({m['role']})")
                if not mappings:
                    st.caption("Colonnes analysées automatiquement.")

        st.divider()

        st.markdown(sidebar_section("💬 Conversations"), unsafe_allow_html=True)
        if user:
            convs = list_conversations(
                user["id"],
                st.session_state.active_file_id,
            )
            if convs:
                for conv in convs[:8]:
                    label = f"{conv['title'][:32]} — {conv['updated_at'][:10]}"
                    col_btn, col_edit = st.columns([5, 1])
                    with col_btn:
                        if st.button(label, key=f"conv_{conv['id']}", use_container_width=True):
                            st.session_state.renaming_conv_id = None
                            load_conversation_into_session(conv["id"])
                            st.rerun()
                    with col_edit:
                        if st.button("✏️", key=f"rename_btn_{conv['id']}", help="Renommer"):
                            st.session_state.renaming_conv_id = conv["id"]
                            st.rerun()

                    # Formulaire de renommage inline
                    if st.session_state.renaming_conv_id == conv["id"]:
                        new_title = st.text_input(
                            "Nouveau nom",
                            value=conv["title"],
                            key=f"rename_input_{conv['id']}",
                            label_visibility="collapsed",
                        )
                        col_ok, col_cancel = st.columns(2)
                        with col_ok:
                            if st.button("✅ OK", key=f"rename_ok_{conv['id']}", use_container_width=True):
                                if new_title.strip():
                                    rename_conversation(conv["id"], user["id"], new_title)
                                st.session_state.renaming_conv_id = None
                                st.rerun()
                        with col_cancel:
                            if st.button("✖ Annuler", key=f"rename_cancel_{conv['id']}", use_container_width=True):
                                st.session_state.renaming_conv_id = None
                                st.rerun()

                if st.button("➕ Nouvelle conversation", use_container_width=True):
                    reset_chat_state()
                    st.session_state.renaming_conv_id = None
                    st.session_state.conversation_id = create_conversation(
                        user["id"],
                        st.session_state.active_file_id,
                        f"Session {datetime.now().strftime('%d/%m %H:%M')}",
                    )
                    st.rerun()
            else:
                st.caption("Aucune conversation pour ce fichier.")
        else:
            st.markdown(
                empty_box_html("Connectez-vous pour sauvegarder et consulter vos conversations."),
                unsafe_allow_html=True,
            )

        if st.session_state.suggested_questions:
            st.divider()
            st.markdown(sidebar_section("💡 Questions suggérées"), unsafe_allow_html=True)
            for q in st.session_state.suggested_questions[:6]:
                if st.button(q, key=f"rag_q_{hash(q)}", use_container_width=True):
                    st.session_state.pending_prompt = q

        st.divider()

        if not user:
            st.markdown(guest_card_html(), unsafe_allow_html=True)
            if st.button("Connectez-vous pour déverrouiller", use_container_width=True, type="primary"):
                open_auth_modal("Connexion")
                st.rerun()


def open_auth_modal(tab: str = "Connexion") -> None:
    """Ouvre le modal d'authentification sur l'onglet demandé."""
    st.session_state.auth_modal_tab = tab
    st.session_state.auth_active_tab_modal = tab
    st.session_state.show_auth_modal = True


def render_topbar() -> None:
    """Barre supérieure : branding à gauche, auth ou profil à droite."""
    user = st.session_state.user
    col_brand, col_actions = st.columns([4, 6])
    with col_brand:
        st.markdown(NAVBAR_HTML, unsafe_allow_html=True)
    with col_actions:
        if user:
            chip_col, profile_col, logout_col = st.columns([2.5, 1.4, 1.3])
            with chip_col:
                st.markdown(user_chip_html(user["username"]), unsafe_allow_html=True)
            with profile_col:
                if st.button("Mon profil", key="top_profile_btn"):
                    st.session_state.show_profile_modal = True
                    st.rerun()
            with logout_col:
                if st.button("Déconnexion", key="top_logout_btn"):
                    logout()
                    st.rerun()
        else:
            badge_col, login_col, signup_col = st.columns([2.2, 1.5, 1.8])
            with badge_col:
                st.markdown(guest_badge_html(), unsafe_allow_html=True)
            with login_col:
                if st.button("Se connecter", key="top_login_btn"):
                    open_auth_modal("Connexion")
                    st.rerun()
            with signup_col:
                if st.button("Créer un compte", key="top_signup_btn", type="primary"):
                    open_auth_modal("Inscription")
                    st.rerun()


def render_profile_modal() -> None:
    """Modal de modification du profil (depuis la barre supérieure)."""
    user = st.session_state.user
    if not user:
        st.session_state.show_profile_modal = False
        st.rerun()
        return

    with st.container(border=True):
        st.markdown('<div class="auth-modal-title">Modifier mon profil</div>', unsafe_allow_html=True)
        with st.form("profile_form_top", clear_on_submit=False):
            new_username = st.text_input("Nom d'utilisateur", value=user["username"])
            new_email = st.text_input("Email", value=user["email"])
            new_password = st.text_input(
                "Nouveau mot de passe (optionnel)",
                type="password",
                help="Laissez vide pour conserver l'ancien",
            )
            if st.form_submit_button("Sauvegarder", use_container_width=True):
                success, msg = update_user_profile(user["id"], new_email, new_username, new_password)
                if success:
                    st.session_state.user["username"] = new_username.strip()
                    st.session_state.user["email"] = new_email.strip()
                    st.session_state.show_profile_modal = False
                    st.success("Profil mis à jour !")
                    st.rerun()
                else:
                    st.error(msg)
        if st.button("Fermer", use_container_width=True, key="close_profile_modal"):
            st.session_state.show_profile_modal = False
            st.rerun()


def render_header() -> None:
    """En-tête masqué — le hero est dans render_chat."""
    return


def get_guest_questions_count() -> int:
    return sum(1 for m in st.session_state.messages if m["role"] == "user")


def render_chat() -> None:
    if not st.session_state.groq_key:
        st.warning("Clé API Groq manquante dans `.env`")
        return

    if not st.session_state.datasets:
        st.markdown(HERO_HTML, unsafe_allow_html=True)

        uploaded_main = st.file_uploader(
            "Glissez-déposez votre fichier ici",
            type=["csv", "xlsx", "xls", "json", "parquet"],
            key="main_file_uploader",
            label_visibility="collapsed",
        )
        st.markdown('<p class="upload-hint">CSV, Excel, JSON ou Parquet</p>', unsafe_allow_html=True)
        if uploaded_main:
            sig = (uploaded_main.name, uploaded_main.size)
            if sig != st.session_state.upload_signature:
                st.session_state.upload_signature = sig
                user = st.session_state.user
                process_upload(uploaded_main, user["id"] if user else None)
                st.rerun()

        col_f1, col_f2, col_f3 = st.columns(3)
        for col, (icon, title, desc) in zip([col_f1, col_f2, col_f3], FEATURE_CARDS):
            with col:
                st.markdown(feature_card_html(icon, title, desc), unsafe_allow_html=True)
        return

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["content"] and str(message["content"]).strip():
                st.markdown(message["content"])
            if message.get("display_df") is not None and not message["display_df"].empty:
                st.dataframe(message["display_df"], use_container_width=True, hide_index=True)
            chart_bytes = message.get("chart_bytes")
            if chart_bytes:
                st.image(chart_bytes, use_container_width=True)
            if message.get("code"):
                with st.expander("🔍 Voir le code de calcul exécuté"):
                    st.code(message["code"], language="python")
            pdf_bytes = message.get("pdf_bytes")
            if pdf_bytes:
                st.download_button(
                    "⬇️ Télécharger le Rapport PDF",
                    data=pdf_bytes,
                    file_name="rapport_datainsight.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"pdf_dl_{hash(pdf_bytes) % 10**8}",
                )

    # Limite pour les utilisateurs invités
    guest_limit_reached = False
    if not st.session_state.user:
        if get_guest_questions_count() >= 3:
            guest_limit_reached = True

    if guest_limit_reached:
        st.warning("⚠️ Vous avez atteint la limite de 3 questions en mode invité.")
        st.info("Pour sauvegarder vos données et continuer la conversation, veuillez vous connecter ou créer un compte.")
        render_auth_tabs("guest_limit")
    else:
        pending = st.session_state.pop("pending_prompt", None)
        user_input = st.chat_input("Posez votre question sur vos données...")
        prompt = pending or user_input
        if prompt:
            handle_user_message(prompt)
            st.rerun()


def main() -> None:
    init_db()
    init_session_state()
    init_session_auth()
    ensure_authenticated()
    if st.session_state.get("authenticated") and st.session_state.get("user"):
        load_user_workspace(st.session_state.user)
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    render_topbar()

    if st.session_state.get("show_auth_modal"):
        with st.container(border=True):
            st.markdown(
                '<div class="auth-modal-title">Espace Connexion & Inscription</div>',
                unsafe_allow_html=True,
            )
            render_auth_tabs("modal")
            if st.button("Fermer", use_container_width=True):
                st.session_state.show_auth_modal = False
                st.session_state.pop("auth_active_tab_modal", None)
                st.session_state.auth_modal_tab = "Connexion"
                st.rerun()
        return

    if st.session_state.get("show_profile_modal"):
        render_profile_modal()
        return

    render_sidebar()
    render_header()
    render_chat()


if __name__ == "__main__":
    main()
