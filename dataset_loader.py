"""Chargement de datasets depuis des octets (stockage SQLite BLOB)."""

from __future__ import annotations

import io
import os

import pandas as pd

CSV_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1", "iso-8859-1", "utf-16")
CSV_SEPARATORS = (",", ";", "\t", "|")


def _decode_csv_bytes(raw: bytes) -> tuple[str, str]:
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


def load_dataset_from_bytes(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Charge un dataset depuis des octets (stockage BDD)."""
    name = filename.lower()
    if name.endswith(".csv"):
        text, encoding = _decode_csv_bytes(file_bytes)
        df, separator = _read_csv_text(text)
        df.attrs["load_info"] = {"encoding": encoding, "separator": repr(separator)}
        return df
    buffer = io.BytesIO(file_bytes)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(buffer)
    if name.endswith(".json"):
        return pd.read_json(buffer)
    if name.endswith(".parquet"):
        return pd.read_parquet(buffer)
    raise ValueError(f"Format non supporté : {filename}")


def load_dataset_from_path(path: str) -> pd.DataFrame:
    """Charge un dataset depuis le disque (rétrocompatibilité migration)."""
    with open(path, "rb") as handle:
        return load_dataset_from_bytes(handle.read(), os.path.basename(path))
