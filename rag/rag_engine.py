"""RAG e-commerce : analyse des en-têtes et suggestions de questions."""

from __future__ import annotations

import json
import os
import re
from difflib import SequenceMatcher
from typing import Any

import pandas as pd

KB_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.json")


def _load_knowledge_base() -> dict:
    with open(KB_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def match_column_to_semantic(column: str, kb: dict) -> dict | None:
    col_norm = _normalize(column)
    best_match = None
    best_score = 0.0

    for sem_type in kb["semantic_types"]:
        for pattern in sem_type["patterns"]:
            pat_norm = _normalize(pattern)
            if pat_norm in col_norm or col_norm in pat_norm:
                score = 0.95
            else:
                score = _similarity(column, pattern)
            if score > best_score and score >= 0.55:
                best_score = score
                best_match = {
                    "column": column,
                    "semantic_id": sem_type["id"],
                    "label": sem_type["label"],
                    "role": sem_type["role"],
                    "confidence": round(score, 2),
                }
    return best_match


def analyze_dataset(df: pd.DataFrame, filename: str = "dataset") -> dict[str, Any]:
    """Analyse RAG complète d'un dataset uploadé."""
    kb = _load_knowledge_base()
    column_mappings: list[dict] = []
    detected_types: dict[str, list[str]] = {
        "dimensions": [],
        "metrics": [],
        "temporal": [],
        "identifiers": [],
    }

    for col in df.columns:
        match = match_column_to_semantic(str(col), kb)
        if match:
            column_mappings.append(match)
            role = match["role"]
            if role == "dimension":
                detected_types["dimensions"].append(col)
            elif role == "metric":
                detected_types["metrics"].append(col)
            elif role == "temporal":
                detected_types["temporal"].append(col)
            elif role == "identifier":
                detected_types["identifiers"].append(col)
        else:
            if pd.api.types.is_numeric_dtype(df[col]):
                detected_types["metrics"].append(col)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                detected_types["temporal"].append(col)
            else:
                detected_types["dimensions"].append(col)

    suggested_questions = build_suggested_questions(column_mappings, kb)
    rag_context = build_rag_context(filename, df, column_mappings, detected_types, suggested_questions)

    return {
        "filename": filename,
        "columns": list(df.columns),
        "row_count": len(df),
        "column_mappings": column_mappings,
        "detected_types": detected_types,
        "suggested_questions": suggested_questions,
        "rag_context": rag_context,
    }


def build_suggested_questions(mappings: list[dict], kb: dict) -> list[str]:
    questions: list[str] = list(kb.get("generic_questions", []))
    seen_semantic: set[str] = set()

    for mapping in mappings:
        sem_id = mapping["semantic_id"]
        if sem_id in seen_semantic:
            continue
        seen_semantic.add(sem_id)
        for sem_type in kb["semantic_types"]:
            if sem_type["id"] == sem_id:
                for q in sem_type.get("questions", []):
                    personalized = q.replace("catégorie", mapping["column"]).replace(
                        "région", mapping["column"]
                    )
                    if personalized not in questions:
                        questions.append(personalized)
                break

    if len(questions) < 6:
        for mapping in mappings:
            col = mapping["column"]
            if mapping["role"] == "metric":
                questions.append(f"Quel est le total de {col} ?")
            elif mapping["role"] == "dimension":
                questions.append(f"Quelle est la répartition par {col} ?")
            if len(questions) >= 8:
                break

    return questions[:10]


def build_rag_context(
    filename: str,
    df: pd.DataFrame,
    mappings: list[dict],
    detected_types: dict,
    suggested_questions: list[str],
) -> str:
    """Contexte RAG injecté dans le prompt LLM."""
    mapping_lines = [
        f"  - '{m['column']}' → {m['label']} ({m['role']}, confiance {m['confidence']})"
        for m in mappings
    ] or ["  - Aucune correspondance sémantique forte"]

    unmapped = [c for c in df.columns if c not in {m["column"] for m in mappings}]
    if unmapped:
        mapping_lines.append(f"  - Colonnes non mappées : {unmapped}")

    questions_block = "\n".join(f"  - {q}" for q in suggested_questions[:8])

    return f"""
=== CONTEXTE RAG E-COMMERCE ===
Fichier : {filename} | Lignes : {len(df):,}

Colonnes détectées et leur sémantique :
{chr(10).join(mapping_lines)}

Colonnes recommandées pour agrégations (dimensions) : {detected_types.get('dimensions', [])}
Colonnes recommandées pour calculs (métriques) : {detected_types.get('metrics', [])}
Colonnes temporelles : {detected_types.get('temporal', [])}
Colonnes identifiants (NE PAS utiliser pour groupby) : {detected_types.get('identifiers', [])}

Questions pertinentes pour CE dataset :
{questions_block}

Règles RAG :
- Utilise les colonnes mappées ci-dessus pour répondre aux questions
- Pour "par catégorie/région/sexe/livraison", utilise la colonne dimension correspondante
- Pour totaux et moyennes, utilise les colonnes métriques
- Si Quantity et UnitPrice existent sans Amount, calcule ventes = Quantity * UnitPrice
=== FIN CONTEXTE RAG ===
"""


def get_suggested_questions_from_profile(rag_profile: dict) -> list[str]:
    return rag_profile.get("suggested_questions", [])


def get_rag_context_from_profile(rag_profile: dict) -> str:
    return rag_profile.get("rag_context", "")
