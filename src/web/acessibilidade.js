/* Acessibilidade Impulso Stone: daltonismo, tamanho da letra, contraste, VLibras.
   Script único, sem dependências, incluído em todas as páginas. Preferências em localStorage. */
(function () {
  "use strict";
  var KEY = "impulso.a11y";
  var DEF = { fonte: 100, cor: "normal", contraste: false, links: false, leitura: false, mov: false, libras: false };
  var P = Object.assign({}, DEF);
  try { P = Object.assign(P, JSON.parse(localStorage.getItem(KEY) || "{}")); } catch (e) {}
  var salvar = function () { try { localStorage.setItem(KEY, JSON.stringify(P)); } catch (e) {} };

  // Matrizes de daltonização (compensam a perda de canal em vez de simular a falta dele).
  var MATRIZES = {
    protanopia: "0.567 0.433 0 0 0  0.558 0.442 0 0 0  0 0.242 0.758 0 0  0 0 0 1 0",
    deuteranopia: "0.625 0.375 0 0 0  0.7 0.3 0 0 0  0 0.3 0.7 0 0  0 0 0 1 0",
    tritanopia: "0.95 0.05 0 0 0  0 0.433 0.567 0 0  0 0.475 0.525 0 0  0 0 0 1 0",
    monocromatico: "0.299 0.587 0.114 0 0  0.299 0.587 0.114 0 0  0.299 0.587 0.114 0 0  0 0 0 1 0"
  };
  var ROTULOS = { normal: "Cores originais", protanopia: "Protanopia (sem vermelho)", deuteranopia: "Deuteranopia (sem verde)",
    tritanopia: "Tritanopia (sem azul)", monocromatico: "Preto e branco (acromatopsia)" };

  var css = [
    "html.a11y-contraste body{background:#000!important;color:#fff!important}",
    "html.a11y-contraste *{border-color:#fff!important;text-shadow:none!important}",
    "html.a11y-contraste a{color:#ffff00!important}",
    "html.a11y-contraste button,html.a11y-contraste input,html.a11y-contraste textarea,html.a11y-contraste select{background:#000!important;color:#fff!important;border:2px solid #fff!important}",
    "html.a11y-contraste [class*=muted],html.a11y-contraste small,html.a11y-contraste p{color:#fff!important}",
    "html.a11y-links a{text-decoration:underline!important;text-underline-offset:3px}",
    "html.a11y-leitura,html.a11y-leitura *{font-family:Verdana,Tahoma,'Atkinson Hyperlegible',sans-serif!important;letter-spacing:.04em!important;word-spacing:.12em!important;line-height:1.7!important}",
    "html.a11y-mov *,html.a11y-mov *::before,html.a11y-mov *::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}",
    "html.a11y-mov video{animation:none!important}",
    "*:focus-visible{outline:3px solid #7dffb5!important;outline-offset:2px!important}",
    ".a11y-skip{position:fixed;left:8px;top:-60px;z-index:100001;background:#7dffb5;color:#000;padding:10px 16px;border-radius:8px;font-weight:700;text-decoration:none}.a11y-skip:focus{top:8px}",
    "#a11y-btn{position:fixed;left:16px;bottom:16px;z-index:100000;width:52px;height:52px;border-radius:50%;border:2px solid #fff;background:#0b5fff;color:#fff;cursor:pointer;display:grid;place-items:center;box-shadow:0 6px 20px #0008}",
    "#a11y-btn:hover{background:#0a4fd6}",
    "#a11y-panel{position:fixed;left:16px;bottom:78px;z-index:100000;width:min(340px,calc(100vw - 32px));max-height:calc(100vh - 100px);overflow:auto;background:#fff;color:#111;border:2px solid #0b5fff;border-radius:16px;padding:16px;font:15px/1.4 system-ui,sans-serif;box-shadow:0 20px 50px #000a}",
    "#a11y-panel[hidden]{display:none}",
    "#a11y-panel h2{margin:0 0 10px;font-size:1.05rem;color:#111}",
    "#a11y-panel fieldset{border:1px solid #c9d1dc;border-radius:10px;margin:0 0 12px;padding:10px}",
    "#a11y-panel legend{font-weight:700;padding:0 6px;color:#111}",
    "#a11y-panel label{display:flex;align-items:center;gap:8px;padding:4px 0;cursor:pointer;color:#111}",
    "#a11y-panel input{accent-color:#0b5fff;width:18px;height:18px}",
    "#a11y-panel .row{display:flex;gap:8px;align-items:center}",
    "#a11y-panel .row button,#a11y-panel .reset{background:#0b5fff;color:#fff;border:0;border-radius:8px;padding:8px 14px;font-weight:700;cursor:pointer;font-size:1rem}",
    "#a11y-panel .reset{background:#e6ebf2;color:#111;width:100%}",
    "#a11y-panel output{min-width:52px;text-align:center;font-weight:700}",
    "html.a11y-contraste #a11y-panel,html.a11y-contraste #a11y-panel *{background:#000!important;color:#fff!important;border-color:#fff!important}"
  ].join("\n");

  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in (attrs || {})) e.setAttribute(k, attrs[k]);
    if (html) e.innerHTML = html;
    return e;
  }

  function aplicar() {
    var h = document.documentElement;
    h.classList.toggle("a11y-contraste", !!P.contraste);
    h.classList.toggle("a11y-links", !!P.links);
    h.classList.toggle("a11y-leitura", !!P.leitura);
    h.classList.toggle("a11y-mov", !!P.mov);
    // Tamanho da letra: escala o conteúdo todo (rem e px), sem afetar o painel.
    document.body.style.zoom = P.fonte === 100 ? "" : String(P.fonte / 100);
    h.style.filter = P.cor === "normal" ? "" : "url(#a11y-f-" + P.cor + ")";
    var o = document.getElementById("a11y-fonte-val");
    if (o) o.textContent = P.fonte + "%";
    var libras = document.querySelector("[vw]");
    if (libras) libras.style.display = P.libras ? "" : "none";
    salvar();
  }

  function carregarVLibras() {
    if (window.__vlibras) return;
    window.__vlibras = true;
    var box = el("div", { vw: "", class: "enabled" });
    box.innerHTML = '<div vw-access-button class="active"></div><div vw-plugin-wrapper><div class="vw-plugin-top-wrapper"></div></div>';
    document.body.appendChild(box);
    var s = el("script", { src: "https://vlibras.gov.br/app/vlibras-plugin.js", async: "" });
    s.onload = function () { try { new window.VLibras.Widget("https://vlibras.gov.br/app"); } catch (e) {} };
    s.onerror = function () { window.__vlibras = false; box.remove(); };
    document.head.appendChild(s);
  }

  function montar() {
    document.head.appendChild(el("style", { id: "a11y-css" }, css));

    // Filtros SVG de daltonismo
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>';
    Object.keys(MATRIZES).forEach(function (k) {
      svg += '<filter id="a11y-f-' + k + '" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values="' + MATRIZES[k] + '"/></filter>';
    });
    document.body.appendChild(el("div", { "aria-hidden": "true" }, svg + "</defs></svg>"));

    var main = document.querySelector("main,.wrap,section") || document.body;
    if (!main.id) main.id = "a11y-conteudo";
    document.body.insertBefore(el("a", { class: "a11y-skip", href: "#" + main.id }, "Pular para o conteúdo"), document.body.firstChild);

    var btn = el("button", { id: "a11y-btn", type: "button", "aria-label": "Abrir opções de acessibilidade", "aria-expanded": "false", "aria-controls": "a11y-panel", title: "Acessibilidade" },
      '<svg width="30" height="30" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="12" cy="4.2" r="2.2"/><path d="M20 8.5H4v2h6v3.3l-1.9 6.7 1.9.6L12 15l2 6.1 1.9-.6L14 13.8V10.5h6z"/></svg>');
    var cores = Object.keys(ROTULOS).map(function (k) {
      return '<label><input type="radio" name="a11y-cor" value="' + k + '"' + (P.cor === k ? " checked" : "") + "> " + ROTULOS[k] + "</label>";
    }).join("");
    var panel = el("div", { id: "a11y-panel", role: "dialog", "aria-label": "Opções de acessibilidade", hidden: "" },
      "<h2>Acessibilidade</h2>" +
      '<fieldset><legend>Tamanho da letra</legend><div class="row"><button type="button" id="a11y-menos" aria-label="Diminuir letras">A−</button><output id="a11y-fonte-val" aria-live="polite">' + P.fonte + '%</output><button type="button" id="a11y-mais" aria-label="Aumentar letras">A+</button></div></fieldset>' +
      "<fieldset><legend>Filtro para daltonismo</legend>" + cores + "</fieldset>" +
      "<fieldset><legend>Leitura e visão</legend>" +
      '<label><input type="checkbox" id="a11y-contraste"> Alto contraste</label>' +
      '<label><input type="checkbox" id="a11y-links"> Sublinhar links</label>' +
      '<label><input type="checkbox" id="a11y-leitura"> Fonte e espaçamento para leitura fácil</label>' +
      '<label><input type="checkbox" id="a11y-mov"> Reduzir animações</label></fieldset>' +
      "<fieldset><legend>Língua de sinais</legend>" +
      '<label><input type="checkbox" id="a11y-libras"> Ativar VLibras (tradução para Libras)</label></fieldset>' +
      '<button type="button" class="reset" id="a11y-reset">Restaurar padrão</button>');
    document.body.appendChild(btn);
    document.body.appendChild(panel);

    function sync() {
      ["contraste", "links", "leitura", "mov", "libras"].forEach(function (k) { document.getElementById("a11y-" + k).checked = !!P[k]; });
      Array.prototype.forEach.call(panel.querySelectorAll('input[name="a11y-cor"]'), function (r) { r.checked = r.value === P.cor; });
    }
    function abrir(v) {
      panel.hidden = !v;
      btn.setAttribute("aria-expanded", String(v));
      if (v) panel.querySelector("button,input").focus(); else btn.focus();
    }
    btn.onclick = function () { abrir(panel.hidden); };
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) abrir(false); });
    document.getElementById("a11y-menos").onclick = function () { P.fonte = Math.max(80, P.fonte - 10); aplicar(); };
    document.getElementById("a11y-mais").onclick = function () { P.fonte = Math.min(200, P.fonte + 10); aplicar(); };
    ["contraste", "links", "leitura", "mov"].forEach(function (k) {
      document.getElementById("a11y-" + k).onchange = function (e) { P[k] = e.target.checked; aplicar(); };
    });
    document.getElementById("a11y-libras").onchange = function (e) {
      P.libras = e.target.checked; if (P.libras) carregarVLibras(); aplicar();
    };
    Array.prototype.forEach.call(panel.querySelectorAll('input[name="a11y-cor"]'), function (r) {
      r.onchange = function () { P.cor = r.value; aplicar(); };
    });
    document.getElementById("a11y-reset").onclick = function () { P = Object.assign({}, DEF); sync(); aplicar(); };

    if (P.libras) carregarVLibras();
    sync();
    aplicar();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", montar); else montar();
})();
