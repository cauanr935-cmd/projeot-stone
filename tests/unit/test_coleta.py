"""Testes da coleta: sem rede, sem Apify, sem YouTube (apenas funções puras e fakes)."""
from datetime import UTC, datetime

import pandas as pd
import pytest

from src.coleta import instagram as ig
from src.coleta import midia
from src.coleta import youtube as yt
from src.coleta.metricas import adicionar_metricas, filtrar_idade, numero

COLETA = datetime(2026, 11, 17, tzinfo=UTC)


def _post(**kw):
    base = {"shortCode": "AbC", "url": "https://instagram.com/p/AbC", "ownerUsername": "Fulano",
            "type": "Video", "caption": "oi", "timestamp": "2026-10-01T12:00:00.000Z",
            "likesCount": 100, "commentsCount": 10, "videoPlayCount": 5000, "videoDuration": 21.5}
    base.update(kw)
    return base


@pytest.mark.parametrize("v,esperado", [(None, None), (-1, None), (float("nan"), None), (0, 0), (7, 7), (True, None)])
def test_numero_curtidas_ocultas(v, esperado):
    assert numero(v) == esperado


def test_normalizar_post_basico():
    r = ig.normalizar_post(_post(), COLETA)
    assert r["post_id"] == "AbC" and r["username"] == "fulano" and r["plataforma"] == "instagram"
    assert r["tipo_post"] == "reels" and r["curtidas"] == 100 and r["views"] == 5000
    assert r["idade_dias"] == 46


def test_normalizar_post_curtidas_ocultas():
    assert ig.normalizar_post(_post(likesCount=-1), COLETA)["curtidas"] is None
    assert ig.normalizar_post(_post(likesCount=None), COLETA)["curtidas"] is None


def test_views_fallback_para_videoViewCount():
    r = ig.normalizar_post(_post(videoPlayCount=None, videoViewCount=300), COLETA)
    assert r["views"] == 300


@pytest.mark.parametrize("t,esperado", [("Video", "reels"), ("Sidecar", "carrossel"), ("Image", "imagem")])
def test_mapeamento_de_tipos(t, esperado):
    assert ig.mapear_tipo(t) == esperado
    assert ig.normalizar_post(_post(type=t, childPosts=[{}, {}]), COLETA)["tipo_post"] == esperado


def test_n_slides():
    assert ig.normalizar_post(_post(type="Sidecar", childPosts=[{}, {}, {}]), COLETA)["n_slides"] == 3


def test_filtro_de_14_dias():
    df = pd.DataFrame({"idade_dias": [3, 13, 14, 15, 400]})
    assert filtrar_idade(df, 14)["idade_dias"].tolist() == [14, 15, 400]


def _df(rows):
    cols = {"plataforma": "instagram", "views": 1000}
    return pd.DataFrame([{**cols, **r} for r in rows])


def test_metricas():
    df = adicionar_metricas(_df([
        {"username": "a", "curtidas": 90, "comentarios": 10, "seguidores": 1000},   # 0.10
        {"username": "a", "curtidas": 40, "comentarios": 10, "seguidores": 1000},   # 0.05
        {"username": "a", "curtidas": 190, "comentarios": 10, "seguidores": 1000},  # 0.20
    ]))
    assert df["taxa_eng"].round(3).tolist() == [0.1, 0.05, 0.2]
    assert df["score_relativo"].round(3).tolist() == [1.0, 0.5, 2.0]   # mediana = 0.10
    assert df["alcance"].tolist() == [1.0, 1.0, 1.0]
    assert df["ressonancia"].round(3).tolist() == [0.1, 0.05, 0.2]


def test_metricas_curtidas_ocultas_ficam_fora_da_mediana():
    df = adicionar_metricas(_df([
        {"username": "a", "curtidas": 90, "comentarios": 10, "seguidores": 1000},
        {"username": "a", "curtidas": None, "comentarios": 10, "seguidores": 1000},
        {"username": "a", "curtidas": 190, "comentarios": 10, "seguidores": 1000},
    ]))
    assert df["curtidas_ocultas"].tolist() == [False, True, False]
    assert pd.isna(df.loc[1, "taxa_eng"]) and pd.isna(df.loc[1, "score_relativo"])
    assert df.loc[0, "score_relativo"] == pytest.approx(0.1 / 0.15)


def test_metricas_seguidores_zero_ou_nulo_nao_divide():
    df = adicionar_metricas(_df([
        {"username": "a", "curtidas": 5, "comentarios": 1, "seguidores": 0},
        {"username": "b", "curtidas": 5, "comentarios": 1, "seguidores": None},
    ]))
    assert df["taxa_eng"].isna().all() and df["alcance"].isna().all()


def test_mediana_por_perfil_separada():
    df = adicionar_metricas(_df([
        {"username": "a", "curtidas": 10, "comentarios": 0, "seguidores": 100},
        {"username": "b", "curtidas": 50, "comentarios": 0, "seguidores": 100},
    ]))
    assert df["score_relativo"].tolist() == [1.0, 1.0]


@pytest.mark.parametrize("iso,seg", [("PT45S", 45), ("PT1M5S", 65), ("PT3M", 180), ("PT1H", 3600), (None, None)])
def test_duracao_iso(iso, seg):
    assert yt.duracao_segundos(iso) == seg


@pytest.mark.parametrize("dur,esperado", [(59, True), (180, True), (181, False), (0, False), (None, False)])
def test_heuristica_short(dur, esperado):
    assert yt.eh_short(dur) is esperado


def test_normalizar_video_youtube():
    v = {"id": "xyz", "snippet": {"title": "T", "description": "D", "publishedAt": "2026-10-01T00:00:00Z"},
         "contentDetails": {"duration": "PT30S"}, "statistics": {"viewCount": "1000", "likeCount": "50"}}
    r = yt.normalizar_video(v, "@Canal", COLETA)
    assert r["tipo_post"] == "short" and r["url"].endswith("/shorts/xyz")
    assert r["curtidas"] == 50 and r["comentarios"] is None and r["views"] == 1000
    assert r["username"] == "@canal" and r["legenda"] == "T\nD"


def test_youtube_longo_nao_e_short():
    v = {"id": "x", "snippet": {"publishedAt": "2026-10-01T00:00:00Z"},
         "contentDetails": {"duration": "PT10M"}, "statistics": {}}
    assert yt.normalizar_video(v, "@c", COLETA)["tipo_post"] == "video"


def test_ler_perfis_csv_filtros(tmp_path):
    csv = tmp_path / "p.csv"
    csv.write_text("plataforma,username,tamanho,tipo_conta,segmento\n"
                   "instagram,@A,pequeno,criador,geral\ninstagram,b,medio,marca,geral\n"
                   "youtube,@c,medio,criador,geral\n")
    assert ig.ler_perfis_csv(csv, "instagram")["username"].tolist() == ["a", "b"]
    assert ig.ler_perfis_csv(csv, "instagram", apenas=["@B"])["username"].tolist() == ["b"]
    assert ig.ler_perfis_csv(csv, "instagram", max_perfis=1)["username"].tolist() == ["a"]
    assert ig.ler_perfis_csv(csv, "youtube")["username"].tolist() == ["@c"]


def test_trava_de_custo():
    ig.checar_custo(5, False)
    with pytest.raises(SystemExit):
        ig.checar_custo(6, False)
    ig.checar_custo(600, True)


def test_rodar_actor_usa_cache_e_registra_custo(tmp_path):
    class Actor:
        def call(self, run_input):
            Actor.n += 1
            return {"id": "r1", "defaultDatasetId": "d", "usageTotalUsd": 0.0123}
    Actor.n = 0

    class Client:
        def actor(self, _): return Actor()
        def dataset(self, _):
            return type("D", (), {"iterate_items": lambda s: iter([{"a": 1}])})()

    cache = tmp_path / "x.json"
    assert ig.rodar_actor(Client(), "a/b", {}, cache) == [{"a": 1}]
    assert ig.rodar_actor(Client(), "a/b", {}, cache) == [{"a": 1}]
    assert Actor.n == 1
    assert '"usageTotalUsd": 0.0123' in cache.with_suffix(".run.json").read_text()


def test_baixar_sem_url_ou_com_arquivo_existente(tmp_path):
    assert ig.baixar(None, tmp_path / "a.jpg") is False
    f = tmp_path / "b.jpg"
    f.write_bytes(b"x")
    assert ig.baixar("http://invalido.local/x", f) is True  # cache: não toca na rede


def test_destino_frames(tmp_path):
    assert midia.destino_frames(tmp_path / "abc" / "video.mp4") == tmp_path / "abc" / "frames"
    assert midia.destino_frames(tmp_path / "xyz.mp4") == tmp_path / "xyz_frames"


def test_selecionar_top_por_tipo():
    df = pd.DataFrame({
        "post_id": ["r1", "r2", "r3", "c1", "c2"],
        "tipo_post": ["reels", "reels", "reels", "carrossel", "carrossel"],
        "views": [100, 900, 500, None, None],
        "curtidas": [1, 1, 1, 10, 50], "comentarios": [0, 0, 0, 0, 5],
    })
    assert ig.selecionar_top(df, 2) == {"r2", "r3", "c1", "c2"}
    assert ig.selecionar_top(df, 1) == {"r2", "c2"}


def test_campo_aceita_dict_e_objeto():
    class Run:
        default_dataset_id = "d1"
        usage_total_usd = 0.5
    assert ig._campo(Run(), "default_dataset_id", "defaultDatasetId") == "d1"
    assert ig._campo({"defaultDatasetId": "d2"}, "default_dataset_id", "defaultDatasetId") == "d2"
    assert ig._campo(Run(), "inexistente") is None
