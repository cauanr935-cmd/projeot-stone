"""Normalização numérica, filtro de idade e métricas de engajamento (compartilhado IG/YT)."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd


def numero(v: Any) -> int | float | None:
    """Contagens ocultas ou inválidas viram None (Instagram devolve None ou -1 para curtidas ocultas)."""
    if v is None or isinstance(v, bool):
        return None
    try:
        if isinstance(v, float) and math.isnan(v):
            return None
        return None if v < 0 else v
    except TypeError:
        return None


def filtrar_idade(df: pd.DataFrame, idade_minima_dias: int) -> pd.DataFrame:
    """Mantém só posts com pelo menos `idade_minima_dias` dias na data da coleta."""
    return df[df["idade_dias"] >= idade_minima_dias].copy()


def adicionar_metricas(df: pd.DataFrame) -> pd.DataFrame:
    """taxa_eng, score_relativo (vs. mediana do perfil), alcance e ressonância.

    Linhas com curtidas ocultas ficam com taxa_eng/score NaN e não entram na mediana.
    """
    df = df.copy()
    for c in ("curtidas", "comentarios", "views", "seguidores"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    seg = df["seguidores"].where(df["seguidores"] > 0)
    views = df["views"].where(df["views"] > 0)
    inter = df["curtidas"] + df["comentarios"]  # NaN se curtidas ocultas
    df["curtidas_ocultas"] = df["curtidas"].isna()
    df["taxa_eng"] = inter / seg
    mediana = df.groupby(["plataforma", "username"])["taxa_eng"].transform("median")
    df["score_relativo"] = df["taxa_eng"] / mediana.where(mediana > 0)
    df["alcance"] = df["views"] / seg
    df["ressonancia"] = inter / views
    return df
