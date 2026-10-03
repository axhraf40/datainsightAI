"""Moteur d'analyse de données alimenté par Groq / Llama 3."""

from __future__ import annotations

import io
import os
import re
import time
import traceback
import uuid
from contextlib import redirect_stdout
from datetime import datetime
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from groq import Groq

from dataset_loader import load_dataset_from_bytes, load_dataset_from_path

matplotlib.use("Agg")

DEFAULT_MODEL = "llama-3.3-70b-versatile"
MODEL_FAST = "llama-3.1-8b-instant"
MODEL_POWERFUL = "llama-3.3-70b-versatile"

# Chaîne de fallback : si un modèle atteint la limite ou est décommissioné, on essaie le suivant
MODEL_FALLBACK_CHAIN = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "gemma2-9b-it",
]


def groq_chat_with_fallback(
    client: "Groq",
    model: str,
    messages: list[dict],
    temperature: float = 0,
) -> str:
    """Appelle l'API Groq avec fallback automatique sur rate limit (429) ou modèle décommissioné (400)."""
    # Construire la chaîne de modèles : modèle demandé en premier, puis les autres
    chain = [model] + [m for m in MODEL_FALLBACK_CHAIN if m != model]
    last_error = None
    for candidate in chain:
        try:
            response = client.chat.completions.create(
                model=candidate,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            err_str = str(exc)
            # Rate limit (429), quota dépassé, ou modèle décommissioné/invalide → essayer le suivant
            is_rate_limit = "429" in err_str or "rate_limit" in err_str.lower() or "quota" in err_str.lower()
            is_decommissioned = "decommissioned" in err_str.lower() or "model_decommissioned" in err_str.lower()
            is_not_found = "404" in err_str or "model_not_found" in err_str.lower()
            if is_rate_limit or is_decommissioned or is_not_found:
                last_error = exc
                continue
            # Autre erreur → propager immédiatement
            raise
    # Tous les modèles ont échoué
    raise RuntimeError(
        f"Tous les modèles Groq sont temporairement indisponibles. "
        f"Dernière erreur : {last_error}"
    )

CSV_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1", "iso-8859-1", "utf-16")
CSV_SEPARATORS = (",", ";", "\t", "|")

CHART_KEYWORDS = (
    "graphique", "chart", "plot", "visualis", "diagramme", "camembert",
    "pie", "barre", "bar ", "histogramme", "courbe", "line chart",
    "scatter", "nuage", "graphe", "figure",
)

AGG_KEYWORDS = (
    "total", "somme", "sum", "par ", "par catégorie", "par region", "par région",
    "group", "moyenne", "average", "combien", "nombre", "count", "top ",
    "répartition", "repartition", "agreg", "agrég", "ventes par", "sales by",
)

MAX_DISPLAY_ROWS = 20
MAX_TEXT_LENGTH = 1200

COUNT_KEYWORDS = ("combien", "nombre", "count", "how many", "total de lignes", "taille")
TOP_PATTERN = re.compile(r"(?:top\s*(\d+)|(\d+)\s*(?:premier|first|meilleur))", re.IGNORECASE)

CATEGORY_COLUMNS = (
    "category", "catégorie", "categorie", "type", "department", "département",
    "region", "région", "state", "country", "pays", "segment", "class", "classe",
)

AMOUNT_COLUMNS = (
    "amount", "montant", "price", "prix", "total", "revenue", "vente", "sales",
    "quantity", "quantité", "quantite", "profit", "value", "valeur",
)

ID_LIKE_COLUMNS = (
    "description", "name", "nom", "product", "produit", "stockcode", "sku",
    "order id", "order_id", "customerid", "customer id", "invoice",
)

# Colonnes à EXCLURE explicitement comme valeur de ventes
EXCLUDE_VALUE_COLUMNS = (
    "return", "retour", "rate", "taux", "ratio", "discount", "remise",
    "id", "code", "index", "rank", "rang",
)

TIME_GROUPBY_KEYWORDS = (
    "par mois", "by month", "mensuel", "monthly",
    "par semaine", "by week", "hebdomadaire", "weekly",
    "par trimestre", "by quarter", "trimestriel", "quarterly",
    "par année", "par an", "by year", "annuel", "yearly",
    "par jour", "by day", "quotidien", "daily",
)


def select_best_model(datasets: dict[str, pd.DataFrame]) -> str:
    """Sélectionne automatiquement le modèle Llama le plus adapté au dataset."""
    if not datasets:
        return DEFAULT_MODEL

    total_rows = sum(len(df) for df in datasets.values())
    total_cols = max((len(df.columns) for df in datasets.values()), default=0)
    num_files = len(datasets)
    memory_cells = sum(df.size for df in datasets.values())

    # Gros volume, multi-fichiers ou structure complexe → modèle le plus capable
    if (
        total_rows >= 10_000
        or memory_cells >= 500_000
        or num_files >= 2
        or total_cols >= 25
    ):
        return MODEL_POWERFUL

    # Dataset moyen → modèle capable pour analyses fiables
    if total_rows >= 1_000 or total_cols >= 15:
        return MODEL_POWERFUL

    # Petit dataset → modèle rapide
    return MODEL_FAST


SYSTEM_PROMPT = """Tu es un assistant expert en analyse de données e-commerce avec pandas.
L'utilisateur te pose une question sur un ou plusieurs DataFrames déjà chargés en mémoire.

DataFrames disponibles :
{datasets_info}

{rag_context}

Règles strictes :
1. Écris UNIQUEMENT du code Python exécutable, sans markdown ni explication.
2. Les DataFrames sont déjà en mémoire dans le dictionnaire `datasets` (clé = nom du fichier).
   Exemple : datasets["orders"] ou datasets["List of Orders"].
3. Si un seul fichier est chargé, tu peux aussi utiliser `df` (alias du premier dataset).
4. Pour TOUTE réponse (sans exception) :
   - assigne `result = format_for_display(...)` en dernière étape
   - maximum 20 lignes affichées ; jamais df entier, jamais toutes les lignes brutes
5. Sélection des colonnes — Règle ABSOLUE :
   - N'utilise JAMAIS une colonne contenant : "return", "retour", "rate", "taux", "ratio", "discount", "rank" pour calculer des ventes ou un chiffre d'affaires.
   - Pour VENTES / COMMANDES ("ventes", "sales", "combien de ventes", "nombre de commandes", "how many orders/sales") :
     * COMPTER le nombre de lignes ou d'identifiants de commandes uniques (.shape[0] ou .nunique()).
     * JAMAIS faire une somme. Retourne OBLIGATOIREMENT un nombre ENTIER via : result = format_for_display(pd.Series([int(valeur)], index=["total"]))
   - Pour CHIFFRE D'AFFAIRES / MONTANT ("chiffre d'affaires", "revenue", "montant", "amount", "total revenue") :
     * ADDITIONNER la colonne montant/amount/revenue. Retourne un float arrondi à 2 décimales.
   - Si un hint de colonne est fourni en commentaire en tête du code (# COLONNE_DATE=... # COLONNE_VALEUR=...), utilise-le OBLIGATOIREMENT.
6. Groupby temporel ("par mois", "par semaine", "by month", "mensuel", etc.) :
   - Étape 1 : Convertir la colonne date avec `pd.to_datetime(df[col], errors='coerce')` si pas déjà datetime.
   - Étape 2 : Extraire la période selon la granularité demandée :
     * par mois → `df['Période'] = df[col].dt.to_period('M').astype(str)`
     * par trimestre → `df['Période'] = df[col].dt.to_period('Q').astype(str)`
     * par année → `df['Période'] = df[col].dt.year`
     * par semaine → `df['Période'] = df[col].dt.to_period('W').astype(str)`
     * par jour → `df['Période'] = df[col].dt.date`
   - Étape 3 : Grouper par 'Période' et agréger (count pour ventes, sum pour CA). Trier par période croissante.
   - NE JAMAIS utiliser groupby sur la colonne date brute sans extraction de période.
7. Colonnes pour groupby catégoriel : Category, State, Region, Type... JAMAIS Description, StockCode, Order ID, CustomerID
8. TOP N ("top 10", "5 premiers", "best 5") → `.head(N)` puis format_for_display (N max 20)
9. Pour un graphique :
   - utilise matplotlib (`plt`) ou seaborn (`sns`)
   - appelle OBLIGATOIREMENT `save_chart()` à la fin (sans argument) pour enregistrer le graphique
   - assigne result = "Graphique généré avec succès."
   - NE PAS utiliser plt.show()
10. N'utilise QUE : pandas, numpy, matplotlib, seaborn, save_chart, format_for_display, LinearRegression. Pas de lecture de fichiers.
11. Gère les dates et les valeurs manquantes si nécessaire. Filtre par année : `.dt.year == 2011`.
12. Requêtes multi-fichiers : effectue une jointure (`pd.merge`) sur la colonne commune (ex: 'Order ID').
13. LANGUE : Réponds et écris les labels dans la LANGUE de l'utilisateur (FR ou EN).
14. Ne retourne JAMAIS des milliers de lignes brutes : agrège, filtre ou limite avec format_for_display.
15. HORS DOMAINE : Si la question n'est PAS liée à l'analyse de données, l'écommerce, les ventes ou Pandas, écris uniquement : HORS_DOMAINE
16. Analyse Prédictive / No-Code ML : groupe les données par mois, crée un index numérique, entraîne `LinearRegression()`, retourne un DataFrame 'Période'/'Prédiction'.
17. Recommandations : calcule les indicateurs faibles, crée un DataFrame avec 'Alerte / Diagnostic', 'Valeur mesurée', 'Action Recommandée'.
"""


def _fig_to_png_bytes(fig=None) -> bytes:
    buffer = io.BytesIO()
    if fig is not None:
        fig.savefig(buffer, format="png", bbox_inches="tight", dpi=120, facecolor="white")
        plt.close(fig)
    else:
        plt.savefig(buffer, format="png", bbox_inches="tight", dpi=120, facecolor="white")
        plt.close("all")
    buffer.seek(0)
    return buffer.read()


def _make_save_chart(chart_store: list[bytes]):
    """Fonction injectée dans le code généré pour sauvegarder les graphiques en mémoire."""

    def save_chart(fig=None) -> bytes:
        data = _fig_to_png_bytes(fig)
        chart_store.append(data)
        return data

    return save_chart


def _capture_open_figures() -> bytes | None:
    """Sauvegarde les figures matplotlib encore ouvertes après exécution."""
    fignums = plt.get_fignums()
    if not fignums:
        return None
    fig = plt.figure(fignums[-1])
    return _fig_to_png_bytes(fig)


def _is_aggregation_request(question: str) -> bool:
    lower = question.lower()
    return any(keyword in lower for keyword in AGG_KEYWORDS)


def _is_time_groupby_request(question: str) -> bool:
    lower = question.lower()
    return any(keyword in lower for keyword in TIME_GROUPBY_KEYWORDS)


def _find_date_column(frame: pd.DataFrame) -> str | None:
    """Trouve la première colonne date dans un DataFrame."""
    # 1. Colonnes déjà au format datetime
    for col in frame.columns:
        if pd.api.types.is_datetime64_any_dtype(frame[col]):
            return str(col)
    # 2. Colonnes avec 'date', 'time', 'order' dans le nom
    date_hints = ("date", "time", "order date", "invoice date", "purchase", "created")
    for col in frame.columns:
        col_lower = str(col).lower()
        if any(h in col_lower for h in date_hints):
            return str(col)
    return None


def _find_sales_column(frame: pd.DataFrame, question: str) -> str | None:
    """Trouve la colonne numérique la plus pertinente selon la question."""
    q_lower = question.lower()
    # Mots-clés pour chiffre d'affaires (SOMME)
    ca_hints = ("chiffre d'affaires", "revenue", "montant", "amount", "total revenue",
                "total amount", "sales amount", "prix", "price")
    # Mots-clés pour ventes/commandes (COMPTAGE)
    count_hints = ("ventes", "sales", "commandes", "orders", "nombre de", "how many")
    wants_ca = any(h in q_lower for h in ca_hints)
    wants_count = any(h in q_lower for h in count_hints) and not wants_ca
    
    # Colonnes numériques candidates (exclure les colonnes parasites)
    numeric_cols = [
        col for col in frame.columns
        if pd.api.types.is_numeric_dtype(frame[col])
        and not any(excl in str(col).lower() for excl in EXCLUDE_VALUE_COLUMNS)
    ]
    if not numeric_cols:
        return None
    
    if wants_ca:
        # Priorité : colonnes contenant 'amount', 'revenue', 'sales', 'montant', 'price'
        for hint in ("amount", "revenue", "sales", "montant", "price", "total", "value"):
            for col in numeric_cols:
                if hint in str(col).lower():
                    return str(col)
    
    if wants_count or not wants_ca:
        # Pour le comptage, on n'a pas besoin de colonne numérique
        # Mais si nécessaire, prendre la colonne 'quantity' ou 'qty'
        for hint in ("quantity", "qty", "quantit"):
            for col in numeric_cols:
                if hint in str(col).lower():
                    return str(col)
    
    # Fallback : première colonne numérique non-exclue
    return str(numeric_cols[0]) if numeric_cols else None


def _column_hints(frame: pd.DataFrame) -> str:
    cols_lower = {str(c).lower(): c for c in frame.columns}
    category_cols = [cols_lower[k] for k in cols_lower if any(t in k for t in CATEGORY_COLUMNS)]
    amount_cols = [cols_lower[k] for k in cols_lower if any(t in k for t in AMOUNT_COLUMNS)]
    id_cols = [cols_lower[k] for k in cols_lower if any(t in k for t in ID_LIKE_COLUMNS)]

    hints = []
    if category_cols:
        hints.append(f"Colonnes catégorielles suggérées : {category_cols}")
    else:
        hints.append("Pas de colonne Category explicite — ne pas utiliser Description/StockCode comme catégorie")
    if amount_cols:
        hints.append(f"Colonnes numériques suggérées : {amount_cols}")
    if id_cols:
        hints.append(f"Colonnes à NE PAS agréger comme catégorie : {id_cols[:5]}")
    return " | ".join(hints)


def format_for_display(data: Any, max_rows: int = MAX_DISPLAY_ROWS) -> Any:
    """Limite et formate un résultat pour l'affichage (injecté dans le code généré)."""
    if isinstance(data, pd.Series):
        series = data.copy()
        if pd.api.types.is_numeric_dtype(series):
            series = series.sort_values(ascending=False)
        total = len(series)
        if total > max_rows:
            series = series.head(max_rows)
        series.name = series.name or "Valeur"
        frame = series.reset_index()
        if len(frame.columns) == 2:
            frame.columns = [str(frame.columns[0]), str(series.name)]
        if total > max_rows:
            frame.attrs["truncated_note"] = (
                f"Affichage des {max_rows} premiers résultats sur {total} au total."
            )
        return frame

    if isinstance(data, pd.DataFrame):
        frame = data.copy()
        total = len(frame)
        if pd.api.types.is_numeric_dtype(frame.iloc[:, -1]):
            frame = frame.sort_values(frame.columns[-1], ascending=False)
        if total > max_rows:
            frame = frame.head(max_rows)
            frame.attrs["truncated_note"] = (
                f"Affichage des {max_rows} premiers résultats sur {total} au total."
            )
        return frame

    return data


def _extract_top_n(question: str) -> int:
    match = TOP_PATTERN.search(question)
    if match:
        value = match.group(1) or match.group(2)
        return min(int(value), MAX_DISPLAY_ROWS)
    return MAX_DISPLAY_ROWS


def _is_count_request(question: str) -> bool:
    lower = question.lower()
    return any(keyword in lower for keyword in COUNT_KEYWORDS)


def _tabulate_row_count(result: Any) -> int:
    if isinstance(result, pd.DataFrame):
        return len(result)
    if isinstance(result, pd.Series):
        return len(result)
    return 0


def _truncate_text(text: str, max_len: int = MAX_TEXT_LENGTH) -> str:
    text = text.strip()
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}\n\n... (réponse tronquée, {len(text):,} caractères au total)"


def _make_display_answer(display: pd.DataFrame | None, prefix: str | None = None) -> str:
    parts: list[str] = []
    if prefix:
        parts.append(prefix)
    if display is not None and display.attrs.get("truncated_note"):
        parts.append(display.attrs["truncated_note"])
    if not parts and display is not None:
        parts.append("Voici le résultat :")
    if not parts:
        return "Voici le résultat :"
    return "\n\n".join(parts)


def prepare_display_result(
    result: Any,
    question: str,
    datasets: dict[str, pd.DataFrame],
) -> tuple[str, pd.DataFrame | None]:
    """Post-traitement universel : limite et formate toute réponse."""
    if result is None:
        return "Aucun résultat retourné.", None

    # Scalaires et petits textes
    if isinstance(result, (int, float, np.integer, np.floating, bool)):
        return str(result), None

    if isinstance(result, str):
        if result.strip().lower().startswith("graphique"):
            return result, None
        return _truncate_text(result), None

    # Tableaux pandas
    if isinstance(result, (pd.Series, pd.DataFrame)):
        row_count = _tabulate_row_count(result)

        if row_count > MAX_DISPLAY_ROWS:
            summarized = _smart_summarize_fallback(datasets, question, result)
            if summarized is not None:
                display = format_for_display(summarized)
                return _make_display_answer(display, "Résultat résumé automatiquement."), display

            display = format_for_display(result)
            return _make_display_answer(
                display,
                f"Résultat limité à {MAX_DISPLAY_ROWS} lignes (sur {row_count:,} au total).",
            ), display

        display = format_for_display(result)
        return _make_display_answer(display), display

    text = _truncate_text(str(result))
    return text, None


def _clean_code(raw: str) -> str:
    text = raw.strip()
    fenced = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    return text


def _is_chart_request(question: str) -> bool:
    lower = question.lower()
    return any(keyword in lower for keyword in CHART_KEYWORDS)


def _build_datasets_info(datasets: dict[str, pd.DataFrame]) -> str:
    parts = []
    for name, frame in datasets.items():
        sample = frame.head(3).to_string(index=False)
        hints = _column_hints(frame)
        parts.append(
            f"- Nom: '{name}' | Lignes: {len(frame)} | Colonnes: {list(frame.columns)}\n"
            f"  Types: {frame.dtypes.astype(str).to_dict()}\n"
            f"  Indices: {hints}\n"
            f"  Aperçu:\n{sample}"
        )
    return "\n\n".join(parts)


def _extract_code(
    client: Groq,
    model: str,
    datasets: dict[str, pd.DataFrame],
    question: str,
    wants_chart: bool,
    rag_context: str = "",
    chat_history: list[dict[str, Any]] | None = None,
) -> str:
    extra = ""
    
    # --- Analyse automatique du dataset pour guider le LLM ---
    # Trouver la colonne date et la colonne valeur les plus pertinentes
    column_hints_parts = []
    for name, frame in datasets.items():
        date_col = _find_date_column(frame)
        val_col = _find_sales_column(frame, question)
        if date_col:
            column_hints_parts.append(f"# COLONNE_DATE='{date_col}' dans le dataset '{name}'")
        if val_col:
            column_hints_parts.append(f"# COLONNE_VALEUR='{val_col}' dans le dataset '{name}'")
    if column_hints_parts:
        extra += "\n" + "\n".join(column_hints_parts)
    
    # --- Hints contextuels selon le type de question ---
    if wants_chart:
        extra += (
            "\nIMPORTANT : l'utilisateur demande un GRAPHIQUE. "
            "Tu DOIS créer un graphique et appeler save_chart() à la fin."
        )
    if _is_time_groupby_request(question):
        # Déterminer la granularité temporelle
        q_lower = question.lower()
        if any(k in q_lower for k in ("mois", "month", "mensuel", "monthly")):
            period_code = "'M'"
            period_label = "mois"
        elif any(k in q_lower for k in ("trimestre", "quarter", "trimestriel", "quarterly")):
            period_code = "'Q'"
            period_label = "trimestre"
        elif any(k in q_lower for k in ("semaine", "week", "hebdomadaire", "weekly")):
            period_code = "'W'"
            period_label = "semaine"
        elif any(k in q_lower for k in ("année", "an", "year", "annuel", "yearly")):
            period_code = "'A'"
            period_label = "année"
        else:
            period_code = "'D'"
            period_label = "jour"
        
        extra += (
            f"\nIMPORTANT : l'utilisateur veut un groupby PAR {period_label.upper()}. "
            f"Tu DOIS : "
            f"1) convertir la COLONNE_DATE en datetime avec pd.to_datetime(errors='coerce'), "
            f"2) créer une colonne 'Période' = df[COLONNE_DATE].dt.to_period({period_code}).astype(str), "
            f"3) faire groupby('Période').agg(...) en comptant les lignes (pour ventes) ou en sommant la colonne montant (pour CA), "
            f"4) trier par 'Période' croissant, "
            f"5) assigner le résultat à result = format_for_display(...). "
            f"JAMAIS faire groupby sur la colonne date brute."
        )
    elif _is_aggregation_request(question):
        extra += (
            "\nIMPORTANT : question d'AGRÉGATION catégorielle. "
            "Utilise groupby sur une colonne catégorielle (PAS Description/StockCode). "
            "Calcule sum/mean/count, trie par valeur décroissante, "
            "puis result = format_for_display(...)."
        )
    if _is_count_request(question):
        extra += (
            "\nIMPORTANT : question de COMPTAGE. "
            "Retourne UN seul nombre ENTIER via format_for_display, pas toutes les lignes. "
            "N'utilise PAS de colonnes 'return rate', 'discount' ou similaires."
        )
    if TOP_PATTERN.search(question):
        n = _extract_top_n(question)
        extra += (
            f"\nIMPORTANT : limite le résultat aux {n} premiers éléments avec head({n}) "
            "puis format_for_display(...)."
        )
    if not wants_chart:
        extra += (
            "\nIMPORTANT : result = format_for_display(...) obligatoire. "
            f"Maximum {MAX_DISPLAY_ROWS} lignes."
        )
        
    history_text = ""
    if chat_history:
        history_parts = []
        for msg in chat_history[-6:]:
            role = "Utilisateur" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            history_parts.append(f"{role}: {content}")
        history_text = "\n\nHistorique des messages récents :\n" + "\n".join(history_parts)

    prompt = (
        SYSTEM_PROMPT.replace("{datasets_info}", _build_datasets_info(datasets))
        .replace("{rag_context}", (rag_context or "Aucun contexte RAG disponible.") + history_text)
    )
    content = groq_chat_with_fallback(
        client,
        model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question + extra},
        ],
        temperature=0,
    )
    return _clean_code(content)


def _execute_code(
    code: str,
    datasets: dict[str, pd.DataFrame],
    wants_chart: bool,
) -> tuple[Any, bytes | None, str | None]:
    chart_store: list[bytes] = []
    save_chart = _make_save_chart(chart_store)

    try:
        from sklearn.linear_model import LinearRegression
        sklearn_linear = LinearRegression
    except ImportError:
        sklearn_linear = None

    namespace: dict[str, Any] = {
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
        "save_chart": save_chart,
        "format_for_display": format_for_display,
        "datasets": datasets,
        "df": next(iter(datasets.values())) if datasets else pd.DataFrame(),
        "result": None,
        "LinearRegression": sklearn_linear,
    }

    if datasets:
        for name, frame in datasets.items():
            var_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
            if var_name and not var_name[0].isdigit():
                namespace[var_name] = frame
            if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
                namespace[name] = frame

    stdout = io.StringIO()
    error_output = None
    try:
        with redirect_stdout(stdout):
            exec(code, namespace)  # noqa: S102
    except Exception:
        error_output = traceback.format_exc()

    resolved_chart = chart_store[-1] if chart_store else None
    if not resolved_chart:
        resolved_chart = _capture_open_figures()

    output = stdout.getvalue().strip() or None
    raw_result = namespace.get("result")

    if error_output:
        return None, None, error_output

    if isinstance(raw_result, (pd.Series, pd.DataFrame)):
        if _tabulate_row_count(raw_result) > MAX_DISPLAY_ROWS:
            raw_result = format_for_display(raw_result)

    return raw_result, resolved_chart, output


def _smart_summarize_fallback(
    datasets: dict[str, pd.DataFrame],
    question: str,
    raw_result: Any | None = None,
) -> pd.DataFrame | None:
    """Reformate intelligemment un résultat trop volumineux."""
    if not datasets:
        return None

    df = next(iter(datasets.values())).copy()
    cols_lower = {str(c).lower(): c for c in df.columns}

    def col_match(keywords: tuple[str, ...]) -> str | None:
        return next((cols_lower[k] for k in cols_lower if any(t in k for t in keywords)), None)

    # Si le LLM a déjà agrégé mais trop de groupes → garder top N
    if isinstance(raw_result, pd.Series) and len(raw_result) > MAX_DISPLAY_ROWS:
        series = raw_result.copy()
        if pd.api.types.is_numeric_dtype(series):
            series = series.sort_values(ascending=False)
        top_n = _extract_top_n(question)
        return series.head(top_n).reset_index()

    if isinstance(raw_result, pd.DataFrame) and len(raw_result) > MAX_DISPLAY_ROWS:
        frame = raw_result.copy()
        numeric_cols = frame.select_dtypes(include="number").columns
        if len(numeric_cols):
            frame = frame.sort_values(numeric_cols[-1], ascending=False)
        top_n = _extract_top_n(question)
        return frame.head(top_n)

    # Comptage simple
    if _is_count_request(question):
        if isinstance(raw_result, (int, float, np.integer, np.floating)):
            value = raw_result
        else:
            value = len(df)
        return pd.DataFrame({"Indicateur": ["Total"], "Valeur": [value]})

    # Agrégation par catégorie / région / etc.
    if _is_aggregation_request(question):
        amount_col = col_match(AMOUNT_COLUMNS)
        qty_col = col_match(("quantity", "quantité", "quantite", "qty"))
        price_col = col_match(("unitprice", "unit price", "price", "prix"))

        if amount_col is None and qty_col and price_col:
            df["_ventes"] = pd.to_numeric(df[qty_col], errors="coerce") * pd.to_numeric(
                df[price_col], errors="coerce"
            )
            amount_col = "_ventes"
        elif amount_col is None:
            numeric = df.select_dtypes(include="number").columns
            amount_col = numeric[0] if len(numeric) else None

        if amount_col is None:
            return None

        category_col = col_match(CATEGORY_COLUMNS)
        if category_col is None:
            desc_col = col_match(("description", "product", "produit", "item"))
            if desc_col:
                df["_categorie"] = (
                    df[desc_col].astype(str).str.strip().str.split().str[0].str.upper()
                )
                category_col = "_categorie"
            else:
                total = pd.to_numeric(df[amount_col], errors="coerce").sum()
                return pd.DataFrame(
                    {
                        "Message": ["Total global"],
                        "Valeur": [round(float(total), 2)],
                    }
                )

        agg = (
            df.groupby(category_col, dropna=False)[amount_col]
            .sum()
            .sort_values(ascending=False)
        )
        label = "Catégorie" if not str(category_col).startswith("_") else "Groupe"
        return agg.reset_index(name="Total").rename(columns={category_col: label})

    # Top N générique sur colonne catégorielle
    cat_col = col_match(CATEGORY_COLUMNS) or col_match(("customer", "client", "city", "ville"))
    amount_col = col_match(AMOUNT_COLUMNS)
    if cat_col and amount_col:
        top_n = _extract_top_n(question)
        agg = (
            df.groupby(cat_col)[amount_col]
            .sum()
            .sort_values(ascending=False)
            .head(top_n)
            .reset_index(name="Total")
        )
        return agg

    # Dernier recours : aperçu des premières lignes utiles
    top_n = _extract_top_n(question)
    preview = df.head(top_n)
    return preview


def _is_explanation_request(question: str, chat_history: list[dict[str, Any]] | None) -> bool:
    if not chat_history:
        return False
    lower = question.lower().strip()
    keywords = ["comment", "pourquoi", "explique", "explications", "quel code", "quelle formule", "comment as-tu", "comment tu as", "how did", "why did", "explain"]
    return any(kw in lower for kw in keywords)


def generate_explanation(
    client: Groq,
    model: str,
    datasets: dict[str, pd.DataFrame],
    question: str,
    chat_history: list[dict[str, Any]],
    rag_context: str = "",
) -> str:
    datasets_info = _build_datasets_info(datasets)
    
    history_parts = []
    for msg in chat_history[-6:]:
        role = "Utilisateur" if msg["role"] == "user" else "Assistant"
        content = msg["content"]
        code_part = f"\n[Code exécuté par l'assistant: {msg['code']}]" if msg.get("code") else ""
        history_parts.append(f"{role}: {content}{code_part}")
    
    history_text = "\n\n".join(history_parts)
    
    prompt = f"""Tu es un assistant expert en analyse de données e-commerce avec pandas.
L'utilisateur te pose une question explicative sur la logique, le calcul ou le code de programmation utilisé pour obtenir des résultats précédents.

DataFrames disponibles :
{datasets_info}

{rag_context}

Historique des échanges récents :
{history_text}

Règles strictes :
1. Réponds dans la LANGUE utilisée par l'utilisateur dans sa question (français si la question est en français, anglais si la question est en anglais). Sois clair et structuré.
2. Explique la logique métier e-commerce et la formule mathématique utilisée.
3. Référence précisément les colonnes du dataset qui ont été utilisées.
4. Si pertinent, montre le code Pandas précis (dans des blocs ```python) qui a servi à obtenir le résultat.
5. Ne génère pas de code brut à exécuter, explique-le simplement à l'utilisateur.
"""
    content = groq_chat_with_fallback(
        client,
        model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.2,
    )
    return content or "Désolé, je n'ai pas pu générer d'explication."


def _summarize_result_for_narrator(result: Any) -> str:
    if isinstance(result, (pd.DataFrame, pd.Series)):
        return result.head(10).to_string()
    return str(result)


def generate_narrative_answer(
    client: Groq,
    model: str,
    question: str,
    code: str,
    result_summary: str,
) -> str:
    prompt = f"""Tu es un analyste de données e-commerce senior.
L'utilisateur a posé une question sur ses données. Nous avons exécuté du code Python Pandas pour obtenir le résultat brut.

Question de l'utilisateur :
"{question}"

Code exécuté :
```python
{code}
```

Résultat brut obtenu :
{result_summary}

Règles strictes :
1. Détecte la langue de la question de l'utilisateur et réponds OBLIGATOIREMENT dans cette même langue (français si la question est en français, anglais si la question est en anglais). Ne mélange jamais les deux langues dans ta réponse.
2. Rédige une réponse claire et professionnelle (1 à 3 paragraphes).
3. Explique le résultat de manière humaine et concrète, en le reliant au contexte de la question de l'utilisateur.
4. Décris brièvement le calcul ou la logique Pandas appliquée pour arriver à ce résultat.
5. Si le résultat contient des chiffres clés (ex: un total, un panier moyen, des ventes), mentionne-les clairement dans le texte. Si le résultat est un tableau, commente les tendances principales ou le top du classement.
6. Sois fluide et évite d'être trop académique ou trop verbeux. Ne réécris pas tout le code Pandas.
"""
    content = groq_chat_with_fallback(
        client,
        model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Commente et détaille le résultat obtenu."},
        ],
        temperature=0.3,
    )
    return content or "Voici les résultats."


def _is_out_of_domain(code: str) -> bool:
    """Vérifie si le LLM a signalé une question hors domaine."""
    return code.strip() == "HORS_DOMAINE" or "HORS_DOMAINE" in code.strip()


def _out_of_domain_message(question: str) -> str:
    """Retourne le message hors domaine dans la langue de l'utilisateur."""
    lower = question.lower()
    english_words = ["how", "what", "who", "where", "when", "why", "is", "are", "the", "a ", "can", "do", "does"]
    if any(w in lower for w in english_words):
        return "This question is out of my domain. I can only answer questions about your e-commerce data."
    return "Cette question est hors de mon domaine. Je ne réponds qu'aux questions liées à vos données e-commerce."


def _fix_code_with_error(
    client: Groq,
    model: str,
    datasets: dict[str, pd.DataFrame],
    original_question: str,
    failed_code: str,
    error_traceback: str,
) -> str:
    """Demande au LLM de corriger le code qui a planté."""
    datasets_info = _build_datasets_info(datasets)
    prompt = f"""Tu es un expert Python/Pandas. Le code suivant a été généré pour répondre à une question sur un DataFrame, mais il a produit une erreur.

DataFrames disponibles :
{datasets_info}

Question de l'utilisateur : {original_question}

Code qui a échoué :
```python
{failed_code}
```

Erreur obtenue :
{error_traceback}

Règles de correction STRICTES :
1. Écris UNIQUEMENT le code Python corrigé, sans markdown, sans explication.
2. Assure-toi que les DataFrames/Series ne sont JAMAIS vides avant d'appeler .idxmax(), .idxmin(), .max(), .min(), .mean() — utilise `.dropna()` et vérifie `if len(df) > 0:` avant.
3. Si une colonne n'existe pas, cherche-la via une correspondance partielle sur df.columns.
4. Si le résultat est un scalaire vide ou une séquence vide, retourne result = format_for_display(pd.Series(["Aucune donnée disponible"], index=["Info"]))
5. Assigne toujours result = format_for_display(...) à la fin.
"""
    content = groq_chat_with_fallback(
        client,
        model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Corrige ce code pour qu'il s'exécute sans erreur."},
        ],
        temperature=0,
    )
    return _clean_code(content)


def ask_data_question(
    api_key: str,
    datasets: dict[str, pd.DataFrame],
    question: str,
    model: str = DEFAULT_MODEL,
    rag_context: str = "",
    chat_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    client = Groq(api_key=api_key)
    
    if _is_explanation_request(question, chat_history):
        explanation = generate_explanation(client, model, datasets, question, chat_history or [], rag_context)
        return {
            "answer": explanation,
            "chart_bytes": None,
            "display_df": None,
            "code": None,
            "error": False,
        }
        
    wants_chart = _is_chart_request(question)
    code = _extract_code(client, model, datasets, question, wants_chart, rag_context, chat_history)

    # -- Hors domaine : le LLM a renvoyé le sentinel HORS_DOMAINE --
    if _is_out_of_domain(code):
        return {
            "answer": _out_of_domain_message(question),
            "chart_bytes": None,
            "display_df": None,
            "code": None,
            "error": False,
        }

    result, chart_bytes, exec_output = _execute_code(
        code, datasets, wants_chart
    )

    # -- Retry automatique si erreur d'exécution --
    if exec_output and result is None and chart_bytes is None:
        fixed_code = _fix_code_with_error(
            client, model, datasets, question, code, exec_output
        )
        if fixed_code and fixed_code != code:
            result, chart_bytes, exec_output2 = _execute_code(
                fixed_code, datasets, wants_chart
            )
            if result is not None or chart_bytes is not None:
                code = fixed_code
                exec_output = exec_output2  # peut être None si succès
            else:
                # Le retry a aussi échoué : retourner un message propre (pas la trace technique)
                return {
                    "answer": (
                        "⚠️ Je n'ai pas pu calculer ce résultat. "
                        "Essayez de reformuler votre question ou de préciser les colonnes concernées."
                    ),
                    "chart_bytes": None,
                    "display_df": None,
                    "code": fixed_code,
                    "error": True,
                }
        else:
            return {
                "answer": (
                    "⚠️ Je n'ai pas pu calculer ce résultat. "
                    "Essayez de reformuler votre question ou de préciser les colonnes concernées."
                ),
                "chart_bytes": None,
                "display_df": None,
                "code": code,
                "error": True,
            }

    if result is None and chart_bytes is None:
        return {
            "answer": "Aucun résultat produit par le code généré.",
            "chart_bytes": None,
            "display_df": None,
            "code": code,
            "error": True,
        }

    display_df = None

    if wants_chart and chart_bytes:
        answer = ""
        display_df = None
    elif result is not None:
        _, display_df = prepare_display_result(result, question, datasets)
        res_summary = _summarize_result_for_narrator(result)
        try:
            answer = generate_narrative_answer(client, model, question, code, res_summary)
        except Exception:
            answer, _ = prepare_display_result(result, question, datasets)
    else:
        answer = ""

    if wants_chart and not chart_bytes:
        answer = (
            "⚠️ Le graphique n'a pas pu être généré. "
            "Reformulez votre demande ou précisez les colonnes à visualiser."
        )

    return {
        "answer": answer,
        "chart_bytes": chart_bytes,
        "display_df": display_df,
        "code": code,
        "error": False,
    }


def generate_insights(
    api_key: str,
    datasets: dict[str, pd.DataFrame],
    model: str = DEFAULT_MODEL,
) -> list[str]:
    """Génère des insights automatiques pour le rapport PDF."""
    questions = [
        "Quel est le nombre total de lignes et un résumé des colonnes numériques (sum, mean) ?",
        "Quelles sont les 5 valeurs les plus fréquentes dans la première colonne catégorielle trouvée ?",
        "Y a-t-il des valeurs manquantes ? Si oui, combien par colonne ?",
    ]
    insights = []
    for q in questions:
        try:
            response = ask_data_question(api_key, datasets, q, model)
            if not response["error"]:
                insights.append(f"**{q}**\n{response['answer']}")
        except Exception as exc:
            insights.append(f"**{q}**\nAnalyse non disponible : {exc}")
    return insights


def summarize_for_pdf(
    api_key: str,
    datasets: dict[str, pd.DataFrame],
    chat_history: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
) -> str:
    """Produit un résumé exécutif en français pour le PDF."""
    client = Groq(api_key=api_key)
    history_text = "\n".join(
        f"- {msg['role']}: {msg['content'][:500]}"
        for msg in chat_history[-10:]
        if msg.get("role") in ("user", "assistant")
    )
    datasets_info = _build_datasets_info(datasets)

    prompt = f"""Rédige un résumé exécutif en français (4-6 paragraphes) sur ce dataset et les échanges utilisateur.
Sois concret : tendances, chiffres clés, recommandations.

Dataset :
{datasets_info}

Historique récent :
{history_text or "Aucun échange pour le moment."}
"""
    content = groq_chat_with_fallback(
        client,
        model,
        messages=[
            {"role": "system", "content": "Tu es un analyste data senior. Rédige des rapports clairs en français."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return content or "Résumé non disponible."


def _read_uploaded_bytes(uploaded_file) -> bytes:
    uploaded_file.seek(0)
    return uploaded_file.read()


def _decode_csv_bytes(raw: bytes) -> tuple[str, str]:
    """Décode les bytes CSV en testant plusieurs encodages courants."""
    last_error: Exception | None = None
    for encoding in CSV_ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except (UnicodeDecodeError, UnicodeError) as exc:
            last_error = exc
    raise ValueError(
        "Impossible de lire le fichier CSV : encodage non reconnu. "
        "Essayez de l'enregistrer en UTF-8 depuis Excel ou LibreOffice."
    ) from last_error


def _read_csv_text(text: str) -> tuple[pd.DataFrame, str]:
    """Lit un CSV texte en détectant automatiquement le séparateur."""
    first_error: Exception | None = None
    for sep in CSV_SEPARATORS:
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, low_memory=False)
            if len(df.columns) > 1:
                return df, sep
        except Exception as exc:
            first_error = exc
    try:
        return pd.read_csv(io.StringIO(text), low_memory=False), ","
    except Exception as exc:
        raise ValueError(f"Impossible de parser le CSV : {exc}") from first_error


def read_csv_robust(uploaded_file) -> tuple[pd.DataFrame, dict[str, str]]:
    """Charge un CSV avec détection automatique d'encodage et de séparateur."""
    raw = _read_uploaded_bytes(uploaded_file)
    text, encoding = _decode_csv_bytes(raw)
    df, separator = _read_csv_text(text)
    meta = {"encoding": encoding, "separator": repr(separator)}
    df.attrs["load_info"] = meta
    return df, meta


def load_dataset(uploaded_file) -> pd.DataFrame:
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df, _meta = read_csv_robust(uploaded_file)
        return df
    if name.endswith((".xlsx", ".xls")):
        uploaded_file.seek(0)
        return pd.read_excel(uploaded_file)
    if name.endswith(".json"):
        uploaded_file.seek(0)
        return pd.read_json(uploaded_file)
    if name.endswith(".parquet"):
        uploaded_file.seek(0)
        return pd.read_parquet(uploaded_file)
    raise ValueError(f"Format non supporté : {uploaded_file.name}")


def dataset_overview(datasets: dict[str, pd.DataFrame]) -> dict[str, Any]:
    overview = {
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "files": [],
    }
    for name, frame in datasets.items():
        numeric = frame.select_dtypes(include="number")
        overview["files"].append(
            {
                "name": name,
                "rows": len(frame),
                "columns": list(frame.columns),
                "dtypes": frame.dtypes.astype(str).to_dict(),
                "missing": frame.isna().sum().to_dict(),
                "describe": numeric.describe().to_string() if not numeric.empty else "Aucune colonne numérique",
            }
        )
    return overview
