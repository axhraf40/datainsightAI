"""Nettoyage et préparation automatique des datasets à l'upload."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

DATE_PATTERNS = [
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d-%m-%y",
    "%Y/%m/%d",
]

COMMON_DATE_KEYWORDS = ("date", "time", "jour", "month", "year", "created", "updated")


@dataclass
class CleaningReport:
    filename: str
    rows_before: int
    rows_after: int
    cols_before: int
    cols_after: int
    actions: list[str] = field(default_factory=list)
    missing_before: dict[str, int] = field(default_factory=dict)
    missing_after: dict[str, int] = field(default_factory=dict)
    dtypes_converted: dict[str, str] = field(default_factory=dict)

    @property
    def rows_removed(self) -> int:
        return self.rows_before - self.rows_after

    @property
    def cols_removed(self) -> int:
        return self.cols_before - self.cols_after

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "rows_before": self.rows_before,
            "rows_after": self.rows_after,
            "cols_before": self.cols_before,
            "cols_after": self.cols_after,
            "rows_removed": self.rows_removed,
            "cols_removed": self.cols_removed,
            "actions": self.actions,
            "missing_before": self.missing_before,
            "missing_after": self.missing_after,
            "dtypes_converted": self.dtypes_converted,
        }


def _normalize_column_names(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    cleaned = df.copy()
    new_cols = []
    changed = False
    for col in cleaned.columns:
        new_name = re.sub(r"\s+", " ", str(col).strip())
        if new_name != col:
            changed = True
        new_cols.append(new_name)
    cleaned.columns = new_cols
    return cleaned, changed


def _strip_string_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    cleaned = df.copy()
    fixed = 0
    for col in cleaned.select_dtypes(include=["object", "string"]).columns:
        series = cleaned[col].astype("string")
        stripped = series.str.strip()
        count = int((series.notna() & (series != stripped)).sum())
        if count:
            fixed += count
            cleaned[col] = stripped
        cleaned[col] = cleaned[col].replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "None": pd.NA})
    return cleaned, fixed


def _remove_empty_rows_cols(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    before_rows, before_cols = len(df), len(df.columns)
    cleaned = df.dropna(how="all")
    cleaned = cleaned.dropna(axis=1, how="all")
    return cleaned, before_rows - len(cleaned), before_cols - len(cleaned.columns)


def _remove_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    before = len(df)
    cleaned = df.drop_duplicates()
    return cleaned, before - len(cleaned)


def _looks_like_date_column(name: str) -> bool:
    lower = name.lower()
    return any(keyword in lower for keyword in COMMON_DATE_KEYWORDS)


def _try_parse_dates(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    cleaned = df.copy()
    converted: list[str] = []
    for col in cleaned.columns:
        if cleaned[col].dtype != "object":
            continue
        if not _looks_like_date_column(col):
            continue
        sample = cleaned[col].dropna().astype(str).head(20)
        if sample.empty:
            continue
        for fmt in DATE_PATTERNS:
            try:
                parsed = pd.to_datetime(cleaned[col], format=fmt, errors="coerce")
                if parsed.notna().mean() >= 0.7:
                    cleaned[col] = parsed
                    converted.append(f"{col} → datetime ({fmt})")
                    break
            except (ValueError, TypeError):
                continue
        else:
            parsed = pd.to_datetime(cleaned[col], errors="coerce", dayfirst=True)
            if parsed.notna().mean() >= 0.7:
                cleaned[col] = parsed
                converted.append(f"{col} → datetime (auto)")
    return cleaned, converted


def _try_convert_numeric(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    cleaned = df.copy()
    converted: list[str] = []
    for col in cleaned.select_dtypes(include=["object", "string"]).columns:
        series = cleaned[col].astype("string")
        numeric_candidate = series.str.replace(r"[€$£%\s]", "", regex=True)
        numeric_candidate = numeric_candidate.str.replace(",", ".", regex=False)
        converted_series = pd.to_numeric(numeric_candidate, errors="coerce")
        if converted_series.notna().mean() >= 0.8:
            cleaned[col] = converted_series
            converted.append(f"{col} → numérique")
    return cleaned, converted


def _fill_missing_values(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    cleaned = df.copy()
    actions: list[str] = []
    for col in cleaned.columns:
        missing = int(cleaned[col].isna().sum())
        if missing == 0:
            continue
        if pd.api.types.is_numeric_dtype(cleaned[col]):
            fill_value = cleaned[col].median()
            if pd.notna(fill_value):
                cleaned[col] = cleaned[col].fillna(fill_value)
                actions.append(f"{col} : {missing} valeurs manquantes → médiane ({fill_value:.2f})")
        else:
            mode = cleaned[col].mode(dropna=True)
            if not mode.empty:
                cleaned[col] = cleaned[col].fillna(mode.iloc[0])
                actions.append(f"{col} : {missing} valeurs manquantes → mode ({mode.iloc[0]})")
    return cleaned, actions


def clean_dataset(df: pd.DataFrame, filename: str = "dataset") -> tuple[pd.DataFrame, CleaningReport]:
    """Applique un pipeline de nettoyage complet et retourne le DataFrame + rapport."""
    report = CleaningReport(
        filename=filename,
        rows_before=len(df),
        cols_before=len(df.columns),
        rows_after=len(df),
        cols_after=len(df.columns),
        missing_before=df.isna().sum().to_dict(),
    )

    cleaned = df.copy()

    cleaned, cols_changed = _normalize_column_names(cleaned)
    if cols_changed:
        report.actions.append("Noms de colonnes normalisés (espaces supprimés)")

    cleaned, stripped = _strip_string_columns(cleaned)
    if stripped:
        report.actions.append(f"{stripped} cellules texte nettoyées (espaces, valeurs vides)")

    cleaned, empty_rows, empty_cols = _remove_empty_rows_cols(cleaned)
    if empty_rows:
        report.actions.append(f"{empty_rows} lignes vides supprimées")
    if empty_cols:
        report.actions.append(f"{empty_cols} colonnes vides supprimées")

    cleaned, dupes = _remove_duplicates(cleaned)
    if dupes:
        report.actions.append(f"{dupes} lignes dupliquées supprimées")

    cleaned, date_conversions = _try_parse_dates(cleaned)
    for conv in date_conversions:
        report.actions.append(f"Conversion date : {conv}")
        col_name = conv.split(" → ")[0]
        report.dtypes_converted[col_name] = "datetime"

    cleaned, num_conversions = _try_convert_numeric(cleaned)
    for conv in num_conversions:
        report.actions.append(f"Conversion numérique : {conv}")
        col_name = conv.split(" → ")[0]
        report.dtypes_converted[col_name] = "numeric"

    cleaned, fill_actions = _fill_missing_values(cleaned)
    report.actions.extend(fill_actions)

    report.rows_after = len(cleaned)
    report.cols_after = len(cleaned.columns)
    report.missing_after = cleaned.isna().sum().to_dict()

    if not report.actions:
        report.actions.append("Aucune correction nécessaire — données déjà propres")

    return cleaned, report
