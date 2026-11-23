from src.analise.score_viral import carregar_referencia, pontuar


def test_mediana_do_top10_tem_nota_alta_e_extremo_tem_nota_baixa():
    ref = carregar_referencia()
    assert len(ref) >= 100
    mediana = {k: sorted(r[k] for r in ref if r.get(k) is not None)[len([1 for r in ref if r.get(k) is not None]) // 2]
               for k in ("duration_sec", "cuts_per_minute", "words_per_minute", "speech_activity_ratio",
                         "face_detected_ratio", "max_face_area_pct", "optical_flow_25d_score", "subtitle_zone_contrast")}
    alto = pontuar(mediana, ref)
    ruim = pontuar({k: v * 50 + 100 for k, v in mediana.items()}, ref)
    assert alto["nota"] >= 90 and alto["faixa"] == "alto"
    assert ruim["nota"] <= 30 and ruim["melhorias"]
