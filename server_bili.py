#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站短剧AI剪辑工具 - 本地HTTP服务 v4.0
独立引擎 (ai_short_drama_engine) | 零抖音依赖 | 日志落地 processing.log
"""

import http.server
import socketserver
import os, sys, json, threading, subprocess, time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ---- Path ----
WORK_DIR  = Path(__file__).parent.resolve()
_VENV_SP  = str(WORK_DIR / ".venv" / "lib" / "python3.11" / "site-packages")

if _VENV_SP not in sys.path:
    sys.path.insert(0, _VENV_SP)
sys.path.insert(0, str(WORK_DIR))

PORT = 8766
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".flv"}
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".js":   "application/javascript",
    ".json": "application/json",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".svg":  "image/svg+xml",
}

# ============================================================
# Helpers
# ============================================================

def _ts(): return time.strftime("%Y-%m-%d %H:%M:%S")

def _list_f(d):
    if not d.exists(): return []
    return sorted(f.name for f in d.iterdir() if f.is_file() and not f.name.startswith("."))

def _scan(d):
    if not d.exists(): return []
    dr = []
    for sd in sorted([x for x in d.iterdir() if x.is_dir() and not x.name.startswith(".")]):
        n = len([f for f in sd.iterdir() if f.suffix.lower() in VIDEO_EXTS])
        if n: dr.append({"name": sd.name, "path": str(sd), "count": n})
    if not dr:
        ff = [f for f in d.iterdir() if f.suffix.lower() in VIDEO_EXTS and not f.name.startswith(".")]
        if ff: dr.append({"name": d.name, "path": str(d), "count": len(ff)})
    return dr

def _tvc(d):
    if not d.exists(): return 0
    c = sum(1 for f in d.iterdir() if f.suffix.lower() in VIDEO_EXTS and not f.name.startswith("."))
    for sd in d.iterdir():
        if sd.is_dir() and not sd.name.startswith("."):
            c += sum(1 for f in sd.iterdir() if f.suffix.lower() in VIDEO_EXTS)
    return c

LOG_PATH = WORK_DIR / "processing.log"

# ============================================================
# Handler
# ============================================================

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(WORK_DIR), **kw)

    # ---- GET ----
    def do_GET(self):
        pq = urlparse(self.path)
        p = pq.path

        if p == "/api/log":
            return self._log()
        if p == "/api/status":
            return self._json({
                "status": "ready", "platform": "bilibili",
                "raw_count": _tvc(WORK_DIR / "raw_videos"),
                "bgm_count": len(_list_f(WORK_DIR / "bgm")),
                "out_count":  len(_list_f(WORK_DIR / "output_videos")),
                "aspect": "16:9", "resolution": "1920×1080",
            })
        if p == "/api/dramas":
            return self._json(_scan(WORK_DIR / "raw_videos"))
        if p == "/api/files":
            qs = parse_qs(pq.query)
            d = qs.get("dir", ["raw"])[0]
            m = {"raw":"raw_videos","bgm":"bgm","output":"output_videos","narration":"narration"}
            return self._json(_list_f(WORK_DIR / m.get(d, "raw_videos")))
        if p == "/api/test":
            import shutil
            ok = {"Python": sys.version.split()[0], "ffmpeg": bool(shutil.which("ffmpeg"))}
            try: from PIL import Image; ok["PIL"] = True
            except: ok["PIL"] = False
            try: from ai_short_drama_engine import has_whisper_cpp; ok["whisper"] = has_whisper_cpp()
            except: ok["whisper"] = False
            try:
                import requests as _r; r = _r.get("http://localhost:11434/api/tags", timeout=2); ok["Ollama"] = r.status_code == 200
            except: ok["Ollama"] = False
            try: from ai_short_drama_engine import CONFIG; ok["独立引擎"] = True
            except: ok["独立引擎"] = False
            return self._json(ok)
        if p == "/api/open-folder":
            qs = parse_qs(pq.query)
            d = qs.get("dir", ["raw"])[0]
            m = {"raw":"raw_videos","bgm":"bgm","output":"output_videos","narration":"narration"}
            subprocess.Popen(["open", str(WORK_DIR / m.get(d, "raw_videos"))])
            return self._json({"ok": True})
        if p in ("/", "/index.html"):
            return self._send_file(WORK_DIR / "bilibili_gui.html")
        safe = p.lstrip("/")
        fp = WORK_DIR / safe
        if not fp.exists() or not fp.resolve().is_relative_to(WORK_DIR.resolve()):
            self.send_error(404); return
        return self._send_file(fp)

    def _send_file(self, fp):
        ext = os.path.splitext(str(fp))[1].lower()
        self.send_response(200)
        self.send_header("Content-type", MIME.get(ext, "application/octet-stream"))
        self.end_headers()
        with open(fp, "rb") as f: self.wfile.write(f.read())

    def _log(self):
        if LOG_PATH.exists():
            try:
                with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                return self._json({"log": "".join(lines[-100:])})
            except Exception as e:
                return self._json({"log": f"[日志读取失败] {e}"})
        return self._json({"log": ""})

    # ---- POST ----
    def do_POST(self):
        cl = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(cl) if cl else b"{}"
        try: data = json.loads(body)
        except: data = {}
        p = urlparse(self.path).path
        if p == "/api/cut": return self._cut(data)
        if p == "/api/compliance": return self._compliance(data)
        self.send_error(404)

    def _cut(self, data):
        self.send_response(200)
        self.send_header("Content-type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def ev(t, txt):
            try:
                self.wfile.write(f"data: {json.dumps({'type':t,'text':txt})}\n\n".encode())
                self.wfile.flush()
            except: pass

        dramas = data.get("selected_dramas") or data.get("dramas") or []
        drama  = data.get("drama", "")
        if drama and drama not in dramas:
            dramas = [drama]

        cfg = {
            "selected_dramas": dramas,
            "aspect_ratio":    data.get("aspect", "16:9"),
            "width":          int(data.get("res", "1920x1080").split("x")[0]),
            "height":         int(data.get("res", "1920x1080").split("x")[1]) if "x" in data.get("res","1920x1080") else 1080,
            "min_duration":    int(data.get("min_dur", 60)),
            "max_duration":    int(data.get("max_dur", 600)),
            "beat_detection_interval": float(data.get("beat", 0.8)),
            "bgm_volume":     float(data.get("bgm_vol", 0.15)),
            "add_ending_card": data.get("ending_card", "true") == "true",
            "bilibili_zone":   data.get("zone", "short_drama"),
            "export_post_config": True,
        }
        cfg_path = str(WORK_DIR / "narration" / f"_bili_cfg_{int(time.time())}.json")
        os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

        log_fh = open(LOG_PATH, "w", encoding="utf-8")
        log_fh.write(f"[{_ts()}] 🚀 开始处理: {', '.join(dramas) if dramas else '全部'}\n")
        log_fh.write(f"[{_ts()}] 📐 {cfg['aspect_ratio']} {cfg['width']}×{cfg['height']}\n")
        log_fh.flush()

        ev("log", "🚀 B站短剧AI自动剪辑引擎启动")
        ev("log", f"📐 画幅: {cfg['aspect_ratio']} | {cfg['width']}×{cfg['height']}")
        ev("log", f"📺 剧目: {', '.join(dramas) if dramas else '全部'}")
        ev("log", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 直接调用独立引擎 (同进程)
        try:
            from ai_short_drama_engine import batch_auto_cut, log as engine_log, _bili_post_process
            import io
            # 重定向引擎日志到 SSE + 文件
            class _SSEWriter:
                def __init__(self, ev_fn, log_fh):
                    self._ev = ev_fn
                    self._fh = log_fh
                def write(self, s):
                    if s and s.strip():
                        self._fh.write(s)
                        self._fh.flush()
                        line_s = s.strip()
                        cls = "log"
                        if "❌" in line_s: cls = "error"
                        elif "⚠" in line_s: cls = "warn"
                        elif "✅" in line_s: cls = "success"
                        self._ev(cls, line_s)
                def flush(self): pass

            old_stdout = sys.stdout
            sys.stdout = _SSEWriter(ev, log_fh)
            try:
                batch_auto_cut(cfg)
            finally:
                sys.stdout = old_stdout

            # B站后处理: 合规报告 + 不合规标记
            from ai_short_drama_engine import _bili_post_process
            _bili_post_process(cfg)
            ev("done", "✅ 全部处理完成!")
            log_fh.write(f"\n[{_ts()}] 处理完成\n")
        except Exception as e:
            ev("error", f"❌ {e}")
            log_fh.write(f"\n[{_ts()}] 异常: {e}\n")
        finally:
            log_fh.flush()
            log_fh.close()

    def _compliance(self, data):
        try:
            from bilibili_compliance_checker import check_bilibili_compliance
            r = check_bilibili_compliance(
                data.get("video",""), data.get("title",""),
                data.get("narration",""), data.get("tags",[]),
                data.get("zone","short_drama"))
            return self._json(r)
        except Exception as e:
            return self._json({"error": str(e)})

    def _json(self, d):
        self.send_response(200)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(d, ensure_ascii=False).encode())


# ============================================================
# Main
# ============================================================

def main():
    os.chdir(str(WORK_DIR))
    print(f"""
╔══════════════════════════════════════════════════╗
║  📺 B站短剧剪辑工作站 v4.0                     ║
║  独立引擎 · 16:9横屏 · B站合规                  ║
║  http://localhost:{PORT}                          ║
║  📄 日志: {LOG_PATH}
╚══════════════════════════════════════════════════╝
""")
    try:
        from ai_short_drama_engine import CONFIG
        print(f"✅ 独立引擎已载入 | {CONFIG['width']}×{CONFIG['height']} | {len([x for x in dir(__import__('ai_short_drama_engine')) if not x.startswith('_')])} 个公开符号")
    except Exception as e:
        print(f"⚠️ 引擎载入失败: {e}")
    import webbrowser
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    with socketserver.TCPServer(("", PORT), Handler) as h:
        h.allow_reuse_address = True
        try: h.serve_forever()
        except KeyboardInterrupt: print("\n👋 已关闭")

if __name__ == "__main__":
    main()
