"""Schema estável da tabela `posts` (contrato para ranking, categorização e agente)."""
from __future__ import annotations

import pandas as pd

# coluna -> dtype pandas
POSTS_SCHEMA: dict[str, str] = {
    "plataforma": "string", "post_id": "string", "url": "string", "username": "string",
    "tipo_post": "string", "product_type": "string", "legenda": "string",
    "data_post": "datetime64[ns, UTC]", "data_coleta": "datetime64[ns, UTC]", "idade_dias": "Int64",
    "curtidas": "Int64", "comentarios": "Int64", "views": "Int64", "duracao_s": "Float64",
    "n_slides": "Int64", "collab": "boolean", "publipost": "boolean",
    "seguidores": "Int64", "tamanho": "string", "tipo_conta": "string", "segmento": "string",
    "curtidas_ocultas": "boolean", "elegivel_ranking": "boolean",
    "taxa_eng": "Float64", "score_relativo": "Float64", "alcance": "Float64", "ressonancia": "Float64",
    "thumb_ok": "boolean", "video_ok": "boolean", "pasta_midia": "string", "grupo_midia": "string",
    "lote": "string",
}
# hashtags fica como lista de strings (tratada à parte)
EXCLUIDOS_COLS = ["plataforma", "post_id", "url", "username", "tipo_post", "data_post", "motivo", "lote"]

MOTIVOS = {
    "menos_14_dias": "publicado há menos de 14 dias na data da coleta (métricas não estabilizadas)",
    "colaboracao_dono_diferente": "Reel da grade do perfil, mas de outra conta (seguidores não são do dono)",
    "fora_janela_12m": "publicado há mais de 12 meses da data da coleta (fora da janela de atividade)",
    "fora_do_foco_reels": "carrossel ou imagem (piloto do @impulsostone); a base é só de Reels",
}


def aplicar_schema(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for col, dt in POSTS_SCHEMA.items():
        s = df[col] if col in df else pd.Series([None] * len(df), index=df.index)
        if dt.startswith("datetime"):
            out[col] = pd.to_datetime(s, utc=True)
        elif dt in ("Int64",):
            out[col] = pd.to_numeric(s, errors="coerce").round().astype("Int64")
        elif dt == "Float64":
            out[col] = pd.to_numeric(s, errors="coerce").astype("Float64")
        elif dt == "boolean":
            out[col] = s.astype("boolean")
        else:
            out[col] = s.astype("string")
    out["hashtags"] = df["hashtags"].map(lambda v: [str(x) for x in v] if v is not None and len(v) else []) \
        if "hashtags" in df else [[] for _ in range(len(df))]
    return out
