"""
DataInsight AI — FastAPI REST backend
Exécuter avec : uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import json
import os
from io import BytesIO
from typing import Any
from uuid import uuid4

import bcrypt
import pandas as pd
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

# ── Modules internes ──────────────────────────────────────────────────────────
from database import (
    add_message,
    create_conversation,
    create_session,
    create_user,
    delete_user_file,
    get_conversation,
    get_message_attachment,
    get_messages,
    get_user_by_email,
    get_user_file,
    get_user_file_bytes,
    init_db,
    list_conversations,
    list_user_files,
    rename_conversation,
    revoke_session,
    save_user_file,
    touch_conversation,
    update_user_profile_db,
    verify_session,
)
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
from pdf_report import build_pdf_report
from rag.rag_engine import analyze_dataset, get_rag_context_from_profile

# ── Initialisation ────────────────────────────────────────────────────────────
load_dotenv()
init_db()

app = FastAPI(title="DataInsight AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token manquant")


def _get_binding(request: Request) -> str:
    binding = request.headers.get("X-Session-Binding", "").strip()
    if not binding:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide")
    return binding


def _get_current_user(request: Request) -> dict[str, Any]:
    user = verify_session(_get_token(request), _get_binding(request))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée")
    return user


def _optional_user(request: Request) -> dict[str, Any] | None:
    auth = request.headers.get("Authorization", "")
    binding = request.headers.get("X-Session-Binding", "").strip()
    if auth.startswith("Bearer ") and binding:
        return verify_session(auth[7:], binding)
    return None


GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# ── Schémas Pydantic ──────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UpdateProfileRequest(BaseModel):
    email: str
    username: str
    password: str | None = None


class CreateConversationRequest(BaseModel):
    file_id: int | None = None
    title: str = "Nouvelle conversation"


class RenameConversationRequest(BaseModel):
    title: str


class AskRequest(BaseModel):
    conversation_id: int | None = None
    file_id: int | None = None
    prompt: str
    # Pour les invités : données de fichier temporaire en mémoire
    guest_file_id: str | None = None


# ── Stockage temporaire des datasets invités (en mémoire) ────────────────────
# Clé : guest_file_id (UUID), Valeur : dict avec df, rag_profile, etc.
_guest_datasets: dict[str, dict] = {}


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/auth/register", status_code=201)
def register(body: RegisterRequest):
    if len(body.password) < 6:
        raise HTTPException(400, "Le mot de passe doit contenir au moins 6 caractères.")
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user_id = create_user(body.email, body.username, hashed)
    if user_id is None:
        raise HTTPException(409, "Email ou nom d'utilisateur déjà utilisé.")
    token, binding = create_session(user_id)
    return {
        "token": token,
        "binding": binding,
        "user": {"id": user_id, "email": body.email, "username": body.username},
    }


@app.post("/api/auth/login")
def login(body: LoginRequest):
    user = get_user_by_email(body.email)
    if not user:
        raise HTTPException(401, "Email ou mot de passe incorrect.")
    if not bcrypt.checkpw(body.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Email ou mot de passe incorrect.")
    token, binding = create_session(user["id"])
    return {
        "token": token,
        "binding": binding,
        "user": {"id": user["id"], "email": user["email"], "username": user["username"]},
    }


@app.post("/api/auth/logout")
def logout(request: Request):
    token = _get_token(request)
    revoke_session(token)
    return {"ok": True}


@app.put("/api/auth/profile")
def update_profile(body: UpdateProfileRequest, request: Request):
    user = _get_current_user(request)
    new_hash = None
    if body.password:
        new_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    ok, msg = update_user_profile_db(user["id"], body.email, body.username, new_hash)
    if not ok:
        raise HTTPException(400, msg)
    return {"ok": True, "message": msg}


# ─────────────────────────────────────────────────────────────────────────────
# FILES
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/files/upload", status_code=201)
async def upload_file(request: Request, file: UploadFile = File(...)):
    user = _optional_user(request)
    content = await file.read()

    # Charger + nettoyer
    try:
        file_like = BytesIO(content)
        file_like.name = file.filename  # type: ignore[attr-defined]
        raw_df = load_dataset(file_like)
        cleaned_df, report = clean_dataset(raw_df, filename=file.filename)
        rag_profile = analyze_dataset(cleaned_df, file.filename)
    except Exception as exc:
        raise HTTPException(422, f"Impossible de lire le fichier : {exc}")

    if user:
        # Utilisateur connecté → persister
        file_id = save_user_file(
            user_id=user["id"],
            filename=file.filename,
            file_bytes=content,
            row_count=len(cleaned_df),
            col_count=len(cleaned_df.columns),
            columns=list(cleaned_df.columns),
            rag_profile=rag_profile,
            cleaning_report=report.to_dict() if hasattr(report, "to_dict") else report,
        )
        conv_id = create_conversation(user["id"], file_id, f"Analyse — {file.filename}")
        return {
            "file_id": file_id,
            "conversation_id": conv_id,
            "filename": file.filename,
            "row_count": len(cleaned_df),
            "col_count": len(cleaned_df.columns),
            "columns": list(cleaned_df.columns),
            "rag_profile": rag_profile,
            "suggested_questions": rag_profile.get("suggested_questions", []),
            "cleaning_report": report.to_dict() if hasattr(report, "to_dict") else report,
            "guest": False,
        }
    else:
        # Invité → en mémoire
        guest_id = uuid4().hex
        _guest_datasets[guest_id] = {
            "df": cleaned_df,
            "filename": file.filename,
            "rag_profile": rag_profile,
            "cleaning_report": report.to_dict() if hasattr(report, "to_dict") else report,
        }
        return {
            "guest_file_id": guest_id,
            "filename": file.filename,
            "row_count": len(cleaned_df),
            "col_count": len(cleaned_df.columns),
            "columns": list(cleaned_df.columns),
            "rag_profile": rag_profile,
            "suggested_questions": rag_profile.get("suggested_questions", []),
            "cleaning_report": report.to_dict() if hasattr(report, "to_dict") else report,
            "guest": True,
        }


@app.get("/api/files")
def list_files(request: Request):
    user = _get_current_user(request)
    files = list_user_files(user["id"])
    # Ne pas exposer stored_path
    return [
        {
            "id": f["id"],
            "filename": f["filename"],
            "row_count": f["row_count"],
            "col_count": f["col_count"],
            "columns": json.loads(f["columns_json"] or "[]"),
            "rag_profile": json.loads(f["rag_profile_json"] or "{}"),
            "suggested_questions": json.loads(f["rag_profile_json"] or "{}").get("suggested_questions", []),
            "uploaded_at": f["uploaded_at"],
        }
        for f in files
    ]


@app.delete("/api/files/{file_id}", status_code=204)
def delete_file(file_id: int, request: Request):
    user = _get_current_user(request)
    ok = delete_user_file(file_id, user["id"])
    if not ok:
        raise HTTPException(404, "Fichier introuvable.")


# ─────────────────────────────────────────────────────────────────────────────
# CONVERSATIONS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/conversations")
def list_convs(request: Request, file_id: int | None = None):
    user = _get_current_user(request)
    convs = list_conversations(user["id"], file_id)
    return convs


@app.post("/api/conversations", status_code=201)
def create_conv(body: CreateConversationRequest, request: Request):
    user = _get_current_user(request)
    conv_id = create_conversation(user["id"], body.file_id, body.title)
    return {"id": conv_id, "title": body.title, "file_id": body.file_id}


@app.patch("/api/conversations/{conv_id}")
def rename_conv(conv_id: int, body: RenameConversationRequest, request: Request):
    user = _get_current_user(request)
    rename_conversation(conv_id, user["id"], body.title)
    return {"ok": True}


@app.get("/api/conversations/{conv_id}/messages")
def get_conv_messages(conv_id: int, request: Request):
    user = _get_current_user(request)
    # Vérifier que la conversation appartient à l'utilisateur
    conv = get_conversation(conv_id, user["id"])
    if not conv:
        raise HTTPException(404, "Conversation introuvable.")
    msgs = get_messages(conv_id)
    return [
        {
            "id": m["id"],
            "role": m["role"],
            "content": m["content"],
            "has_chart": m.get("has_chart", False),
            "chart_url": f"/api/messages/{m['id']}/chart" if m.get("has_chart") else None,
            "display_df": json.loads(m["display_df_json"]) if m.get("display_df_json") else None,
            "code": m.get("code"),
            "has_pdf": m.get("has_pdf", False),
            "pdf_url": f"/api/messages/{m['id']}/pdf" if m.get("has_pdf") else None,
            "created_at": m["created_at"],
        }
        for m in msgs
    ]


# ─────────────────────────────────────────────────────────────────────────────
# CHAT — Question / Réponse LLM
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/chat/ask")
async def ask(body: AskRequest, request: Request):
    user = _optional_user(request)

    # ── Résoudre le dataset ──────────────────────────────────────────────────
    datasets: dict[str, pd.DataFrame] = {}
    rag_profile: dict = {}
    conv_id: int | None = body.conversation_id

    if user and body.file_id:
        record = get_user_file(body.file_id, user["id"])
        if not record:
            raise HTTPException(404, "Fichier introuvable.")
        name = os.path.splitext(record["filename"])[0]
        file_bytes = get_user_file_bytes(body.file_id, user["id"])
        if not file_bytes:
            raise HTTPException(404, "Contenu du fichier introuvable.")
        datasets = {name: load_dataset_from_bytes(file_bytes, record["filename"])}
        rag_profile = json.loads(record["rag_profile_json"] or "{}")

        # Créer la conversation si besoin
        if not conv_id:
            title = body.prompt[:60] + ("..." if len(body.prompt) > 60 else "")
            conv_id = create_conversation(user["id"], body.file_id, title)

        # Enregistrer le message user
        add_message(conv_id, "user", body.prompt)

    elif body.guest_file_id and body.guest_file_id in _guest_datasets:
        guest = _guest_datasets[body.guest_file_id]
        name = os.path.splitext(guest["filename"])[0]
        datasets = {name: guest["df"]}
        rag_profile = guest["rag_profile"]
    else:
        raise HTTPException(400, "Aucun dataset actif. Uploadez un fichier d'abord.")

    if not datasets:
        raise HTTPException(400, "Dataset vide ou non chargé.")

    # ── Construire le contexte RAG ────────────────────────────────────────────
    rag_context = get_rag_context_from_profile(rag_profile) if rag_profile else ""
    model = select_best_model(datasets)

    # ── Historique du chat (pour le contexte) ─────────────────────────────────
    chat_history: list[dict] = []
    if conv_id and user:
        prev = get_messages(conv_id)
        chat_history = [{"role": m["role"], "content": m["content"]} for m in prev[:-1]]

    # ── Vérifier si PDF demandé ───────────────────────────────────────────────
    pdf_keywords = ("pdf", "rapport", "document", "report")
    wants_pdf = any(kw in body.prompt.lower() for kw in pdf_keywords)

    chart_url: str | None = None
    display_df: list | None = None
    code: str | None = None
    pdf_url: str | None = None
    answer: str = ""
    chart_bytes: bytes | None = None
    pdf_bytes: bytes | None = None
    message_id: int | None = None

    prior_charts: list[bytes] = []
    if conv_id and user:
        for prev_msg in get_messages(conv_id, include_blobs=True):
            if prev_msg.get("chart_data"):
                prior_charts.append(bytes(prev_msg["chart_data"]))

    if wants_pdf:
        try:
            overview = dataset_overview(datasets)
            summary = summarize_for_pdf(GROQ_KEY, datasets, chat_history, model)
            insights = generate_insights(GROQ_KEY, datasets, model)
            pdf_bytes = build_pdf_report(overview, summary, insights, prior_charts)
            answer = "✅ Votre rapport PDF est prêt."
        except Exception as exc:
            answer = f"❌ Erreur lors de la génération du PDF : {exc}"
    else:
        try:
            response = ask_data_question(
                GROQ_KEY,
                datasets,
                body.prompt,
                model,
                rag_context=rag_context,
                chat_history=chat_history,
            )
            answer = response.get("answer", "")
            chart_bytes = response.get("chart_bytes")
            df_result = response.get("display_df")
            code = response.get("code")

            if df_result is not None:
                try:
                    display_df = json.loads(df_result.to_json(orient="records", force_ascii=False))
                except Exception:
                    display_df = None
        except Exception as exc:
            answer = f"❌ Erreur : {exc}"

    df_json_str = json.dumps(display_df, ensure_ascii=False) if display_df else None

    if user and conv_id:
        message_id = add_message(
            conv_id,
            "assistant",
            answer,
            display_df_json=df_json_str,
            code=code,
            chart_bytes=chart_bytes,
            pdf_bytes=pdf_bytes,
        )
        touch_conversation(conv_id)
        if chart_bytes:
            chart_url = f"/api/messages/{message_id}/chart"
        if pdf_bytes:
            pdf_url = f"/api/messages/{message_id}/pdf"

    return {
        "conversation_id": conv_id,
        "message_id": message_id,
        "answer": answer,
        "chart_url": chart_url,
        "display_df": display_df,
        "code": code,
        "pdf_url": pdf_url,
    }


@app.get("/api/messages/{message_id}/chart")
def serve_message_chart(message_id: int, request: Request):
    user = _get_current_user(request)
    data = get_message_attachment(message_id, user["id"], "chart")
    if not data:
        raise HTTPException(404, "Graphique introuvable.")
    return Response(content=data, media_type="image/png")


@app.get("/api/messages/{message_id}/pdf")
def serve_message_pdf(message_id: int, request: Request):
    user = _get_current_user(request)
    data = get_message_attachment(message_id, user["id"], "pdf")
    if not data:
        raise HTTPException(404, "PDF introuvable.")
    return Response(content=data, media_type="application/pdf")


# ─────────────────────────────────────────────────────────────────────────────
# TRANSFER — Transférer dataset invité vers compte utilisateur
# ─────────────────────────────────────────────────────────────────────────────

class TransferGuestRequest(BaseModel):
    guest_file_id: str
    guest_messages: list[dict] = []


@app.post("/api/guest/transfer", status_code=201)
def transfer_guest(body: TransferGuestRequest, request: Request):
    """Transfère un dataset invité vers le compte de l'utilisateur authentifié."""
    user = _get_current_user(request)
    guest = _guest_datasets.get(body.guest_file_id)
    if not guest:
        raise HTTPException(404, "Session invité introuvable ou expirée.")

    df: pd.DataFrame = guest["df"]
    filename: str = guest["filename"]
    rag_profile: dict = guest["rag_profile"]
    cleaning_report = guest.get("cleaning_report", {})

    buf = BytesIO()
    if filename.endswith(".csv"):
        df.to_csv(buf, index=False)
    else:
        df.to_excel(buf, index=False)
    file_bytes = buf.getvalue()

    file_id = save_user_file(
        user_id=user["id"],
        filename=filename,
        file_bytes=file_bytes,
        row_count=len(df),
        col_count=len(df.columns),
        columns=list(df.columns),
        rag_profile=rag_profile,
        cleaning_report=cleaning_report,
    )
    conv_id = create_conversation(user["id"], file_id, f"Analyse — {filename}")

    # Migrer les messages invités dans la vraie conversation
    for msg in body.guest_messages:
        role = msg.get("role", "user")
        content = msg.get("text") or msg.get("content", "")
        if content:
            add_message(conv_id, role, content)

    # Nettoyer la session invité
    del _guest_datasets[body.guest_file_id]

    return {
        "file_id": file_id,
        "conversation_id": conv_id,
        "filename": filename,
        "row_count": len(df),
        "col_count": len(df.columns),
        "rag_profile": rag_profile,
        "suggested_questions": rag_profile.get("suggested_questions", []),
    }
