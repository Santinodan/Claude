#!/usr/bin/env python3
"""Arma un HTML local que reproduce una página del dashboard (tipo Data) para sacar capturas.

Uso: python3 armar_visor.py pagina.html salida.html id=archivo.csv [id=archivo.csv ...] [--param clave=valor]
Simula la API `dash` (data, calc, draw, onData, params) con los CSV dados y usa app.css del tipo.
"""
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent

pagina = Path(sys.argv[1]).read_text(encoding="utf-8")
salida = Path(sys.argv[2])
datos, params = {}, {}
for a in sys.argv[3:]:
    if a.startswith("--param"):
        continue
    k, v = a.split("=", 1)
    if k.startswith("p:"):
        params[k[2:]] = v
    else:
        datos[k] = Path(v).read_text(encoding="utf-8")

# separar <style>, cuerpo y <script> de la página
import re
estilos = "\n".join(re.findall(r"<style>(.*?)</style>", pagina, re.S))
scripts = re.findall(r"<script>(.*?)</script>", pagina, re.S)
cuerpo = re.sub(r"<style>.*?</style>|<script>.*?</script>|<meta[^>]*>", "", pagina, flags=re.S)

mock = r"""
window.dash = (() => {
  const raw = %(datos)s;
  const files = {}; for (const [k, v] of Object.entries(raw)) files[k] = d3.csvParse(v);
  const calcs = {}, draws = {}, onDatas = []; let params = %(params)s;
  const cache = {};
  const get = (id) => {
    if (files[id]) return files[id];
    if (cache[id]) return cache[id];
    const c = calcs[id]; if (!c) return [];
    cache[id] = c.fn(...c.inputs.map(get)); return cache[id];
  };
  const api = {
    colors: ['#4fbf8f', '#6aa9ff', '#e6a23c', '#c678dd', '#ff7a90', '#56c2c2', '#b0b36b', '#9a9ca4'],
    data(id) { const d = get(id); return { status: 'ok', data: d, columns: d.columns || (d[0] ? Object.keys(d[0]) : []), meta: [] }; },
    calc(id, o) { calcs[id] = o; },
    loader() {},
    onData(fn) { onDatas.push(fn); },
    draw(name, fn) { draws[name] = fn; },
    params() { return params; },
    setParams(p) { params = { ...params, ...p }; render(); },
    resetParams() {},
    setLink() {},
    refresh() {},
  };
  function render() {
    onDatas.forEach((f) => f());
    for (const [name, fn] of Object.entries(draws)) {
      document.querySelectorAll(`[data-draw="${name}"]`).forEach((el) => {
        if (el.closest('[hidden]')) return;
        try { fn(el); } catch (e) { console.error(name, e); }
      });
    }
  }
  api._render = render;
  return api;
})();
"""

html = f"""<!doctype html>
<html lang="es" class="cds-root" data-mode="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="{AQUI / 'app.css'}">
<script src="{AQUI / 'node_modules/d3/dist/d3.min.js'}"></script>
<style>
  body {{ margin: 0; }}
  .visor {{ min-height: 100vh; background: var(--color-bg); color: var(--color-fg); font-family: var(--font-anthropic-sans); }}
  #dash-root {{ padding: 24px max(16px, 3vw); }}
{estilos}
</style></head>
<body><div class="visor"><div id="dash-root">{cuerpo}</div></div>
<script>{mock % {'datos': json.dumps(datos), 'params': json.dumps(params)}}</script>
{''.join(f'<script>{s}</script>' for s in scripts)}
<script>dash._render(); setTimeout(() => dash._render(), 50);</script>
</body></html>"""
salida.write_text(html, encoding="utf-8")
print(salida)
