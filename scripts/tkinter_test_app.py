#!/usr/bin/env python3
"""Persian Speech Intelligence — Tkinter desktop test client.

A clean local GUI for exercising the FastAPI backend without Streamlit.
Requires only the Python standard library (optional: httpx if installed).

Run:
    python scripts/tkinter_test_app.py
"""

from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import sys
import threading
import tkinter as tk
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)


# ── Theme ────────────────────────────────────────────────────────────────────
COLORS = {
    "bg": "#f4f1ea",
    "surface": "#ffffff",
    "sidebar": "#0f3d3e",
    "sidebar_hover": "#1a5f61",
    "accent": "#c4a35a",
    "accent_dark": "#a8863f",
    "text": "#1c2b2b",
    "muted": "#5c6b6b",
    "border": "#d9c9a3",
    "success": "#1a7a4c",
    "danger": "#b33a3a",
    "info": "#1a5f61",
    "card": "#faf8f3",
}

FONT_UI = ("Segoe UI", 10)
FONT_UI_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 16, "bold")
FONT_HEADING = ("Segoe UI", 12, "bold")
FONT_MONO = ("Consolas", 10)
FONT_PERSIAN = ("Segoe UI", 11)


class ApiClient:
    """Minimal HTTP client using stdlib urllib."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_prefix = "/api/v1"
        self.api_key = api_key
        self.timeout = 120

    def _headers(self, content_type: str | None = "application/json") -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _url(self, path: str, query: dict[str, Any] | None = None) -> str:
        url = f"{self.base_url}{self.api_prefix}{path}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        return url

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        req = urllib.request.Request(
            self._url(path, query),
            data=data,
            headers=headers or self._headers(),
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                ctype = resp.headers.get("Content-Type", "")
                if "application/json" in ctype:
                    return json.loads(body) if body else {}
                return body
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
                msg = payload.get("message") or payload.get("detail") or raw
            except json.JSONDecodeError:
                msg = raw or str(exc)
            raise RuntimeError(f"HTTP {exc.code}: {msg}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"اتصال برقرار نشد: {exc.reason}") from exc

    def health(self) -> dict:
        return self._request("GET", "/health")

    def ready(self) -> dict:
        return self._request("GET", "/ready")

    def stats(self) -> dict:
        return self._request("GET", "/recordings/stats")

    def list_recordings(self, limit: int = 50) -> dict:
        return self._request("GET", "/recordings", query={"limit": limit})

    def get_status(self, recording_id: str) -> dict:
        return self._request("GET", f"/recordings/{recording_id}/status")

    def get_transcript(self, recording_id: str) -> dict:
        return self._request("GET", f"/recordings/{recording_id}/transcript")

    def get_analysis(self, recording_id: str) -> dict:
        return self._request("GET", f"/recordings/{recording_id}/analysis")

    def chat(self, recording_id: str, question: str) -> dict:
        payload = json.dumps({"question": question}, ensure_ascii=False).encode("utf-8")
        return self._request("POST", f"/recordings/{recording_id}/chat", data=payload)

    def export(self, recording_id: str, fmt: str = "json") -> str:
        result = self._request(
            "GET",
            f"/recordings/{recording_id}/export",
            query={"format": fmt},
            headers=self._headers(content_type=None),
        )
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)

    def delete(self, recording_id: str) -> dict:
        return self._request("DELETE", f"/recordings/{recording_id}")

    def upload(self, filepath: Path) -> dict:
        boundary = "----PsiBoundary7MA4YWxkTrZu0gW"
        filename = filepath.name
        file_bytes = filepath.read_bytes()
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        body = b""
        body += f"--{boundary}\r\n".encode()
        body += (
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        ).encode()
        body += f"Content-Type: {content_type}\r\n\r\n".encode()
        body += file_bytes
        body += f"\r\n--{boundary}--\r\n".encode()

        headers = self._headers(content_type=f"multipart/form-data; boundary={boundary}")
        return self._request("POST", "/recordings", data=body, headers=headers)


class TestApp(tk.Tk):
    """Main Tkinter window for backend testing."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Persian Speech Intelligence — Test Client")
        self.geometry("1100x720")
        self.minsize(960, 640)
        self.configure(bg=COLORS["bg"])

        self.api = ApiClient()
        self.current_recording_id = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="آماده")
        self.backend_url = tk.StringVar(value="http://localhost:8000")
        self.api_key = tk.StringVar(value="")
        self.api_power_label = tk.StringVar(value="API: خاموش / نامشخص")
        self.worker_power_label = tk.StringVar(value="Worker: خاموش / نامشخص")
        self._nav_buttons: dict[str, tk.Button] = {}
        self._pages: dict[str, tk.Frame] = {}
        self._api_proc: subprocess.Popen | None = None
        self._worker_proc: subprocess.Popen | None = None
        self._status_poll_job: str | None = None
        self._auto_poll_active = False

        self._setup_styles()
        self._enable_global_clipboard()
        self._build_layout()
        self.show_page("dashboard")
        self.after(200, self.refresh_connection)
        self.after(1500, self._refresh_service_indicators)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Clipboard (copy / paste) ──────────────────────────────────────────────
    def _enable_global_clipboard(self) -> None:
        """Make Ctrl+C/V/X/A and right-click work reliably on Windows (incl. Persian keyboard)."""
        for seq, handler in (
            ("<Control-c>", self._event_copy),
            ("<Control-C>", self._event_copy),
            ("<Control-v>", self._event_paste),
            ("<Control-V>", self._event_paste),
            ("<Control-x>", self._event_cut),
            ("<Control-X>", self._event_cut),
            ("<Control-a>", self._event_select_all),
            ("<Control-A>", self._event_select_all),
            ("<Shift-Insert>", self._event_paste),
            ("<Control-Insert>", self._event_copy),
        ):
            self.bind_class("Entry", seq, handler)
            self.bind_class("TEntry", seq, handler)
            self.bind_class("Text", seq, handler)
            self.bind_all(seq, handler)

        self.bind_class("Entry", "<Button-3>", self._show_entry_context_menu)
        self.bind_class("TEntry", "<Button-3>", self._show_entry_context_menu)
        self.bind_class("Text", "<Button-3>", self._show_text_context_menu)

    def _focused_editable(self):
        w = self.focus_get()
        if w is None:
            return None
        cls = w.winfo_class()
        if cls in {"Entry", "TEntry", "Text"}:
            return w
        return None

    def _event_copy(self, event=None):
        w = event.widget if event is not None else self._focused_editable()
        if w is None:
            return None
        try:
            if w.winfo_class() == "Text":
                text = w.get("sel.first", "sel.last")
            else:
                if w.selection_present():
                    text = w.selection_get()
                else:
                    text = w.get()
            if text:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update_idletasks()
        except tk.TclError:
            pass
        return "break"

    def _event_paste(self, event=None):
        w = event.widget if event is not None else self._focused_editable()
        if w is None:
            return None
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            if w.winfo_class() == "Text":
                try:
                    w.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                w.insert("insert", text)
            else:
                try:
                    if w.selection_present():
                        w.delete("sel.first", "sel.last")
                except tk.TclError:
                    pass
                w.insert("insert", text)
        except tk.TclError:
            pass
        return "break"

    def _event_cut(self, event=None):
        self._event_copy(event)
        w = event.widget if event is not None else self._focused_editable()
        if w is None:
            return "break"
        try:
            if w.winfo_class() == "Text":
                w.delete("sel.first", "sel.last")
            elif w.selection_present():
                w.delete("sel.first", "sel.last")
        except tk.TclError:
            pass
        return "break"

    def _event_select_all(self, event=None):
        w = event.widget if event is not None else self._focused_editable()
        if w is None:
            return None
        try:
            if w.winfo_class() == "Text":
                w.tag_add("sel", "1.0", "end-1c")
            else:
                w.selection_range(0, "end")
                w.icursor("end")
        except tk.TclError:
            pass
        return "break"

    def _show_entry_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="کپی  (Ctrl+C)", command=lambda: self._event_copy(event))
        menu.add_command(label="چسباندن  (Ctrl+V)", command=lambda: self._event_paste(event))
        menu.add_command(label="بریدن  (Ctrl+X)", command=lambda: self._event_cut(event))
        menu.add_separator()
        menu.add_command(label="انتخاب همه  (Ctrl+A)", command=lambda: self._event_select_all(event))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _show_text_context_menu(self, event):
        return self._show_entry_context_menu(event)

    def _copy_to_clipboard(self, text: str, notify: bool = True) -> None:
        text = (text or "").strip()
        if not text:
            if notify:
                messagebox.showinfo("کپی", "متنی برای کپی وجود ندارد.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()
        if notify:
            self.status_text.set("شناسه کپی شد")
            messagebox.showinfo("کپی شد", f"در کلیپ‌بورد قرار گرفت:\n{text}")

    # ── Styling ───────────────────────────────────────────────────────────────
    def _setup_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Card.TFrame", background=COLORS["surface"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=FONT_UI)
        style.configure(
            "Title.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["sidebar"],
            font=FONT_TITLE,
        )
        style.configure(
            "Heading.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["sidebar"],
            font=FONT_HEADING,
        )
        style.configure(
            "Muted.TLabel",
            background=COLORS["bg"],
            foreground=COLORS["muted"],
            font=FONT_UI,
        )
        style.configure(
            "Card.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            font=FONT_UI,
        )
        style.configure(
            "Metric.TLabel",
            background=COLORS["card"],
            foreground=COLORS["sidebar"],
            font=("Segoe UI", 18, "bold"),
        )
        style.configure(
            "MetricCaption.TLabel",
            background=COLORS["card"],
            foreground=COLORS["muted"],
            font=FONT_UI,
        )
        style.configure(
            "Accent.TButton",
            font=FONT_UI_BOLD,
            padding=(14, 8),
        )
        style.map(
            "Accent.TButton",
            background=[("active", COLORS["accent_dark"]), ("!disabled", COLORS["accent"])],
            foreground=[("!disabled", COLORS["sidebar"])],
        )
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 8), font=FONT_UI_BOLD)
        style.configure(
            "Treeview",
            background=COLORS["surface"],
            fieldbackground=COLORS["surface"],
            foreground=COLORS["text"],
            rowheight=28,
            font=FONT_UI,
        )
        style.configure("Treeview.Heading", font=FONT_UI_BOLD, background=COLORS["card"])
        style.configure("Horizontal.TProgressbar", troughcolor=COLORS["border"], background=COLORS["info"])

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_layout(self) -> None:
        # Top bar
        top = tk.Frame(self, bg=COLORS["sidebar"], height=56)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        tk.Label(
            top,
            text="🎙  Persian Speech Intelligence",
            bg=COLORS["sidebar"],
            fg="#f7f3e8",
            font=FONT_TITLE,
        ).pack(side="left", padx=20, pady=12)

        tk.Label(
            top,
            textvariable=self.status_text,
            bg=COLORS["sidebar"],
            fg=COLORS["accent"],
            font=FONT_UI,
        ).pack(side="right", padx=20)

        # Body: sidebar + content
        body = tk.Frame(self, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=COLORS["sidebar"], width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        nav_items = [
            ("dashboard", "📊  داشبورد"),
            ("upload", "⬆️  آپلود صوت"),
            ("transcript", "📝  رونوشت"),
            ("analysis", "🧠  تحلیل AI"),
            ("chat", "💬  پرسش‌وپاسخ"),
            ("export", "📦  خروجی / حذف"),
            ("services", "⏻  روشن / خاموش"),
            ("settings", "⚙️  تنظیمات"),
        ]
        for key, label in nav_items:
            btn = tk.Button(
                sidebar,
                text=label,
                anchor="w",
                bg=COLORS["sidebar"],
                fg="#f7f3e8",
                activebackground=COLORS["sidebar_hover"],
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                font=FONT_UI_BOLD,
                padx=18,
                pady=12,
                cursor="hand2",
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x", pady=2, padx=8)
            self._nav_buttons[key] = btn

        tk.Label(
            sidebar,
            text="Test Client v0.1",
            bg=COLORS["sidebar"],
            fg="#7aa3a4",
            font=("Segoe UI", 8),
        ).pack(side="bottom", pady=12)

        self.content = tk.Frame(body, bg=COLORS["bg"])
        self.content.pack(side="left", fill="both", expand=True, padx=18, pady=16)

        self._pages["dashboard"] = self._build_dashboard()
        self._pages["upload"] = self._build_upload()
        self._pages["transcript"] = self._build_transcript()
        self._pages["analysis"] = self._build_analysis()
        self._pages["chat"] = self._build_chat()
        self._pages["export"] = self._build_export()
        self._pages["services"] = self._build_services()
        self._pages["settings"] = self._build_settings()

    def show_page(self, key: str) -> None:
        for page in self._pages.values():
            page.pack_forget()
        self._pages[key].pack(fill="both", expand=True)
        for name, btn in self._nav_buttons.items():
            if name == key:
                btn.configure(bg=COLORS["sidebar_hover"], fg=COLORS["accent"])
            else:
                btn.configure(bg=COLORS["sidebar"], fg="#f7f3e8")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _card(self, parent: tk.Misc, **pack_kwargs) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=COLORS["surface"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        if pack_kwargs:
            card.pack(**pack_kwargs)
        return card

    def _section_title(self, parent: tk.Misc, text: str) -> None:
        ttk.Label(parent, text=text, style="Title.TLabel").pack(anchor="e", pady=(0, 10))

    def _run_async(self, work, on_success=None, on_error=None) -> None:
        self.status_text.set("در حال اجرا…")

        def task() -> None:
            try:
                result = work()
            except Exception as exc:  # noqa: BLE001
                # Bind into defaults — Python clears `except` names after the block
                self.after(
                    0,
                    lambda err=exc, cb=on_error: self._on_async_error(err, cb),
                )
                return
            self.after(
                0,
                lambda res=result, cb=on_success: self._on_async_ok(res, cb),
            )

        threading.Thread(target=task, daemon=True).start()

    def _on_async_ok(self, result, on_success) -> None:
        self.status_text.set("آماده")
        if on_success:
            on_success(result)

    def _on_async_error(self, exc: Exception, on_error) -> None:
        self.status_text.set("خطا")
        if on_error:
            on_error(exc)
        else:
            messagebox.showerror("خطا", self._friendly_error(exc))

    def _friendly_error(self, exc: Exception) -> str:
        msg = str(exc)
        low = msg.lower()
        if "10061" in msg or "refused" in low:
            return (
                "سرور API روشن نیست.\n"
                "از بخش «روشن / خاموش» ابتدا API را روشن کنید."
            )
        if "404" in msg and "analysis" in low:
            return (
                "تحلیل هنوز آماده نیست.\n\n"
                "آپلود انجام شده، ولی پردازش (Worker) هنوز تمام نشده.\n"
                "۱) بخش «روشن / خاموش» → Worker را روشن کنید\n"
                "۲) صبر کنید تا در صفحه آپلود وضعیت completed شود\n"
                "۳) دوباره تحلیل را بارگذاری کنید"
            )
        if "404" in msg and "not found" in low:
            return "این فایل پیدا نشد. دوباره از داشبورد انتخاب کنید."
        if "409" in msg or "not finished" in low:
            return (
                "پردازش این فایل هنوز تمام نشده است.\n"
                "صبر کنید تا وضعیت completed شود، بعد دوباره تلاش کنید."
            )
        if "ffmpeg" in low:
            return "FFmpeg نصب نیست یا در PATH نیست. با winget install Gyan.FFmpeg نصب کنید."
        return msg

    def _require_completed(self, rid: str, feature_name: str, on_ready) -> None:
        """Check processing status before loading transcript/analysis/chat."""

        def work():
            return self.api.get_status(rid)

        def ok(status):
            state = status.get("status") or "—"
            progress = int(status.get("progress") or 0)
            if state == "completed":
                on_ready()
                return
            if state == "failed":
                messagebox.showerror(
                    feature_name,
                    f"پردازش ناموفق بود.\n{status.get('error_message') or ''}",
                )
                return
            messagebox.showinfo(
                feature_name,
                (
                    f"فایل آپلود شده، ولی هنوز پردازش کامل نشده است.\n\n"
                    f"وضعیت فعلی: {state}\n"
                    f"پیشرفت: {progress}%\n\n"
                    "Worker را از بخش «روشن / خاموش» روشن کنید و\n"
                    "در صفحه آپلود صبر کنید تا وضعیت خودکار completed شود."
                ),
            )

        def err(exc):
            messagebox.showerror(feature_name, self._friendly_error(exc))

        self._run_async(work, on_success=ok, on_error=err)

    def _set_text(self, widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="normal")

    def refresh_connection(self) -> None:
        self.api.base_url = self.backend_url.get().rstrip("/")
        self.api.api_key = self.api_key.get().strip()

        def work():
            return self.api.health(), self.api.ready()

        def ok(result):
            health, ready = result
            self.health_label.configure(
                text=f"وضعیت: {health.get('status', '?')}  |  "
                f"{health.get('app', '')} v{health.get('version', '')}",
                fg=COLORS["success"],
            )
            db = "✓" if ready.get("database") else "✗"
            storage = "✓" if ready.get("storage") else "✗"
            self.ready_label.configure(
                text=f"Ready: {ready.get('status')}  ·  DB {db}  ·  Storage {storage}",
                fg=COLORS["info"] if ready.get("status") == "ready" else COLORS["danger"],
            )
            self.refresh_dashboard()

        def err(exc):
            msg = str(exc)
            if "10061" in msg or "refused" in msg.lower():
                tip = (
                    "سرور API روشن نیست (پورت 8000).\n\n"
                    "در یک ترمینال جدا اجرا کنید:\n"
                    "  .\\scripts\\start_backend_local.ps1\n"
                    "یا:\n"
                    "  cd backend\n"
                    "  .\\.venv\\Scripts\\python -m uvicorn app.main:app --port 8000\n\n"
                    f"جزئیات: {msg}"
                )
                self.health_label.configure(
                    text="Backend روشن نیست — ابتدا API را استارت کنید (پورت 8000)",
                    fg=COLORS["danger"],
                )
                self.ready_label.configure(text="Ready: —", fg=COLORS["muted"])
                messagebox.showwarning("اتصال به Backend", tip)
                return
            self.health_label.configure(text=f"Backend در دسترس نیست — {msg}", fg=COLORS["danger"])
            self.ready_label.configure(text="Ready: —", fg=COLORS["muted"])

        self._run_async(work, on_success=ok, on_error=err)

    # ── Pages ─────────────────────────────────────────────────────────────────
    def _build_dashboard(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=COLORS["bg"])
        self._section_title(page, "داشبورد")

        conn = self._card(page, fill="x", pady=(0, 12))
        self.health_label = tk.Label(
            conn, text="در حال بررسی اتصال…", bg=COLORS["surface"], fg=COLORS["muted"], font=FONT_UI
        )
        self.health_label.pack(anchor="e")
        self.ready_label = tk.Label(
            conn, text="Ready: —", bg=COLORS["surface"], fg=COLORS["muted"], font=FONT_UI
        )
        self.ready_label.pack(anchor="e", pady=(4, 0))
        ttk.Button(conn, text="بروزرسانی اتصال", command=self.refresh_connection).pack(
            anchor="w", pady=(10, 0)
        )

        metrics = tk.Frame(page, bg=COLORS["bg"])
        metrics.pack(fill="x", pady=(0, 12))
        self.metric_vars = {
            "total": tk.StringVar(value="—"),
            "completed": tk.StringVar(value="—"),
            "processing": tk.StringVar(value="—"),
            "pending": tk.StringVar(value="—"),
            "failed": tk.StringVar(value="—"),
        }
        captions = [
            ("total", "کل فایل‌ها"),
            ("completed", "تکمیل‌شده"),
            ("processing", "در حال پردازش"),
            ("pending", "در صف"),
            ("failed", "ناموفق"),
        ]
        for key, caption in captions:
            box = tk.Frame(
                metrics,
                bg=COLORS["card"],
                highlightbackground=COLORS["border"],
                highlightthickness=1,
                padx=12,
                pady=12,
            )
            box.pack(side="left", expand=True, fill="x", padx=4)
            ttk.Label(box, textvariable=self.metric_vars[key], style="Metric.TLabel").pack()
            ttk.Label(box, text=caption, style="MetricCaption.TLabel").pack()

        list_card = self._card(page, fill="both", expand=True)
        ttk.Label(list_card, text="آخرین فایل‌ها", style="Heading.TLabel").pack(anchor="e", pady=(0, 8))

        cols = ("filename", "status", "duration", "id")
        self.recordings_tree = ttk.Treeview(
            list_card, columns=cols, show="headings", height=12
        )
        self.recordings_tree.heading("filename", text="نام فایل")
        self.recordings_tree.heading("status", text="وضعیت")
        self.recordings_tree.heading("duration", text="مدت")
        self.recordings_tree.heading("id", text="شناسه")
        self.recordings_tree.column("filename", width=280, anchor="e")
        self.recordings_tree.column("status", width=110, anchor="center")
        self.recordings_tree.column("duration", width=80, anchor="center")
        self.recordings_tree.column("id", width=280, anchor="center")
        self.recordings_tree.pack(fill="both", expand=True)
        self.recordings_tree.bind("<<TreeviewSelect>>", self._on_recording_select)
        self.recordings_tree.bind("<Double-1>", self._copy_selected_recording_id)
        self.recordings_tree.bind("<Control-c>", self._copy_selected_recording_id)
        self.recordings_tree.bind("<Control-C>", self._copy_selected_recording_id)
        self.recordings_tree.bind("<Button-3>", self._dashboard_context_menu)

        btns = tk.Frame(list_card, bg=COLORS["surface"])
        btns.pack(fill="x", pady=(10, 0))
        ttk.Button(btns, text="بروزرسانی لیست", command=self.refresh_dashboard).pack(side="left")
        ttk.Button(btns, text="انتخاب + کپی شناسه", command=self._use_selected_recording).pack(
            side="left", padx=8
        )
        ttk.Button(btns, text="فقط کپی شناسه", command=self._copy_selected_recording_id).pack(
            side="left", padx=8
        )
        tk.Label(
            list_card,
            text="نکته: دوبار کلیک یا Ctrl+C روی ردیف = کپی شناسه",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
            anchor="e",
        ).pack(fill="x", pady=(8, 0))

        return page

    def refresh_dashboard(self) -> None:
        def work():
            return self.api.stats(), self.api.list_recordings()

        def ok(result):
            stats, listing = result
            self.metric_vars["total"].set(str(stats.get("total_recordings", 0)))
            self.metric_vars["completed"].set(str(stats.get("completed", 0)))
            self.metric_vars["processing"].set(str(stats.get("processing", 0)))
            self.metric_vars["pending"].set(str(stats.get("pending", 0)))
            self.metric_vars["failed"].set(str(stats.get("failed", 0)))

            for item in self.recordings_tree.get_children():
                self.recordings_tree.delete(item)
            for row in listing.get("items") or []:
                duration = row.get("duration_seconds")
                dur = f"{duration:.1f}s" if duration is not None else "—"
                self.recordings_tree.insert(
                    "",
                    "end",
                    values=(
                        row.get("original_filename", ""),
                        row.get("processing_status", ""),
                        dur,
                        row.get("id", ""),
                    ),
                )

        self._run_async(work, on_success=ok)

    def _on_recording_select(self, _event=None) -> None:
        sel = self.recordings_tree.selection()
        if not sel:
            return
        values = self.recordings_tree.item(sel[0], "values")
        if values and len(values) >= 4:
            self.current_recording_id.set(values[3])

    def _selected_recording_id(self) -> str:
        sel = self.recordings_tree.selection()
        if not sel:
            return ""
        values = self.recordings_tree.item(sel[0], "values")
        return str(values[3]) if values and len(values) >= 4 else ""

    def _copy_selected_recording_id(self, _event=None):
        rid = self._selected_recording_id()
        if not rid:
            messagebox.showinfo("کپی", "یک ردیف را انتخاب کنید.")
            return "break"
        self.current_recording_id.set(rid)
        self._copy_to_clipboard(rid)
        return "break"

    def _dashboard_context_menu(self, event):
        row = self.recordings_tree.identify_row(event.y)
        if row:
            self.recordings_tree.selection_set(row)
            self._on_recording_select()
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="کپی شناسه", command=self._copy_selected_recording_id)
        menu.add_command(label="انتخاب برای صفحات دیگر", command=self._use_selected_recording)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _use_selected_recording(self) -> None:
        rid = self._selected_recording_id()
        if not rid:
            messagebox.showinfo("انتخاب", "یک ردیف را انتخاب کنید.")
            return
        self.current_recording_id.set(rid)
        self._copy_to_clipboard(rid, notify=False)
        messagebox.showinfo("انتخاب شد", f"شناسه انتخاب و کپی شد:\n{rid}")

    def _build_upload(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=COLORS["bg"])
        self._section_title(page, "آپلود فایل صوتی")

        card = self._card(page, fill="x")
        self.upload_path = tk.StringVar(value="")
        row = tk.Frame(card, bg=COLORS["surface"])
        row.pack(fill="x")
        path_entry = ttk.Entry(row, textvariable=self.upload_path, font=FONT_UI)
        path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(row, text="انتخاب فایل…", command=self._pick_audio).pack(side="left")

        ttk.Label(
            card,
            text="فرمت‌های مجاز: WAV · MP3 · M4A · FLAC · OGG",
            style="Card.TLabel",
        ).pack(anchor="e", pady=(10, 0))

        ttk.Button(card, text="شروع آپلود و پردازش", style="Accent.TButton", command=self._do_upload).pack(
            anchor="w", pady=(14, 0)
        )

        status_card = self._card(page, fill="x", pady=(12, 0))
        ttk.Label(status_card, text="وضعیت پردازش (خودکار)", style="Heading.TLabel").pack(anchor="e")
        id_row = tk.Frame(status_card, bg=COLORS["surface"])
        id_row.pack(fill="x", pady=8)
        ttk.Label(id_row, text="Recording ID:", style="Card.TLabel").pack(side="left")
        id_entry = ttk.Entry(id_row, textvariable=self.current_recording_id, font=FONT_MONO)
        id_entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(
            id_row,
            text="کپی شناسه",
            command=lambda: self._copy_to_clipboard(self.current_recording_id.get()),
        ).pack(side="left")

        self.progress = ttk.Progressbar(status_card, maximum=100, mode="determinate")
        self.progress.pack(fill="x", pady=(4, 8))
        self.upload_status_label = tk.Label(
            status_card,
            text="هنوز فایلی آپلود نشده است. بعد از آپلود، وضعیت خودکار بروزرسانی می‌شود.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=FONT_UI,
            justify="right",
            anchor="e",
        )
        self.upload_status_label.pack(fill="x")

        return page

    def _pick_audio(self) -> None:
        path = filedialog.askopenfilename(
            title="انتخاب فایل صوتی",
            filetypes=[
                ("Audio", "*.wav *.mp3 *.m4a *.flac *.ogg"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.upload_path.set(path)

    def _do_upload(self) -> None:
        path = Path(self.upload_path.get().strip())
        if not path.exists():
            messagebox.showwarning("فایل", "مسیر فایل معتبر نیست.")
            return

        def work():
            return self.api.upload(path)

        def ok(result):
            rid = str(result.get("recording_id", ""))
            self.current_recording_id.set(rid)
            self._copy_to_clipboard(rid, notify=False)
            self.upload_status_label.configure(
                text=(
                    f"آپلود کامل شد · در صف پردازش\n"
                    f"Job: {result.get('job_id')} · وضعیت: {result.get('status')}\n"
                    "در حال پیگیری خودکار…"
                ),
                fg=COLORS["success"],
            )
            self.progress["value"] = 5
            self.status_text.set("آپلود شد — پیگیری خودکار")
            self._start_auto_status_poll(rid)

        self._run_async(work, on_success=ok)

    def _stop_auto_status_poll(self) -> None:
        self._auto_poll_active = False
        if self._status_poll_job is not None:
            try:
                self.after_cancel(self._status_poll_job)
            except Exception:
                pass
            self._status_poll_job = None

    def _start_auto_status_poll(self, recording_id: str) -> None:
        self._stop_auto_status_poll()
        self._auto_poll_active = True
        self._poll_status_once(recording_id, auto=True)

    def _poll_status_once(self, recording_id: str, *, auto: bool = False) -> None:
        rid = (recording_id or "").strip()
        if not rid:
            return

        def work():
            return self.api.get_status(rid)

        def ok(status):
            progress = int(status.get("progress") or 0)
            self.progress["value"] = progress
            step = status.get("current_step") or "—"
            state = status.get("status") or "—"
            err = status.get("error_message")
            tracking = " · پیگیری خودکار فعال" if auto and self._auto_poll_active else ""
            text = (
                f"وضعیت: {state}  ·  پیشرفت: {progress}%  ·  مرحله: {step}{tracking}"
            )
            color = COLORS["info"]
            done = False
            if state == "completed":
                color = COLORS["success"]
                text = f"✓ پردازش کامل شد ({progress}%)\nمی‌توانید رونوشت و تحلیل را ببینید."
                done = True
                self.status_text.set("پردازش کامل شد")
                messagebox.showinfo(
                    "تمام شد",
                    "پردازش فایل کامل شد.\nحالا می‌توانید به رونوشت یا تحلیل AI بروید.",
                )
            elif state == "failed":
                color = COLORS["danger"]
                text = f"✗ پردازش ناموفق\n{err or ''}"
                done = True
                self.status_text.set("پردازش ناموفق")
                messagebox.showerror("خطا در پردازش", err or "پردازش شکست خورد.")
            else:
                self.status_text.set(f"{state} — {progress}%")

            self.upload_status_label.configure(text=text, fg=color)

            if auto and self._auto_poll_active and not done:
                self._status_poll_job = self.after(
                    2000,
                    lambda: self._poll_status_once(rid, auto=True),
                )
            elif done:
                self._stop_auto_status_poll()
                self.refresh_dashboard()

        def err(exc):
            self.upload_status_label.configure(
                text=self._friendly_error(exc),
                fg=COLORS["danger"],
            )
            if auto and self._auto_poll_active:
                # Keep retrying while API might be restarting
                self._status_poll_job = self.after(
                    3000,
                    lambda: self._poll_status_once(rid, auto=True),
                )

        self._run_async(work, on_success=ok, on_error=err)

    def _build_transcript(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=COLORS["bg"])
        self._section_title(page, "نمایش رونوشت")

        top = self._card(page, fill="x")
        row = tk.Frame(top, bg=COLORS["surface"])
        row.pack(fill="x")
        ttk.Label(row, text="Recording ID:", style="Card.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=self.current_recording_id, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(row, text="بارگذاری", command=self._load_transcript).pack(side="left")

        search_row = tk.Frame(top, bg=COLORS["surface"])
        search_row.pack(fill="x", pady=(10, 0))
        self.transcript_query = tk.StringVar()
        ttk.Label(search_row, text="جستجو:", style="Card.TLabel").pack(side="left")
        ttk.Entry(search_row, textvariable=self.transcript_query, font=FONT_PERSIAN).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(search_row, text="اعمال فیلتر", command=self._filter_transcript).pack(side="left")

        body = self._card(page, fill="both", expand=True, pady=(12, 0))
        self.transcript_full = tk.Text(
            body,
            height=8,
            wrap="word",
            font=FONT_PERSIAN,
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief="flat",
            padx=10,
            pady=8,
        )
        self.transcript_full.pack(fill="x", pady=(0, 10))
        self.transcript_full.tag_configure("rtl", justify="right")

        self.segments_list = tk.Listbox(
            body,
            font=FONT_PERSIAN,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            selectbackground=COLORS["info"],
            activestyle="none",
            height=14,
        )
        self.segments_list.pack(fill="both", expand=True)
        self._transcript_segments: list[dict] = []

        return page

    def _load_transcript(self) -> None:
        rid = self.current_recording_id.get().strip()
        if not rid:
            messagebox.showwarning("شناسه", "Recording ID لازم است.")
            return

        def fetch():
            def work():
                return self.api.get_transcript(rid)

            def ok(data):
                full = data.get("full_text_normalized") or data.get("full_text") or ""
                if not full and not (data.get("segments") or []):
                    messagebox.showinfo(
                        "رونوشت",
                        "پردازش تمام شده ولی رونوشتی تولید نشده "
                        "(مثلاً فایل بدون گفتار فارسی واضح).",
                    )
                self._set_text(self.transcript_full, full or "—")
                self.transcript_full.tag_add("rtl", "1.0", "end")
                self._transcript_segments = data.get("segments") or []
                self._render_segments(self._transcript_segments)

            self._run_async(
                work,
                on_success=ok,
                on_error=lambda e: messagebox.showerror("رونوشت", self._friendly_error(e)),
            )

        self._require_completed(rid, "رونوشت", fetch)

    def _filter_transcript(self) -> None:
        q = self.transcript_query.get().strip()
        if not q:
            self._render_segments(self._transcript_segments)
            return
        filtered = [
            s
            for s in self._transcript_segments
            if q in (s.get("normalized_text") or "") or q in (s.get("original_text") or "")
        ]
        self._render_segments(filtered)

    def _render_segments(self, segments: list[dict]) -> None:
        self.segments_list.delete(0, "end")
        for seg in segments:
            start = float(seg.get("start_time") or 0)
            end = float(seg.get("end_time") or 0)
            text = seg.get("normalized_text") or seg.get("original_text") or ""
            self.segments_list.insert("end", f"[{start:06.1f} → {end:06.1f}]  {text}")

    def _build_analysis(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=COLORS["bg"])
        self._section_title(page, "تحلیل هوش مصنوعی")

        top = self._card(page, fill="x")
        row = tk.Frame(top, bg=COLORS["surface"])
        row.pack(fill="x")
        ttk.Label(row, text="Recording ID:", style="Card.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=self.current_recording_id, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(row, text="بارگذاری تحلیل", command=self._load_analysis).pack(side="left")

        body = self._card(page, fill="both", expand=True, pady=(12, 0))
        self.analysis_text = tk.Text(
            body,
            wrap="word",
            font=FONT_PERSIAN,
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief="flat",
            padx=12,
            pady=10,
        )
        self.analysis_text.pack(fill="both", expand=True)
        self.analysis_text.tag_configure("rtl", justify="right")
        self.analysis_text.tag_configure("h", font=FONT_HEADING, foreground=COLORS["sidebar"])
        return page

    def _load_analysis(self) -> None:
        rid = self.current_recording_id.get().strip()
        if not rid:
            messagebox.showwarning("شناسه", "Recording ID لازم است.")
            return

        def fetch():
            def work():
                return self.api.get_analysis(rid)

            def ok(data):
                lines: list[str] = []
                lines.append("■ خلاصه کوتاه")
                lines.append(data.get("short_summary") or "—")
                lines.append("")
                lines.append("■ خلاصه تفصیلی")
                detailed = data.get("detailed_summary") or {}
                if isinstance(detailed, dict):
                    lines.append(f"بحث اصلی: {detailed.get('main_discussion') or '—'}")
                    for label, key in [
                        ("نکات مهم", "important_points"),
                        ("تصمیم‌ها", "decisions"),
                        ("اقدامات", "action_items"),
                        ("سؤالات باز", "open_questions"),
                        ("نتیجه‌گیری", "final_conclusions"),
                    ]:
                        items = detailed.get(key) or []
                        lines.append(f"\n{label}:")
                        if items:
                            lines.extend(f"  • {x}" for x in items)
                        else:
                            lines.append("  —")
                lines.append("\n■ موضوعات")
                for topic in data.get("topics") or []:
                    if isinstance(topic, dict):
                        lines.append(f"  • {topic.get('name')}: {topic.get('description')}")
                    else:
                        lines.append(f"  • {topic}")
                lines.append("\n■ احساسات زبانی")
                sentiment = data.get("sentiment") or {}
                if isinstance(sentiment, dict):
                    lines.append(f"  برچسب: {sentiment.get('label')}")
                    lines.append(f"  توضیح: {sentiment.get('explanation')}")
                    if sentiment.get("disclaimer"):
                        lines.append(f"  نکته: {sentiment.get('disclaimer')}")
                lines.append("\n■ اقدامات")
                lines.append(
                    json.dumps(data.get("action_items") or [], ensure_ascii=False, indent=2)
                )
                lines.append("\n■ تصمیم‌ها")
                lines.append(json.dumps(data.get("decisions") or [], ensure_ascii=False, indent=2))
                lines.append("\n■ موجودیت‌ها")
                lines.append(
                    json.dumps(data.get("extracted_entities") or {}, ensure_ascii=False, indent=2)
                )

                content = "\n".join(lines)
                self._set_text(self.analysis_text, content)
                self.analysis_text.tag_add("rtl", "1.0", "end")

            self._run_async(
                work,
                on_success=ok,
                on_error=lambda e: messagebox.showerror("تحلیل", self._friendly_error(e)),
            )

        self._require_completed(rid, "تحلیل AI", fetch)

    def _build_chat(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=COLORS["bg"])
        self._section_title(page, "پرسش‌وپاسخ مستند")

        top = self._card(page, fill="x")
        row = tk.Frame(top, bg=COLORS["surface"])
        row.pack(fill="x")
        ttk.Label(row, text="Recording ID:", style="Card.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=self.current_recording_id, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=8
        )

        qrow = tk.Frame(top, bg=COLORS["surface"])
        qrow.pack(fill="x", pady=(10, 0))
        self.question_var = tk.StringVar(value="جلسه درباره چه موضوعی بود؟")
        ttk.Entry(qrow, textvariable=self.question_var, font=FONT_PERSIAN).pack(
            side="left", fill="x", expand=True, padx=(0, 8)
        )
        ttk.Button(qrow, text="ارسال سؤال", style="Accent.TButton", command=self._ask).pack(
            side="left"
        )

        body = self._card(page, fill="both", expand=True, pady=(12, 0))
        self.chat_log = tk.Text(
            body,
            wrap="word",
            font=FONT_PERSIAN,
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief="flat",
            padx=12,
            pady=10,
        )
        self.chat_log.pack(fill="both", expand=True)
        self.chat_log.tag_configure("rtl", justify="right")
        self.chat_log.tag_configure("q", foreground=COLORS["sidebar"], font=FONT_UI_BOLD)
        self.chat_log.tag_configure("a", foreground=COLORS["text"])
        self.chat_log.tag_configure("e", foreground=COLORS["muted"], font=("Segoe UI", 9))
        return page

    def _ask(self) -> None:
        rid = self.current_recording_id.get().strip()
        question = self.question_var.get().strip()
        if not rid or not question:
            messagebox.showwarning("ورودی", "شناسه و سؤال الزامی است.")
            return

        def fetch():
            def work():
                return self.api.chat(rid, question)

            def ok(data):
                self.chat_log.insert("end", f"سؤال: {data.get('question')}\n", ("q", "rtl"))
                self.chat_log.insert("end", f"پاسخ: {data.get('answer')}\n", ("a", "rtl"))
                grounded = "مستند" if data.get("grounded") else "امتناع / بدون شواهد کافی"
                self.chat_log.insert("end", f"وضعیت: {grounded}\n", ("e", "rtl"))
                for ev in data.get("evidence") or []:
                    self.chat_log.insert(
                        "end",
                        f"  شاهد [{ev.get('start_time')}→{ev.get('end_time')}]: {ev.get('text')}\n",
                        ("e", "rtl"),
                    )
                self.chat_log.insert("end", "\n" + ("─" * 48) + "\n\n")
                self.chat_log.see("end")

            self._run_async(
                work,
                on_success=ok,
                on_error=lambda e: messagebox.showerror("پرسش‌وپاسخ", self._friendly_error(e)),
            )

        self._require_completed(rid, "پرسش‌وپاسخ", fetch)

    def _build_export(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=COLORS["bg"])
        self._section_title(page, "خروجی و حذف")

        card = self._card(page, fill="x")
        row = tk.Frame(card, bg=COLORS["surface"])
        row.pack(fill="x")
        ttk.Label(row, text="Recording ID:", style="Card.TLabel").pack(side="left")
        ttk.Entry(row, textvariable=self.current_recording_id, font=FONT_MONO).pack(
            side="left", fill="x", expand=True, padx=8
        )

        self.export_format = tk.StringVar(value="json")
        fmt_row = tk.Frame(card, bg=COLORS["surface"])
        fmt_row.pack(fill="x", pady=12)
        ttk.Label(fmt_row, text="قالب:", style="Card.TLabel").pack(side="left")
        for fmt in ("json", "txt", "markdown"):
            ttk.Radiobutton(fmt_row, text=fmt, value=fmt, variable=self.export_format).pack(
                side="left", padx=8
            )

        btns = tk.Frame(card, bg=COLORS["surface"])
        btns.pack(fill="x")
        ttk.Button(btns, text="دانلود / ذخیره خروجی", style="Accent.TButton", command=self._do_export).pack(
            side="left"
        )
        ttk.Button(btns, text="حذف دائمی فایل", command=self._do_delete).pack(side="left", padx=10)

        preview = self._card(page, fill="both", expand=True, pady=(12, 0))
        ttk.Label(preview, text="پیش‌نمایش خروجی", style="Heading.TLabel").pack(anchor="e")
        self.export_preview = tk.Text(
            preview,
            wrap="word",
            font=FONT_MONO,
            bg=COLORS["card"],
            fg=COLORS["text"],
            relief="flat",
            padx=10,
            pady=8,
        )
        self.export_preview.pack(fill="both", expand=True, pady=(8, 0))
        return page

    def _do_export(self) -> None:
        rid = self.current_recording_id.get().strip()
        if not rid:
            messagebox.showwarning("شناسه", "Recording ID لازم است.")
            return
        fmt = self.export_format.get()

        def work():
            return self.api.export(rid, fmt)

        def ok(content: str):
            self._set_text(self.export_preview, content[:20000])
            ext = {"json": "json", "txt": "txt", "markdown": "md"}[fmt]
            path = filedialog.asksaveasfilename(
                defaultextension=f".{ext}",
                initialfile=f"{rid}.{ext}",
                filetypes=[(ext.upper(), f"*.{ext}"), ("All", "*.*")],
            )
            if path:
                Path(path).write_text(content, encoding="utf-8")
                messagebox.showinfo("ذخیره شد", path)

        self._run_async(work, on_success=ok)

    def _do_delete(self) -> None:
        rid = self.current_recording_id.get().strip()
        if not rid:
            messagebox.showwarning("شناسه", "Recording ID لازم است.")
            return
        if not messagebox.askyesno(
            "تأیید حذف",
            "این عمل فایل صوتی، رونوشت، تحلیل و ایندکس برداری را پاک می‌کند.\nادامه؟",
        ):
            return

        def work():
            return self.api.delete(rid)

        def ok(result):
            self.current_recording_id.set("")
            self._set_text(self.export_preview, result.get("message", "Deleted."))
            messagebox.showinfo("حذف شد", result.get("message", "OK"))
            self.refresh_dashboard()

        self._run_async(work, on_success=ok)

    def _build_services(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=COLORS["bg"])
        self._section_title(page, "روشن / خاموش کردن سرویس‌ها")

        tip = self._card(page, fill="x")
        tk.Label(
            tip,
            text=(
                "برای آپلود فقط API لازم است.\n"
                "برای رونوشت / تحلیل / پرسش‌وپاسخ، Worker هم باید روشن باشد.\n"
                "تا وقتی وضعیت فایل completed نشود، بخش‌های تحلیلی خطا می‌دهند."
            ),
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=FONT_PERSIAN,
            justify="right",
            anchor="e",
        ).pack(fill="x")

        # API card
        api_card = self._card(page, fill="x", pady=(12, 0))
        ttk.Label(api_card, text="FastAPI Backend", style="Heading.TLabel").pack(anchor="e")
        tk.Label(
            api_card,
            textvariable=self.api_power_label,
            bg=COLORS["surface"],
            fg=COLORS["info"],
            font=FONT_UI_BOLD,
            anchor="e",
        ).pack(fill="x", pady=6)
        api_btns = tk.Frame(api_card, bg=COLORS["surface"])
        api_btns.pack(fill="x")
        tk.Button(
            api_btns,
            text="روشن کردن API",
            bg=COLORS["success"],
            fg="white",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._start_api,
        ).pack(side="right", padx=6)
        tk.Button(
            api_btns,
            text="خاموش کردن API",
            bg=COLORS["danger"],
            fg="white",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._stop_api,
        ).pack(side="right", padx=6)

        # Worker card
        worker_card = self._card(page, fill="x", pady=(12, 0))
        ttk.Label(worker_card, text="Processing Worker", style="Heading.TLabel").pack(anchor="e")
        tk.Label(
            worker_card,
            textvariable=self.worker_power_label,
            bg=COLORS["surface"],
            fg=COLORS["info"],
            font=FONT_UI_BOLD,
            anchor="e",
        ).pack(fill="x", pady=6)
        worker_btns = tk.Frame(worker_card, bg=COLORS["surface"])
        worker_btns.pack(fill="x")
        tk.Button(
            worker_btns,
            text="روشن کردن Worker",
            bg=COLORS["success"],
            fg="white",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._start_worker,
        ).pack(side="right", padx=6)
        tk.Button(
            worker_btns,
            text="خاموش کردن Worker",
            bg=COLORS["danger"],
            fg="white",
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._stop_worker,
        ).pack(side="right", padx=6)

        both = self._card(page, fill="x", pady=(12, 0))
        both_btns = tk.Frame(both, bg=COLORS["surface"])
        both_btns.pack(fill="x")
        ttk.Button(both_btns, text="روشن کردن هر دو", command=self._start_all).pack(
            side="right", padx=6
        )
        ttk.Button(both_btns, text="خاموش کردن هر دو", command=self._stop_all).pack(
            side="right", padx=6
        )
        ttk.Button(both_btns, text="بروزرسانی وضعیت", command=self._refresh_service_indicators).pack(
            side="left"
        )
        return page

    def _backend_env(self) -> dict[str, str]:
        env = os.environ.copy()
        path = (
            os.environ.get("Path", "")
            + ";"
            + (os.environ.get("PATH", "") or "")
        )
        # Ensure machine+user PATH (FFmpeg from winget)
        machine = ""
        user = ""
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            ) as key:
                machine, _ = winreg.QueryValueEx(key, "Path")
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                try:
                    user, _ = winreg.QueryValueEx(key, "Path")
                except FileNotFoundError:
                    user = ""
        except Exception:
            pass
        env["Path"] = ";".join(p for p in (machine, user, path) if p)
        env["DATABASE_URL"] = "sqlite:///./storage/psi_local.db"
        env["STORAGE_DIR"] = str(ROOT / "storage")
        env["UPLOAD_DIR"] = str(ROOT / "storage" / "uploads")
        env["TEMP_DIR"] = str(ROOT / "storage" / "temp")
        env["VECTOR_INDEX_DIR"] = str(ROOT / "storage" / "vector_indexes")
        env["AUTH_ENABLED"] = "false"
        return env

    def _is_api_up(self) -> bool:
        try:
            self.api.base_url = self.backend_url.get().rstrip("/")
            self.api.health()
            return True
        except Exception:
            return False

    def _refresh_service_indicators(self) -> None:
        api_alive = self._api_proc is not None and self._api_proc.poll() is None
        worker_alive = self._worker_proc is not None and self._worker_proc.poll() is None
        api_http = self._is_api_up()

        if api_http:
            self.api_power_label.set("API: روشن ✓  (http://127.0.0.1:8000)")
        elif api_alive:
            self.api_power_label.set("API: در حال بالا آمدن…")
        else:
            self.api_power_label.set("API: خاموش ✗")

        if worker_alive:
            self.worker_power_label.set(f"Worker: روشن ✓  (PID {self._worker_proc.pid})")
        else:
            self.worker_power_label.set("Worker: خاموش ✗")

        self.after(3000, self._refresh_service_indicators)

    def _start_api(self) -> None:
        if self._is_api_up():
            messagebox.showinfo("API", "API از قبل روشن است.")
            self._refresh_service_indicators()
            return
        if self._api_proc is not None and self._api_proc.poll() is None:
            messagebox.showinfo("API", "API در حال اجرا است.")
            return

        (BACKEND_DIR / "storage").mkdir(parents=True, exist_ok=True)
        (ROOT / "storage" / "uploads").mkdir(parents=True, exist_ok=True)
        (ROOT / "storage" / "temp").mkdir(parents=True, exist_ok=True)
        (ROOT / "storage" / "vector_indexes").mkdir(parents=True, exist_ok=True)

        creation = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        self._api_proc = subprocess.Popen(
            [
                str(VENV_PYTHON),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=str(BACKEND_DIR),
            env=self._backend_env(),
            creationflags=creation,
        )
        self.api_power_label.set("API: در حال بالا آمدن…")
        self.status_text.set("API روشن شد")
        self.after(2000, self.refresh_connection)

    def _stop_api(self) -> None:
        self._terminate_proc(self._api_proc, "API")
        self._api_proc = None
        # Also try to free port 8000 if orphaned
        self._kill_port(8000)
        self.api_power_label.set("API: خاموش ✗")
        self.status_text.set("API خاموش شد")

    def _start_worker(self) -> None:
        if self._worker_proc is not None and self._worker_proc.poll() is None:
            messagebox.showinfo("Worker", "Worker از قبل روشن است.")
            return
        if not self._is_api_up():
            if not messagebox.askyesno(
                "Worker",
                "API روشن نیست. اول API روشن شود؟",
            ):
                return
            self._start_api()

        creation = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        self._worker_proc = subprocess.Popen(
            [str(VENV_PYTHON), "-m", "app.workers.processing_worker"],
            cwd=str(BACKEND_DIR),
            env=self._backend_env(),
            creationflags=creation,
        )
        self.worker_power_label.set(f"Worker: روشن ✓  (PID {self._worker_proc.pid})")
        self.status_text.set("Worker روشن شد")
        messagebox.showinfo(
            "Worker",
            "Worker روشن شد.\n"
            "اگر فایلی در صف pending بود، به‌زودی پردازش می‌شود.\n"
            "وضعیت در صفحه آپلود خودکار بروزرسانی می‌شود.",
        )

    def _stop_worker(self) -> None:
        self._terminate_proc(self._worker_proc, "Worker")
        self._worker_proc = None
        self.worker_power_label.set("Worker: خاموش ✗")
        self.status_text.set("Worker خاموش شد")

    def _start_all(self) -> None:
        self._start_api()
        self.after(2500, self._start_worker)

    def _stop_all(self) -> None:
        self._stop_worker()
        self._stop_api()

    def _terminate_proc(self, proc: subprocess.Popen | None, name: str) -> None:
        if proc is None:
            return
        if proc.poll() is not None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception as exc:  # noqa: BLE001
            messagebox.showwarning(name, f"توقف کامل نشد: {exc}")

    def _kill_port(self, port: int) -> None:
        try:
            out = subprocess.check_output(
                ["netstat", "-ano"],
                text=True,
                errors="ignore",
            )
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    if pid.isdigit():
                        subprocess.run(
                            ["taskkill", "/PID", pid, "/F"],
                            capture_output=True,
                            check=False,
                        )
        except Exception:
            pass

    def _on_close(self) -> None:
        # Do not auto-kill services — user may want them to keep running
        self.destroy()

    def _build_settings(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=COLORS["bg"])
        self._section_title(page, "تنظیمات اتصال")

        card = self._card(page, fill="x")
        ttk.Label(card, text="Backend URL", style="Heading.TLabel").pack(anchor="w")
        ttk.Entry(card, textvariable=self.backend_url, font=FONT_MONO).pack(fill="x", pady=(6, 12))

        ttk.Label(card, text="API Key (اختیاری)", style="Heading.TLabel").pack(anchor="w")
        ttk.Entry(card, textvariable=self.api_key, font=FONT_MONO, show="•").pack(
            fill="x", pady=(6, 12)
        )

        ttk.Button(
            card,
            text="ذخیره و تست اتصال",
            style="Accent.TButton",
            command=self.refresh_connection,
        ).pack(anchor="w")

        tip = self._card(page, fill="x", pady=(12, 0))
        ttk.Label(
            tip,
            text=(
                "راحت‌ترین روش: از منوی «روشن / خاموش» سرویس‌ها را مدیریت کنید.\n"
                "یا دستی:\n"
                "  .\\scripts\\start_backend_local.ps1\n"
                "  python -m app.workers.processing_worker"
            ),
            style="Card.TLabel",
            justify="left",
        ).pack(anchor="w")
        return page


def main() -> None:
    app = TestApp()
    app.mainloop()


if __name__ == "__main__":
    main()
