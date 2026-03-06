#!/usr/bin/env python3
"""Desktop helper to export currently opened KeyCRM dialog into a .txt file."""

from __future__ import annotations

import json
import re
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

DEFAULT_DEBUG_URL = "http://127.0.0.1:9222"


def get_cdp_websocket(debug_url: str) -> str:
    """Return Chrome DevTools websocket URL from the remote debugging endpoint."""
    version_url = f"{debug_url.rstrip('/')}/json/version"
    try:
        with urlopen(version_url, timeout=3) as response:  # nosec: B310 - local endpoint only
            data = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise ConnectionError(
            "Не вдалося підключитися до Chrome DevTools. Перевірте, що Chrome запущений з --remote-debugging-port=9222."
        ) from exc

    ws_endpoint = data.get("webSocketDebuggerUrl")
    if not ws_endpoint:
        raise ConnectionError("Chrome DevTools не повернув webSocketDebuggerUrl.")
    return ws_endpoint


def sanitize_filename(value: str) -> str:
    value = re.sub(r"[^\w\-. ]+", "_", value.strip(), flags=re.UNICODE)
    return value[:80] or "dialog"


def extract_messages_from_current_page(debug_url: str) -> tuple[list[str], str]:
    """Extract messages from currently focused KeyCRM tab.

    Returns tuple (lines, suggested_name).
    """
    ws_endpoint = get_cdp_websocket(debug_url)

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(ws_endpoint)
        try:
            page = None
            for context in browser.contexts:
                for candidate in context.pages:
                    if "keycrm" in (candidate.url or "").lower():
                        page = candidate
                        break
                if page:
                    break

            if not page:
                raise RuntimeError("Не знайдено відкриту вкладку KeyCRM.")

            js = r"""
            () => {
              const container = document.querySelector('.vac-messages-container');
              if (!container) {
                return { error: 'Контейнер .vac-messages-container не знайдено.' };
              }

              const wrappers = Array.from(container.querySelectorAll('.vac-message-wrapper'));
              const rows = [];
              let activeDate = '';

              for (const wrapper of wrappers) {
                const dateCard = wrapper.querySelector('.vac-card-date span');
                if (dateCard) {
                  activeDate = dateCard.innerText.trim();
                }

                const textNode = wrapper.querySelector('.vac-format-message-wrapper');
                const text = textNode ? textNode.innerText.trim() : '';

                const hasFile = wrapper.querySelector('.vac-message-files-container .vac-message-file-container, .vac-message-files-container .vac-message-image-container');
                let content = text;

                if (!content && hasFile) {
                  content = '[Вкладення]';
                }

                if (!content) {
                  continue;
                }

                const usernameNode = wrapper.querySelector('.vac-text-username .font-weight-bold');
                const username = usernameNode ? usernameNode.innerText.trim() : '';
                const ownMessage = wrapper.querySelector('.vac-message-current') !== null;
                const role = username || (ownMessage ? 'Менеджер' : 'Клієнт');

                const messageDateRaw = wrapper.querySelector('.vac-message-date')?.innerText || '';
                const timeMatch = messageDateRaw.match(/\b\d{1,2}:\d{2}\b/);
                const time = timeMatch ? timeMatch[0] : '';

                const line = `${activeDate ? '[' + activeDate + '] ' : ''}${time ? time + ' ' : ''}${role}: ${content}`;
                rows.push(line.replace(/\s+\n/g, '\n').trim());
              }

              const title = document.title || 'keycrm_dialog';
              return { rows, title };
            }
            """

            result = page.evaluate(js)
            if result.get("error"):
                raise RuntimeError(result["error"])

            lines = result.get("rows", [])
            title = result.get("title", "keycrm_dialog")
            if not lines:
                raise RuntimeError("Повідомлення не знайдено. Можливо, чат ще не завантажився.")

            return lines, sanitize_filename(title)
        finally:
            browser.close()


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("KeyCRM Dialog Exporter")
        self.root.geometry("650x400")

        self.output_dir = tk.StringVar(value=str(Path.cwd() / "exports"))
        self.debug_url = tk.StringVar(value=DEFAULT_DEBUG_URL)
        Path(self.output_dir.get()).mkdir(parents=True, exist_ok=True)

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Папка для .txt файлів:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.output_dir, width=70).grid(row=1, column=0, sticky="we", padx=(0, 8))
        ttk.Button(frame, text="Обрати...", command=self.choose_folder).grid(row=1, column=1, sticky="e")

        ttk.Label(frame, text="Chrome DevTools URL:").grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=self.debug_url, width=70).grid(row=3, column=0, columnspan=2, sticky="we")

        ttk.Button(frame, text="Парсити поточний чат", command=self.export_chat).grid(row=4, column=0, pady=14, sticky="w")

        hint = (
            "Перед парсингом: запустіть Chrome з --remote-debugging-port=9222,\n"
            "відкрийте потрібний діалог у KeyCRM і дочекайтеся завантаження повідомлень.\n"
            "Для старих повідомлень прокрутіть чат догори, щоб вони підвантажилися."
        )
        ttk.Label(frame, text=hint).grid(row=5, column=0, columnspan=2, sticky="w")

        self.log = tk.Text(frame, height=10, wrap="word")
        self.log.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(12, 0))

        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(6, weight=1)

    def choose_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.output_dir.get())
        if folder:
            self.output_dir.set(folder)

    def add_log(self, message: str) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{now}] {message}\n")
        self.log.see(tk.END)

    def export_chat(self) -> None:
        output_path = Path(self.output_dir.get())
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            lines, title = extract_messages_from_current_page(self.debug_url.get())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = output_path / f"{timestamp}_{title}.txt"
            file_path.write_text("\n".join(lines), encoding="utf-8")
            self.add_log(f"Готово: збережено {len(lines)} повідомлень у {file_path}")
        except (ConnectionError, RuntimeError, PlaywrightError) as exc:
            self.add_log(f"Помилка: {exc}")
            messagebox.showerror("Помилка", str(exc))


def main() -> None:
    root = tk.Tk()
    app = App(root)
    app.add_log("Застосунок запущено.")
    root.mainloop()


if __name__ == "__main__":
    main()
