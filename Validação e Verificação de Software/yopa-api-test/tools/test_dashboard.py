#!/usr/bin/env python3
"""
Painel de testes ao vivo — Yopa API.

Sobe um servidor HTTP local que serve um "slide" com um botão grande.
Ao clicar, o botão executa a suíte pytest do projeto e exibe um painel
(BI) com:
  - contadores: total, passou, falhou, duração
  - rosca de aprovação (%)
  - barra Parte 1 vs Parte 2
  - barras de testes por arquivo

Pensado para ser projetado durante a apresentação: deixe a aba aberta e
clique no botão na hora da demonstração.

USO (rodar com a venv do projeto, que tem o pytest instalado):
    venv/bin/python tools/test_dashboard.py [porta]

O navegador abre sozinho em http://localhost:8770 (ou na porta dada).
Apenas biblioteca padrão — sem dependências, funciona offline.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8770


# ──────────────────────────────────────────────────────────────────────
# Execução do pytest + parsing do relatório JUnit XML
# ──────────────────────────────────────────────────────────────────────

def _short_name(file_path: str) -> str:
    """tests/part2/test_agent.py -> test_agent"""
    return Path(file_path).stem


def _part_of(file_path: str) -> str:
    if "part1" in file_path:
        return "part1"
    if "part2" in file_path:
        return "part2"
    return "outros"


def _file_from_testcase(tc) -> str:
    """Deriva o caminho do arquivo de teste a partir do <testcase>.

    Algumas versões do pytest emitem o atributo `file`; quando não, o
    caminho é reconstruído do `classname` (ex.: `tests.part1.test_x.TestY`
    -> `tests/part1/test_x.py`), descartando os segmentos de classe
    (que começam com letra maiúscula).
    """
    direct = tc.get("file")
    if direct:
        return direct
    classname = tc.get("classname", "")
    module_parts = []
    for seg in classname.split("."):
        if seg[:1].isupper():       # segmento de classe — para aqui
            break
        module_parts.append(seg)
    return "/".join(module_parts) + ".py" if module_parts else "desconhecido"


def parse_junit(xml_path: str) -> dict:
    """Lê o JUnit XML do pytest e agrega métricas por arquivo e por parte."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    files: dict[str, dict] = {}
    total = passed = failed = skipped = 0
    suite_time = 0.0

    for tc in root.iter("testcase"):
        fpath = _file_from_testcase(tc)
        f = files.setdefault(fpath, {
            "path": fpath, "name": _short_name(fpath), "part": _part_of(fpath),
            "total": 0, "passed": 0, "failed": 0, "time": 0.0,
        })
        f["total"] += 1
        total += 1
        t = float(tc.get("time") or 0.0)
        f["time"] += t
        suite_time += t

        if tc.find("failure") is not None or tc.find("error") is not None:
            f["failed"] += 1
            failed += 1
        elif tc.find("skipped") is not None:
            skipped += 1
        else:
            f["passed"] += 1
            passed += 1

    parts = {
        "part1": {"total": 0, "passed": 0, "failed": 0},
        "part2": {"total": 0, "passed": 0, "failed": 0},
        "outros": {"total": 0, "passed": 0, "failed": 0},
    }
    for f in files.values():
        p = parts[f["part"]]
        p["total"] += f["total"]
        p["passed"] += f["passed"]
        p["failed"] += f["failed"]

    file_list = sorted(files.values(), key=lambda x: (x["part"], x["name"]))
    for f in file_list:
        f["time"] = round(f["time"], 3)

    return {
        "ok": True,
        "total": total, "passed": passed, "failed": failed, "skipped": skipped,
        "suite_time": round(suite_time, 2),
        "parts": parts,
        "files": file_list,
    }


def run_pytest() -> dict:
    """Roda `pytest tests/` gerando JUnit XML e devolve as métricas."""
    xml_fd, xml_path = tempfile.mkstemp(suffix=".xml", prefix="yopa_junit_")
    os.close(xml_fd)
    cmd = [
        sys.executable, "-m", "pytest", "tests/",
        f"--junit-xml={xml_path}", "-q", "-p", "no:cacheprovider",
    ]
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=300,
        )
        wall = round(time.perf_counter() - start, 2)
        if not os.path.getsize(xml_path):
            tail = (proc.stderr or proc.stdout or "").strip()[-600:]
            return {"ok": False, "error": "pytest não gerou relatório.\n" + tail}
        data = parse_junit(xml_path)
        data["wall_seconds"] = wall
        data["exit_code"] = proc.returncode
        data["timestamp"] = time.strftime("%H:%M:%S")
        return data
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "pytest excedeu o tempo limite (300s)."}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    finally:
        try:
            os.unlink(xml_path)
        except OSError:
            pass


# ──────────────────────────────────────────────────────────────────────
# Página (o "slide")
# ──────────────────────────────────────────────────────────────────────

PAGE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Painel de Testes — Yopa API</title>
<style>
  :root {
    --bg:#0e1116; --panel:#161b22; --panel2:#1c2330; --line:#262d38;
    --fg:#e6edf3; --muted:#8b949e; --green:#3fb950; --red:#f85149;
    --blue:#4d8de0; --purple:#9b7bd4;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body {
    background:var(--bg); color:var(--fg);
    font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
    min-height:100vh; display:flex; align-items:center; justify-content:center;
  }
  .slide { width:min(1100px,94vw); padding:40px 0; }
  header { text-align:center; margin-bottom:34px; }
  .brand {
    font:600 12px ui-monospace,Menlo,Consolas,monospace;
    letter-spacing:.22em; color:var(--muted);
  }
  h1 { font-size:clamp(30px,5vw,52px); font-weight:700; margin-top:8px; }
  h1 span { color:var(--green); }
  .sub { color:var(--muted); margin-top:8px; font-size:15px; }
  .hidden { display:none !important; }

  .launch { text-align:center; padding:50px 0; }
  .run-btn {
    background:linear-gradient(180deg,#2ea043,#238636);
    color:#fff; border:0; cursor:pointer;
    font-size:26px; font-weight:700; letter-spacing:.04em;
    padding:26px 60px; box-shadow:0 8px 30px rgba(46,160,67,.35);
    transition:transform .12s ease, box-shadow .12s ease;
  }
  .run-btn:hover { transform:translateY(-2px); box-shadow:0 12px 36px rgba(46,160,67,.45); }
  .run-btn:active { transform:translateY(0); }
  .hint { color:var(--muted); margin-top:18px; font-size:14px; }

  .running { text-align:center; padding:60px 0; }
  .spinner {
    width:54px; height:54px; margin:0 auto 22px;
    border:5px solid var(--line); border-top-color:var(--green);
    border-radius:50%; animation:spin .8s linear infinite;
  }
  @keyframes spin { to { transform:rotate(360deg); } }
  .running p { color:var(--muted); font-size:17px; }

  .cards { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
  .card {
    background:var(--panel); border:1px solid var(--line);
    padding:22px; text-align:center;
  }
  .card-val { font-size:46px; font-weight:800; line-height:1; }
  .card-lbl {
    margin-top:8px; color:var(--muted); font-size:12px;
    text-transform:uppercase; letter-spacing:.12em;
  }
  .card.ok .card-val { color:var(--green); }
  .card.fail .card-val { color:var(--red); }

  .charts { display:grid; grid-template-columns:300px 1fr; gap:16px; margin-top:16px; }
  .panel {
    background:var(--panel); border:1px solid var(--line); padding:20px;
  }
  .panel-title {
    font:600 11px ui-monospace,Menlo,Consolas,monospace;
    letter-spacing:.16em; text-transform:uppercase; color:var(--muted);
    margin-bottom:16px;
  }
  .donut-panel { display:flex; flex-direction:column; align-items:center; }
  .donut { width:190px; height:190px; }
  .donut-bg { fill:none; stroke:var(--line); stroke-width:13; }
  .donut-fg {
    fill:none; stroke:var(--green); stroke-width:13; stroke-linecap:round;
    transition:stroke-dasharray .9s cubic-bezier(.3,1,.4,1);
  }
  .donut-pct { fill:var(--fg); font-size:26px; font-weight:800; text-anchor:middle; }
  .donut-cap {
    fill:var(--muted); font-size:8px; text-anchor:middle;
    text-transform:uppercase; letter-spacing:.16em;
  }

  .part-bar { display:flex; height:46px; overflow:hidden; border:1px solid var(--line); }
  .part-seg {
    display:flex; align-items:center; justify-content:center;
    color:#fff; font-weight:700; font-size:14px;
    transition:width .9s cubic-bezier(.3,1,.4,1);
  }
  .seg-p1 { background:var(--blue); }
  .seg-p2 { background:var(--purple); }
  .legend { display:flex; gap:22px; margin-top:14px; font-size:13px; color:var(--muted); }
  .legend i { display:inline-block; width:11px; height:11px; margin-right:7px; vertical-align:-1px; }

  .file-bars { margin-top:4px; display:flex; flex-direction:column; gap:9px; }
  .fb-row { display:grid; grid-template-columns:190px 1fr 78px; gap:14px; align-items:center; }
  .fb-name { font:13px ui-monospace,Menlo,Consolas,monospace; }
  .fb-tag {
    font-size:9px; padding:1px 6px; margin-left:6px; border-radius:2px;
    vertical-align:1px; font-family:system-ui;
  }
  .tag-p1 { background:rgba(77,141,224,.2); color:var(--blue); }
  .tag-p2 { background:rgba(155,123,212,.2); color:var(--purple); }
  .fb-track { background:var(--panel2); height:22px; display:flex; }
  .fb-fill { height:100%; transition:width .8s cubic-bezier(.3,1,.4,1); }
  .fb-fill.ok { background:var(--green); }
  .fb-fill.fail { background:var(--red); }
  .fb-count { text-align:right; color:var(--muted); font:12px ui-monospace,monospace; }

  .footer-row {
    display:flex; justify-content:space-between; align-items:center;
    margin-top:20px;
  }
  .meta { color:var(--muted); font-size:13px; }
  .rerun-btn {
    background:var(--panel2); color:var(--fg); border:1px solid var(--line);
    padding:11px 22px; cursor:pointer; font-size:14px; font-weight:600;
  }
  .rerun-btn:hover { border-color:var(--green); color:var(--green); }
  .banner {
    margin-top:16px; padding:14px 18px; font-weight:600;
    border-left:4px solid var(--green); background:rgba(63,185,80,.1);
  }
  .banner.bad { border-left-color:var(--red); background:rgba(248,81,73,.1); }
  .error {
    margin-top:24px; padding:18px; border-left:4px solid var(--red);
    background:rgba(248,81,73,.1); white-space:pre-wrap;
    font:13px ui-monospace,Menlo,Consolas,monospace;
  }
</style>
</head>
<body>
<div class="slide">
  <header>
    <div class="brand">YOPA API · CONTROLE DE QUALIDADE</div>
    <h1>Painel de Testes <span>ao vivo</span></h1>
    <p class="sub">UNIALFA — Ferramentas Automatizadas de Verificação de Software · framework <b>pytest</b></p>
  </header>

  <div id="launch" class="launch">
    <button id="run-btn" class="run-btn">&#9654;&nbsp; EXECUTAR TESTES</button>
    <p class="hint">Roda a suíte completa do projeto — Parte 1 (lógica interna) + Parte 2 (camada HTTP)</p>
  </div>

  <div id="running" class="running hidden">
    <div class="spinner"></div>
    <p>Executando <b>pytest</b>…</p>
  </div>

  <div id="dashboard" class="dashboard hidden">
    <div class="cards">
      <div class="card"><div class="card-val" id="c-total">—</div><div class="card-lbl">Testes</div></div>
      <div class="card ok"><div class="card-val" id="c-passed">—</div><div class="card-lbl">Passou</div></div>
      <div class="card fail"><div class="card-val" id="c-failed">—</div><div class="card-lbl">Falhou</div></div>
      <div class="card"><div class="card-val" id="c-time">—</div><div class="card-lbl">Duração</div></div>
    </div>

    <div class="charts">
      <div class="panel donut-panel">
        <div class="panel-title">Aprovação</div>
        <svg class="donut" viewBox="0 0 120 120">
          <circle class="donut-bg" cx="60" cy="60" r="50"/>
          <circle class="donut-fg" id="donut-fg" cx="60" cy="60" r="50"
                  transform="rotate(-90 60 60)" stroke-dasharray="0 314.16"/>
          <text class="donut-pct" id="donut-pct" x="60" y="58">—</text>
          <text class="donut-cap" x="60" y="72">aprovação</text>
        </svg>
      </div>
      <div class="panel">
        <div class="panel-title">Distribuição — Parte 1 vs Parte 2</div>
        <div class="part-bar" id="part-bar"></div>
        <div class="legend">
          <span><i style="background:#4d8de0"></i>Parte 1 — application + infrastructure</span>
          <span><i style="background:#9b7bd4"></i>Parte 2 — interfaces/http</span>
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top:16px">
      <div class="panel-title">Testes por arquivo</div>
      <div class="file-bars" id="file-bars"></div>
    </div>

    <div id="banner" class="banner"></div>
    <div class="footer-row">
      <span class="meta" id="run-meta"></span>
      <button id="rerun-btn" class="rerun-btn">&#8635; Rodar de novo</button>
    </div>
  </div>

  <div id="error" class="error hidden"></div>
</div>

<script>
  const $ = id => document.getElementById(id);
  const CIRC = 2 * Math.PI * 50;          // circunferência da rosca (r=50)
  const show = id => $(id).classList.remove('hidden');
  const hide = id => $(id).classList.add('hidden');

  async function run() {
    hide('launch'); hide('dashboard'); hide('error'); show('running');
    try {
      const resp = await fetch('/run', { method: 'POST' });
      const data = await resp.json();
      if (!data.ok) throw new Error(data.error || 'falha desconhecida');
      render(data);
    } catch (e) {
      $('error').textContent = 'Erro ao executar a suíte:\n' + e.message;
      hide('running'); show('error'); show('launch');
      return;
    }
    hide('running'); show('dashboard');
  }

  function render(d) {
    $('c-total').textContent  = d.total;
    $('c-passed').textContent = d.passed;
    $('c-failed').textContent = d.failed;
    $('c-time').textContent   = d.wall_seconds + 's';

    const pct = d.total ? d.passed / d.total : 0;
    const allGreen = d.failed === 0;
    $('donut-fg').setAttribute('stroke-dasharray', (pct * CIRC) + ' ' + CIRC);
    $('donut-fg').setAttribute('stroke', allGreen ? '#3fb950' : '#f85149');
    $('donut-pct').textContent = Math.round(pct * 100) + '%';

    // barra Parte 1 vs Parte 2
    const p1 = d.parts.part1.total, p2 = d.parts.part2.total;
    const sum = (p1 + p2) || 1;
    $('part-bar').innerHTML =
      '<div class="part-seg seg-p1" style="width:' + (p1 / sum * 100) + '%">'
        + 'Parte 1 · ' + p1 + '</div>' +
      '<div class="part-seg seg-p2" style="width:' + (p2 / sum * 100) + '%">'
        + 'Parte 2 · ' + p2 + '</div>';

    // barras por arquivo
    const maxTotal = Math.max.apply(null, d.files.map(f => f.total).concat([1]));
    $('file-bars').innerHTML = d.files.map(function (f) {
      const tag = f.part === 'part1' ? 'tag-p1' : 'tag-p2';
      const lbl = f.part === 'part1' ? 'P1' : 'P2';
      const wPass = f.passed / maxTotal * 100;
      const wFail = f.failed / maxTotal * 100;
      return '<div class="fb-row">' +
        '<div class="fb-name">' + f.name +
          '<span class="fb-tag ' + tag + '">' + lbl + '</span></div>' +
        '<div class="fb-track">' +
          '<div class="fb-fill ok" style="width:' + wPass + '%"></div>' +
          '<div class="fb-fill fail" style="width:' + wFail + '%"></div>' +
        '</div>' +
        '<div class="fb-count">' + f.passed + '/' + f.total + '</div>' +
      '</div>';
    }).join('');

    const banner = $('banner');
    if (allGreen) {
      banner.className = 'banner';
      banner.textContent = '✔ Suíte 100% verde — ' + d.passed +
        ' testes passaram em ' + d.wall_seconds + 's.';
    } else {
      banner.className = 'banner bad';
      banner.textContent = '✖ ' + d.failed + ' teste(s) falharam de ' +
        d.total + '.';
    }
    $('run-meta').textContent = 'Execução às ' + d.timestamp +
      ' · tempo de CPU dos testes: ' + d.suite_time + 's · exit code ' +
      d.exit_code;
  }

  $('run-btn').onclick = run;
  $('rerun-btn').onclick = run;
</script>
</body>
</html>
"""


# ──────────────────────────────────────────────────────────────────────
# Servidor HTTP
# ──────────────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silencia o log padrão por requisição
        pass

    def _send(self, code, body, content_type):
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path == "/run":
            print("[test_dashboard] executando pytest…")
            result = run_pytest()
            status = "OK" if result.get("ok") else "ERRO"
            print(f"[test_dashboard] {status}")
            self._send(200, json.dumps(result), "application/json; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")


def main(argv: list[str]) -> int:
    port = int(argv[0]) if argv else DEFAULT_PORT
    url = f"http://localhost:{port}"
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[test_dashboard] painel em {url}")
    print(f"[test_dashboard] projeto: {PROJECT_ROOT}")
    print("[test_dashboard] Ctrl+C para encerrar.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[test_dashboard] encerrado.")
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
