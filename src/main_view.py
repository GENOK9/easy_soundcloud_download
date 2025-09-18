# Python
import html
import re
import tempfile
import urllib.request
import flet as ft
from urllib.parse import urlparse
from soundcloud_resolver import _is_soundcloud_url as validate_url
import download_controller as dc
dc = dc.DownloadController(base_dir="auto")




def fetch_metadata(url: str) -> dict:
    """
    Metadaten aus 'Open-Graph-Tags' (title,uploader,image).
    """
    meta = {"title": None, "image": None}

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}")
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                raise RuntimeError("Not HTML")
            html_text = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        html_text = "" #Platzhalter

    # og:title
    m_title = re.search(
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
        html_text,
        re.IGNORECASE | re.DOTALL,
    )
    if m_title:
        meta["title"] = html.unescape(m_title.group(1)).strip()

    # og:image
    m_image = re.search(
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']',
        html_text,
        re.IGNORECASE | re.DOTALL,
    )
    if m_image:
        meta["image"] = html.unescape(m_image.group(1)).strip()

    # Fallbacks
    if not meta["title"]:
        parsed = urlparse(url)
        last_segment = parsed.path.rstrip("/").split("/")[-1] or parsed.netloc
        meta["title"] = last_segment.replace("-", " ").replace("_", " ").strip() or parsed.netloc

    return meta


def main(page: ft.Page):
    page.title = "SoundCloud Downloader (GUI Preview)"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_min_width = 420
    page.window_min_height = 600

    page.appbar = ft.AppBar(title=ft.Text("Downloads"), center_title=False) #Appbar Initialisieren
    lv = ft.ListView(expand=True, spacing=8, padding=12, auto_scroll=True) #Listview mit Download Items


    log_output = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    class DownloadLogger:
        """
        Klasse für download logging: yt-dlp erwartet ein Objekt mit 4 Funktionen (debug, info, warning, error)
        """
        def debug(self, msg):
            # yt-dlp schickt sowohl "debug" als auch "info" hierher
            if msg.startswith("[debug] "):
                log_output.controls.append(ft.Text(msg, color=ft.Colors.GREY))
            else:
                self.info(msg)
            page.update()

        def info(self, msg):
            log_output.controls.append(ft.Text(msg))
            page.update()

        def warning(self, msg):
            log_output.controls.append(ft.Text(f"WARNING: {msg}", color=ft.Colors.ORANGE))
            page.update()

        def error(self, msg):
            log_output.controls.append(ft.Text(f"ERROR: {msg}", color=ft.Colors.RED))
            page.update()
    log = DownloadLogger()

    # URL input Dialog
    url_field = ft.TextField(label="Download-Link einfügen", autofocus=True, multiline=False, width=500)
    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Neuer Download"),
        content=url_field,
        actions_alignment=ft.MainAxisAlignment.END,
        actions=[
            ft.TextButton("Abbrechen", on_click=lambda e: close_dialog()),
            ft.FilledButton("Hinzufügen", icon=ft.Icons.ADD_LINK, on_click=lambda e: on_add_click(e)),
        ],
    )


    def show_log():
        log_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("yt-dlp Log"),
            content=log_output,
            actions=[ft.ElevatedButton("Close", on_click=lambda e: page.close(log_dialog))]
        )
        page.open(log_dialog)

    def show_debug_info():
        import os
        from pathlib import Path

        debug_text = []
        debug_text.append(f"Arbeitsverzeichnis: {os.getcwd()}")
        debug_text.append(f"__file__ (main): {__file__}")
        debug_text.append(f"FLET_PLATFORM: {os.getenv('FLET_PLATFORM')}")

        # Teste ffmpeg-Pfade
        possible_sources = [
            Path(__file__).resolve().parent / "ffmpeg",
            Path(__file__).resolve().parent.parent / "src" / "ffmpeg",
            Path(os.getcwd()) / "src" / "ffmpeg",
            Path(os.getcwd()) / "ffmpeg",
            Path(tempfile.gettempdir()) / "ffmpeg",
            Path("/sdcard/Music"),
            Path(dc.base_dir),
            Path("/data/data/com.flet.src/files/ffmpeg")
        ]

        debug_text.append("\nffmpeg Suche:")
        for src in possible_sources:
            if src.exists():
                size = src.stat().st_size
                debug_text.append(f"✓ {src} (size={size} bytes)")
            else:
                debug_text.append(f"✗ {src}")

        debug_text.append(f"ffmpeg in projekt ausführbar: {os.access("/data/data/com.flet.src/files/ffmpeg", os.X_OK)}")

        debug_info = "\n".join(debug_text)

        def close_debug(e):
            page.close(debug_dialog)

        debug_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Debug Info"),
            content=ft.Text(debug_info, selectable=True),
            actions=[ft.TextButton("OK", on_click=close_debug)]
        )
        page.open(debug_dialog)

    # Debug-Button zur AppBar hinzufügen
    page.appbar = ft.AppBar(
        title=ft.Text("Downloads"),
        center_title=False,
        actions=[
            ft.IconButton(
                icon=ft.Icons.BUG_REPORT,
                tooltip="Debug Info",
                on_click=lambda e: show_debug_info()
            ),
            ft.IconButton(
                icon=ft.Icons.COMPUTER,
                tooltip="log",
                on_click=lambda e: show_log()
            )
        ]
    )

    #URL Input Dialog
    def open_dialog(e=None):
        url_field.value = ""
        page.open(dlg)

    def close_dialog():
        page.close(dlg)

    def on_add_click(e):
        page.run_task(add_from_dialog)

    async def add_from_dialog():
        url = (url_field.value or "").strip()
        if not url:
            close_dialog()
            return
        if not validate_url(url):
            close_dialog()
            return

        # UI-Elemente erstellen
        title_text = ft.Text("Lade Metadaten...", weight=ft.FontWeight.W_600)
        subtitle_text = ft.Text(url, color=ft.Colors.GREY_700, size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
        avatar = ft.CircleAvatar(radius=24, foreground_image_src=None, bgcolor=ft.Colors.GREY_200,
                                 content=ft.Icon(ft.Icons.AUDIO_FILE))
        status_chip = ft.Chip(label=ft.Text("Ausstehend"), leading=ft.Icon(ft.Icons.DOWNLOAD),
                              bgcolor=ft.Colors.GREY_200)
        progress_bar = ft.ProgressBar(value=0.0, width=220)

        item_tile = ft.ListTile(
            leading=avatar,
            title=title_text,
            subtitle=ft.Column([subtitle_text, progress_bar], spacing=4, tight=True),
            trailing=status_chip,
            dense=False,
        )
        lv.controls.append(item_tile)
        page.update()
        close_dialog()

        #Platzhalter für DownloadItem
        item_ref = {"it": None}

        def show_error_alert(error_message: str):
            def close_alert(e):
                page.close(alert)
                page.update()

            alert = ft.AlertDialog(
                title=ft.Text("Download Error"),
                content=ft.Text(error_message),
                actions=[ft.TextButton("OK", on_click=close_alert)]
            )
            page.dialog = alert
            page.open(alert)
            page.update()

        def on_status(status, err, *, page=page):
            it = item_ref["it"]
            if it and it.title:
                title_text.value = it.title,
            if it and it.image_url:
                avatar.foreground_image_src = it.image_url
                avatar.content = None
            status_chip.label = ft.Text(status.name)
            if status.name == "READY":
                status_chip.leading = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN)
                status_chip.bgcolor = ft.Colors.GREEN_50
            elif status.name == "DOWNLOADING":
                status_chip.leading = ft.Icon(ft.Icons.DOWNLOAD)
                status_chip.bgcolor = ft.Colors.GREY_200
            elif status.name == "COMPLETED":
                status_chip.leading = ft.Icon(ft.Icons.CHECK, color=ft.Colors.GREEN)
                status_chip.bgcolor = ft.Colors.GREEN_50
            elif status.name == "FAILED":
                status_chip.leading = ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED)
                status_chip.bgcolor = ft.Colors.RED_50
                if err:
                    subtitle_text.value = f"{subtitle_text.value}\n{err}"
                    show_error_alert(err)
            page.update()



        def on_progress(d: dict, *, page=page):
            p = float(d.get("progress") or 0.0)
            progress_bar.value = p
            spd = d.get("speed") or 0
            eta = d.get("eta")
            subtitle_text.value = f"{int(p * 100)}% • {int(spd / 1024)} KiB/s" + (f" • ETA {eta}s" if eta else "")
            page.update()

        download_item = dc.add_link(url, on_progress=on_progress, on_status=on_status, log=log)
        item_ref["it"] = download_item

    # FAB unten rechts
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        tooltip="Neuen Link hinzufügen",
        on_click=open_dialog,
    )

    # Content
    page.add(ft.SafeArea(ft.Container(lv, expand=True)))


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)
