#!/usr/bin/env python3
# Desktop-Symbolpositionen – GTK-Version
# Linux Mint 22.3 Cinnamon – natives GTK-Theme
# Version 2.5
#
# Neu in 2.5: Explizite Versionsfestlegung (gi.require_version)
# auch für Gdk vor dem Import.
#
# Neu in 2.4: Im Sicherungsordner werden pro Profil nur die
# letzten 5 Sicherungen aufbewahrt; ältere werden nach jeder
# erfolgreichen Sicherung automatisch gelöscht.
#
# Benötigt: python3-gi, gir1.2-gtk-3.0
#   sudo apt install python3-gi gir1.2-gtk-3.0
#
# Die Konfigurationsdatei (~/.config/desktop-symbolpositionen/
# config.json) ist mit Version 1.x voll kompatibel.

import json
import math
import shutil
import subprocess
import time
import zipfile

from datetime import datetime
from pathlib import Path

try:
    import gi
except ImportError:
    raise SystemExit(
        "PyGObject wird benötigt:\n"
        "  sudo apt install python3-gi gir1.2-gtk-3.0"
    )

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk


VERSION = "2.5"
APP_NAME = "Desktop-Symbolpositionen"

HOME = Path.home()
CONFIG_DIR = HOME / ".config" / "desktop-symbolpositionen"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_FOLDER = HOME / "Dokumente" / "Desktop-Sicherungen"
DEFAULT_PROFILE = "Standard"
KEEP_BACKUPS = 5  # Wie viele Sicherungen pro Profil behalten werden

TEXT = "#263449"
MUTED = "#68778d"
BORDER = "#dce6f2"
RED = "#c03945"
GREEN = "#21865b"


# ============================================================
# Kernfunktionen (unabhängig von der Oberfläche)
# ============================================================

def is_safe_name(name):
    """Prüft, ob ein Name als Datei-/Ordnerteil sicher ist."""
    return (
        bool(name)
        and name not in (".", "..")
        and "/" not in name
        and "\\" not in name
    )


def find_desktop():
    """Ermittelt den Desktop-Ordner."""
    try:
        result = subprocess.run(
            ["xdg-user-dir", "DESKTOP"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        path = Path(result.stdout.strip())
        if path.is_dir():
            return path
    except (OSError, subprocess.SubprocessError):
        pass

    for name in ("Desktop", "Schreibtisch"):
        path = HOME / name
        if path.is_dir():
            return path

    return HOME / "Desktop"


DESKTOP = find_desktop()


def run_command(args, input_data=None):
    """Führt einen externen Befehl aus."""
    return subprocess.run(
        args,
        input=input_data,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )


def refresh_desktop():
    """Löst eine Aktualisierung der Nemo-Desktop-Anzeige aus.

    Versucht zuerst F5 via xdotool, startet andernfalls
    nemo-desktop neu. Rückgabe: True bei Erfolg.
    """
    if shutil.which("xdotool"):
        searches = (
            ["xdotool", "search", "--onlyvisible", "--name", "Desktop"],
            ["xdotool", "search", "--class", "nemo-desktop"],
        )
        for search_cmd in searches:
            try:
                result = subprocess.run(
                    search_cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
            except (OSError, subprocess.SubprocessError):
                continue

            refreshed = False
            for window_id in result.stdout.split()[:5]:
                try:
                    subprocess.run(
                        ["xdotool", "key", "--window", window_id, "F5"],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=10,
                    )
                    refreshed = True
                except (OSError, subprocess.SubprocessError):
                    continue

            if refreshed:
                return True

    if shutil.which("nemo-desktop") and shutil.which("pkill"):
        try:
            subprocess.run(
                ["pkill", "-x", "nemo-desktop"],
                check=False,
                timeout=10,
            )
            subprocess.Popen(
                ["nemo-desktop"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            pass

    return False


def load_config():
    """Lädt Sicherungsordner, Profile und aktives Profil."""
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            config = json.load(file)

        if not isinstance(config, dict):
            raise ValueError("Ungültiges Konfigurationsformat.")

        folder = config.get("folder")
        if isinstance(folder, str) and folder.strip():
            folder = Path(folder).expanduser()
        else:
            folder = DEFAULT_FOLDER

        raw_profiles = config.get("profiles")
        migrated = not isinstance(raw_profiles, dict) or not raw_profiles

        if migrated:
            profiles = {DEFAULT_PROFILE: {"last_backup": None}}
        else:
            profiles = {
                name: (info if isinstance(info, dict) else {})
                for name, info in raw_profiles.items()
                if isinstance(name, str) and name
            }
            if not profiles:
                profiles = {DEFAULT_PROFILE: {"last_backup": None}}
                migrated = True

        active = config.get("active_profile")
        if not isinstance(active, str) or active not in profiles:
            active = next(iter(profiles))

        return folder, profiles, active, migrated

    except (OSError, ValueError, TypeError):
        return (
            DEFAULT_FOLDER,
            {DEFAULT_PROFILE: {"last_backup": None}},
            DEFAULT_PROFILE,
            False,
        )


def save_config(folder, profiles, active_profile):
    """Speichert Sicherungsordner, Profile und aktives Profil."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config = {
        "folder": str(Path(folder).expanduser().resolve()),
        "profiles": profiles,
        "active_profile": active_profile,
    }

    temp_file = CONFIG_FILE.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, ensure_ascii=False)

    temp_file.replace(CONFIG_FILE)


def get_position(path):
    """Liest die Nemo-Symbolposition."""
    try:
        result = run_command([
            "gio", "info",
            "--attributes=metadata::nemo-icon-position",
            str(path),
        ])

        prefix = "metadata::nemo-icon-position:"

        for line in result.stdout.splitlines():
            if prefix in line:
                value = line.split(prefix, 1)[1].strip()
                if value and value != "(null)":
                    return value

    except (OSError, subprocess.SubprocessError):
        pass

    return None


def set_position(path, position):
    """Setzt die Nemo-Symbolposition."""
    run_command([
        "gio", "set",
        str(path),
        "metadata::nemo-icon-position",
        str(position),
    ])


def parse_position(value):
    """Wandelt eine Nemo-Position ('x,y') in ein (x, y)-Tupel um."""
    if not isinstance(value, str):
        return None

    parts = value.split(",")
    if len(parts) < 2:
        return None

    try:
        return float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None


def backup_positions(archive_path):
    """Sichert Symbolpositionen und Nemo-Einstellungen."""
    if not DESKTOP.is_dir():
        raise RuntimeError(
            f"Desktop-Ordner wurde nicht gefunden:\n{DESKTOP}"
        )

    positions = {}

    for item in DESKTOP.iterdir():
        position = get_position(item)
        if position is not None:
            positions[item.name] = position

    manifest = {
        "version": VERSION,
        "created": datetime.now().astimezone().isoformat(),
        "desktop": str(DESKTOP),
        "positions": positions,
    }

    archive_path = Path(archive_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "positions.json",
            json.dumps(manifest, indent=2, ensure_ascii=False),
        )

        for name, schema in [
            ("nemo-desktop.dconf", "/org/nemo/desktop/"),
            ("nemo-icon-view.dconf", "/org/nemo/icon-view/"),
        ]:
            try:
                result = run_command(["dconf", "dump", schema])
                archive.writestr(name, result.stdout)
            except (OSError, subprocess.SubprocessError):
                pass

    return len(positions)


def backup_pattern(profile):
    """Glob-Muster für die Sicherungsdateien eines Profils.

    Das Profil 'Standard' erzeugt Dateien ohne Präfix,
    alle anderen tragen den Profilnamen als Präfix.
    """
    if profile == DEFAULT_PROFILE:
        return "Desktop-Sicherung_*.zip"
    return f"{profile}_Desktop-Sicherung_*.zip"


def cleanup_old_backups(folder, profile, keep=KEEP_BACKUPS):
    """Löscht die ältesten Sicherungen eines Profils.

    Es bleiben nur die 'keep' neuesten Dateien des Profils
    im Sicherungsordner erhalten. Rückgabe: Liste der
    gelöschten Dateinamen (kann leer sein).
    """
    deleted = []

    folder = Path(folder)
    if not folder.is_dir():
        return deleted

    try:
        files = [
            path for path in folder.glob(backup_pattern(profile))
            if path.is_file()
        ]
        # Nach Änderungsdatum sortieren: die neuesten zuerst.
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)

        for old in files[keep:]:
            try:
                old.unlink()
                deleted.append(old.name)
            except OSError:
                pass  # Schutzrechte o. ä.: Datei behalten

    except OSError:
        pass  # Ordner nicht lesbar: nichts löschen

    return deleted


def restore_positions(archive_path):
    """Stellt Symbolpositionen aus einer ZIP-Datei wieder her.

    Rückgabe: (restored, missing, failed, warnings)
    """
    restored = 0
    missing = []
    failed = []
    warnings = []

    with zipfile.ZipFile(archive_path, "r") as archive:
        if "positions.json" not in archive.namelist():
            raise RuntimeError(
                "Ungültige Sicherung: positions.json fehlt."
            )

        try:
            manifest = json.loads(
                archive.read("positions.json").decode("utf-8")
            )
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError(
                f"Die Positionsdaten sind ungültig: {exc}"
            ) from exc

        if not isinstance(manifest, dict):
            raise RuntimeError(
                "Ungültiges Format der Sicherungsdatei."
            )

        positions = manifest.get("positions")
        if positions is None:
            positions = {}

        if not isinstance(positions, dict):
            raise RuntimeError("Die Positionsdaten sind ungültig.")

        for name, position in positions.items():
            if (
                not isinstance(name, str)
                or not is_safe_name(name)
                or not isinstance(position, (str, int, float))
            ):
                continue

            path = DESKTOP / name

            if not path.exists() and not path.is_symlink():
                missing.append(name)
                continue

            try:
                set_position(path, position)
                restored += 1
            except (OSError, subprocess.SubprocessError) as exc:
                failed.append(name)
                warnings.append(f"{name}: {exc}")

        for name, schema in [
            ("nemo-desktop.dconf", "/org/nemo/desktop/"),
            ("nemo-icon-view.dconf", "/org/nemo/icon-view/"),
        ]:
            if name not in archive.namelist():
                continue

            try:
                data = archive.read(name).decode("utf-8")
                run_command(["dconf", "load", schema], data)
            except (
                OSError,
                UnicodeDecodeError,
                subprocess.SubprocessError,
            ) as exc:
                warnings.append(f"{name}: {exc}")

    return restored, missing, failed, warnings


# ============================================================
# GTK-Hilfsfunktionen
# ============================================================

def hex_rgb(color):
    """Wandelt '#rrggbb' in ein Cairo-RGB-Tupel um."""
    color = color.lstrip("#")
    return (
        int(color[0:2], 16) / 255,
        int(color[2:4], 16) / 255,
        int(color[4:6], 16) / 255,
    )


def show_message(parent, heading, message, kind="info"):
    """Zeigt einen Informations- oder Fehlerdialog."""
    message_type = (
        Gtk.MessageType.ERROR if kind == "error"
        else Gtk.MessageType.INFO
    )

    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=message_type,
        buttons=Gtk.ButtonsType.OK,
        text=heading,
    )
    dialog.format_secondary_text(message)
    dialog.run()
    dialog.destroy()


def ask_yes_no(parent, heading, message, ok_label="Fortfahren",
               danger=False):
    """Bestätigungsdialog; Rückgabe True bei Bestätigung."""
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.CANCEL,
        text=heading,
    )
    dialog.format_secondary_text(message)

    ok_button = dialog.add_button(ok_label, Gtk.ResponseType.OK)
    style = ok_button.get_style_context()
    style.add_class(
        "destructive-action" if danger else "suggested-action"
    )
    dialog.set_default_response(Gtk.ResponseType.OK)

    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.OK


class EntryDialog(Gtk.Dialog):
    """Eingabedialog für Profil- und Ordnernamen."""

    def __init__(self, parent, title, heading, prompt, initial=""):
        super().__init__(
            title=title,
            transient_for=parent,
            modal=True,
        )
        self.add_button("Abbrechen", Gtk.ResponseType.CANCEL)
        self.add_button("Erstellen", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)

        box = self.get_content_area()
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_spacing(10)

        box.pack_start(
            Gtk.Label(
                halign=Gtk.Align.START,
                use_markup=True,
                label=f"<big><b>{heading}</b></big>",
            ),
            False, False, 0,
        )
        box.pack_start(
            Gtk.Label(halign=Gtk.Align.START, label=prompt),
            False, False, 0,
        )

        self.entry = Gtk.Entry()
        self.entry.set_text(initial)
        self.entry.set_activates_default(True)
        box.pack_start(self.entry, False, False, 4)

        self.show_all()

    def run_and_get(self):
        """Startet den Dialog und liefert die Eingabe oder None."""
        response = self.run()

        if response == Gtk.ResponseType.OK:
            value = self.entry.get_text()
            self.destroy()
            return value

        self.destroy()
        return None


def choose_file(parent, mode, current_folder, initial_name=""):
    """Nativer GTK-Dateidialog.

    mode: "open" (ZIP-Datei), "save" (ZIP-Datei), "folder" (Ordner)
    Rückgabe: ausgewählter Pfad oder None.
    """
    if mode == "folder":
        action = Gtk.FileChooserAction.SELECT_FOLDER
        ok_label = "_Auswählen"
        title = "Sicherungsordner auswählen"
    elif mode == "save":
        action = Gtk.FileChooserAction.SAVE
        ok_label = "_Speichern"
        title = "Sicherung speichern"
    else:
        action = Gtk.FileChooserAction.OPEN
        ok_label = "_Öffnen"
        title = "Sicherung zum Wiederherstellen auswählen"

    dialog = Gtk.FileChooserDialog(
        title=title,
        transient_for=parent,
        action=action,
    )
    dialog.add_buttons(
        "_Abbrechen", Gtk.ResponseType.CANCEL,
        ok_label, Gtk.ResponseType.OK,
    )
    dialog.set_default_response(Gtk.ResponseType.OK)

    folder = str(current_folder)
    if Path(folder).is_dir():
        dialog.set_current_folder(folder)

    if mode in ("open", "save"):
        zip_filter = Gtk.FileFilter()
        zip_filter.set_name("ZIP-Sicherungen")
        zip_filter.add_pattern("*.zip")
        dialog.add_filter(zip_filter)

    if mode == "save":
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name(initial_name)

    response = dialog.run()
    path = dialog.get_filename() if response == Gtk.ResponseType.OK else None
    dialog.destroy()
    return path


class PreviewWindow(Gtk.Dialog):
    """Vorschau einer Sicherung mit grafischer Positions-Ansicht.

    Nummerierte Punkte auf einer skalierten Desktop-Fläche,
    daneben eine scrollbare Dateiliste. Fehlende Dateien
    sind rot markiert. Wirft RuntimeError bei ungültigen Daten.
    """

    def __init__(self, parent, archive_path):
        # Sicherung lesen (Fehler werden weitergereicht)
        with zipfile.ZipFile(archive_path, "r") as archive:
            names = archive.namelist()

            if "positions.json" not in names:
                raise RuntimeError(
                    "Ungültige Sicherung: positions.json fehlt."
                )

            manifest = json.loads(
                archive.read("positions.json").decode("utf-8")
            )

            settings_names = [
                n for n in (
                    "nemo-desktop.dconf",
                    "nemo-icon-view.dconf",
                )
                if n in names
            ]

        if not isinstance(manifest, dict):
            raise RuntimeError("Ungültiges Format der Sicherungsdatei.")

        positions = manifest.get("positions")
        if positions is None:
            positions = {}
        if not isinstance(positions, dict):
            raise RuntimeError("Die Positionsdaten sind ungültig.")

        self.drawn = []       # (name, x, y, exists)
        self.unplaced = []    # (name, exists)
        missing = []

        for name, position in positions.items():
            if not isinstance(name, str) or not is_safe_name(name):
                continue

            path = DESKTOP / name
            exists = path.exists() or path.is_symlink()

            coords = parse_position(position)
            if coords is None:
                self.unplaced.append((name, exists))
            else:
                self.drawn.append(
                    (name, coords[0], coords[1], exists)
                )

            if not exists:
                missing.append(name)

        self.missing = missing

        existing_count = (
            sum(1 for entry in self.drawn if entry[3])
            + sum(1 for _n, e in self.unplaced if e)
        )

        # Bildschirmgröße für die Skalierung ermitteln
        screen_w, screen_h = 1920, 1080
        try:
            window = parent.get_window()
            if window is not None:
                monitor = window.get_display().get_monitor_at_window(window)
                geometry = monitor.get_geometry()
                screen_w = geometry.width
                screen_h = geometry.height
        except Exception:
            pass

        self.screen_w = max(1, screen_w)
        self.screen_h = max(1, screen_h)

        # Dialog aufbauen
        super().__init__(
            title="Wiederherstellen – Vorschau",
            transient_for=parent,
            modal=True,
        )
        self.add_button("Abbrechen", Gtk.ResponseType.CANCEL)
        ok_button = self.add_button(
            "Wiederherstellen", Gtk.ResponseType.OK
        )
        ok_button.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)

        # Großes, skalierbares Vorschaufenster
        self.set_default_size(1150, 780)
        self.set_resizable(True)

        box = self.get_content_area()
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(18)
        box.set_margin_bottom(18)
        box.set_spacing(12)

        box.pack_start(
            Gtk.Label(
                halign=Gtk.Align.START,
                use_markup=True,
                label="<big><b>Vorschau der Sicherung</b></big>",
            ),
            False, False, 0,
        )

        # Kopfzeile der Sicherung
        created = manifest.get("created")
        created_text = (
            created if isinstance(created, str) and created
            else "unbekannt"
        )
        desktop_text = manifest.get("desktop")
        if not isinstance(desktop_text, str) or not desktop_text:
            desktop_text = str(DESKTOP)

        total = len(self.drawn) + len(self.unplaced)
        count_text = (
            f"Positionen: {total}   ·   "
            f"vorhanden: {existing_count}   ·   "
            f"fehlend: {len(missing)}"
        )
        if self.unplaced:
            count_text += (
                f"   ·   ohne Koordinaten: {len(self.unplaced)}"
            )

        settings_text = (
            ", ".join(settings_names) if settings_names else "keine"
        )

        info_label = Gtk.Label(
            halign=Gtk.Align.START,
            xalign=0,
            label=(
                f"Erstellt: {created_text}\n"
                f"Desktop: {desktop_text}\n"
                f"{count_text}\n"
                f"Enthaltene Nemo-Einstellungen: {settings_text}"
            ),
        )
        box.pack_start(info_label, False, False, 0)

        # Positionsvorschau (links) + Dateiliste (rechts)
        content = Gtk.Box(spacing=14)

        canvas_w = 620
        canvas_h = max(
            260,
            min(520, int(canvas_w * self.screen_h / self.screen_w)),
        )

        self.drawing_area = Gtk.DrawingArea()
        self.drawing_area.set_size_request(canvas_w, canvas_h)
        self.drawing_area.connect("draw", self._on_draw)

        # Vorschau in linker Spalte mit Scrollmöglichkeit,
        # falls das Fenster kleiner gemacht wird.
        preview_scroll = Gtk.ScrolledWindow()
        preview_scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        preview_scroll.set_size_request(canvas_w + 20, canvas_h)
        preview_scroll.add(self.drawing_area)
        content.pack_start(preview_scroll, False, False, 0)

        store = Gtk.ListStore(str, str, str)  # Nr., Datei, Farbe

        for index, (name, _x, _y, exists) in enumerate(
            self.drawn, start=1
        ):
            store.append([
                str(index),
                name,
                TEXT if exists else RED,
            ])

        for name, exists in self.unplaced:
            store.append(["–", name, TEXT if exists else RED])

        tree = Gtk.TreeView(model=store)
        tree.set_headers_visible(True)

        nr_column = Gtk.TreeViewColumn(
            "Nr.", Gtk.CellRendererText(xalign=0.5), text=0
        )
        nr_column.set_fixed_width(52)
        nr_column.set_alignment(0.5)
        nr_column.add_attribute(
            nr_column.get_cells()[0], "foreground", 2
        )

        name_column = Gtk.TreeViewColumn(
            "Datei", Gtk.CellRendererText(), text=1
        )
        name_column.set_expand(True)
        name_column.add_attribute(
            name_column.get_cells()[0], "foreground", 2
        )

        tree.append_column(nr_column)
        tree.append_column(name_column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        scrolled.set_min_content_height(canvas_h)
        scrolled.add(tree)

        content.pack_start(scrolled, True, True, 0)
        box.pack_start(content, True, True, 0)

        # Legende
        legend = Gtk.Box(spacing=12)
        legend.pack_start(
            Gtk.Label(
                use_markup=True,
                label=f"<span foreground='{GREEN}'>●</span> vorhanden",
            ),
            False, False, 0,
        )
        legend.pack_start(
            Gtk.Label(
                use_markup=True,
                label=(
                    f"<span foreground='{RED}'>●</span> "
                    "fehlt auf dem Desktop"
                ),
            ),
            False, False, 0,
        )
        box.pack_start(legend, False, False, 2)

        self.show_all()

    def _on_draw(self, area, cr):
        """Zeichnet die skalierte Desktop-Fläche mit Punkten."""
        width = area.get_allocated_width()
        height = area.get_allocated_height()

        # Hintergrund
        bg_rgb = hex_rgb("#fbfcfe")
        cr.set_source_rgb(bg_rgb[0], bg_rgb[1], bg_rgb[2])
        cr.paint()

        margin = 16
        inner_w = width - 2 * margin
        inner_h = height - 2 * margin

        # Rahmen der Desktop-Fläche
        border_rgb = hex_rgb(BORDER)
        cr.set_source_rgb(border_rgb[0], border_rgb[1], border_rgb[2])
        cr.set_line_width(1)
        cr.rectangle(margin - 1.5, margin - 1.5, inner_w + 3, inner_h + 3)
        cr.stroke()

        # Schrift für die Nummern vorbereiten
        cr.set_font_size(9)

        for index, (name, x, y, exists) in enumerate(self.drawn, 1):
            cx = margin + max(0.0, min(1.0, x / self.screen_w)) * inner_w
            cy = margin + max(0.0, min(1.0, y / self.screen_h)) * inner_h
            rgb = hex_rgb(GREEN if exists else RED)

            # Punkt
            cr.set_source_rgb(rgb[0], rgb[1], rgb[2])
            cr.arc(cx, cy, 5, 0, 2 * math.pi)
            cr.fill()

            # Nummer immer unten rechts neben den Punkt setzen.
            # Am Rand wird sie leicht nach innen verschoben,
            # damit sie nicht abgeschnitten wird.
            label = str(index)
            extents = cr.text_extents(label)
            tw = extents.width
            th = extents.height

            tx = cx + 7
            ty = cy + 11

            if tx + tw > width - margin:
                tx = width - margin - tw
            if ty + th > height - margin:
                ty = height - margin

            cr.set_source_rgb(rgb[0], rgb[1], rgb[2])
            cr.move_to(tx, ty)
            cr.show_text(label)

        return False


# ============================================================
# Hauptfenster
# ============================================================

class DesktopApp:
    """GTK-Hauptfenster der Anwendung."""

    def __init__(self):
        (
            self.folder,
            self.profiles,
            self.active_profile,
            migrated,
        ) = load_config()

        if migrated:
            try:
                save_config(
                    self.folder, self.profiles, self.active_profile
                )
            except OSError:
                pass

        self._updating_profile_ui = False

        self._build_window()

    # --------------------------------------------------------
    # Oberfläche
    # --------------------------------------------------------

    def _apply_style(self):
        """Karten-Optik und Button-Stile."""
        css = (
            "frame.card {"
            "  background-color: @theme_base_color;"
            "  border: 1px solid @borders;"
            "  border-radius: 8px;"
            "}"
            "button.accent-button {"
            "  background-color: #e8f2ff;"
            "  color: #294db6;"
            "  border: 1px solid #b7d4ff;"
            "  font-weight: bold;"
            "}"
            "button.accent-button:hover {"
            "  background-color: #d8e9ff;"
            "}"
            "button.accent-button:active {"
            "  background-color: #c4e0ff;"
            "}"
            "button.big-button {"
            "  padding: 10px 26px;"
            "  font-weight: bold;"
            "}"
        )
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _card(self, title, subtitle=None):
        """Erzeugt eine Karten-Fläche mit Titel."""
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.NONE)
        frame.get_style_context().add_class("card")

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8
        )
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        frame.add(box)

        box.pack_start(
            Gtk.Label(
                halign=Gtk.Align.START,
                use_markup=True,
                label=f"<b>{title}</b>",
            ),
            False, False, 0,
        )

        if subtitle:
            box.pack_start(
                Gtk.Label(
                    halign=Gtk.Align.START,
                    use_markup=True,
                    label=f"<small>{subtitle}</small>",
                ),
                False, False, 0,
            )

        return frame, box

    def _build_window(self):
        self._apply_style()

        self.window = Gtk.Window(title=f"{APP_NAME} · Version {VERSION}")
        self.window.set_default_size(820, 760)
        self.window.set_resizable(True)

        header = Gtk.HeaderBar()
        header.set_title(APP_NAME)
        header.set_subtitle("Sichern, verwalten und wiederherstellen")
        header.set_show_close_button(True)
        self.window.set_titlebar(header)

        # Beenden-Bestätigung
        self.window.connect("delete-event", self._on_delete_event)
        self.window.connect("destroy", Gtk.main_quit)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=14
        )
        content.set_margin_start(24)
        content.set_margin_end(24)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        self.window.add(content)

        # --- Karte: Desktop ---
        desktop_frame, desktop_box = self._card(
            "Desktop", "Ordner mit deinen Desktop-Symbolen"
        )
        self.desktop_label = Gtk.Label(
            halign=Gtk.Align.START, selectable=True
        )
        self.desktop_label.set_text(str(DESKTOP))
        desktop_box.pack_start(self.desktop_label, False, False, 2)
        content.pack_start(desktop_frame, False, False, 0)

        # --- Karte: Sicherungsordner ---
        folder_frame, folder_box = self._card(
            "Sicherungsordner",
            f"Standardordner für Sicherungsdateien "
            f"(max. {KEEP_BACKUPS} pro Profil)",
        )
        folder_row = Gtk.Box(spacing=8)
        self.folder_label = Gtk.Label(
            halign=Gtk.Align.START, selectable=True,
            ellipsize=1,
        )
        self.folder_label.set_text(str(self.folder))
        folder_row.pack_start(self.folder_label, True, True, 0)

        folder_change = Gtk.Button.new_with_mnemonic("Ordner _ändern")
        folder_change.connect("clicked", self.choose_folder)
        folder_row.pack_start(folder_change, False, False, 0)

        folder_new = Gtk.Button.new_with_mnemonic("_Neuer Ordner")
        folder_new.connect("clicked", self.create_backup_folder)
        folder_row.pack_start(folder_new, False, False, 0)

        folder_box.pack_start(folder_row, False, False, 2)
        content.pack_start(folder_frame, False, False, 0)

        # --- Karte: Desktop-Profil ---
        profile_frame, profile_box = self._card(
            "Desktop-Profil",
            "Separate Positionsprofile, z. B. für Laptop- "
            "und Monitor-Layouts",
        )
        profile_row = Gtk.Box(spacing=8)

        self.profile_combo = Gtk.ComboBoxText()
        self.profile_combo.set_valign(Gtk.Align.CENTER)
        self.profile_combo.connect("changed", self.on_profile_change)
        profile_row.pack_start(self.profile_combo, True, True, 0)

        profile_new = Gtk.Button.new_with_mnemonic("Neues _Profil")
        profile_new.connect("clicked", self.new_profile)
        profile_row.pack_start(profile_new, False, False, 0)

        profile_rename = Gtk.Button.new_with_mnemonic("_Umbenennen")
        profile_rename.connect("clicked", self.rename_profile)
        profile_row.pack_start(profile_rename, False, False, 0)

        profile_delete = Gtk.Button.new_with_mnemonic("_Löschen")
        profile_delete.connect("clicked", self.delete_profile)
        profile_row.pack_start(profile_delete, False, False, 0)

        profile_box.pack_start(profile_row, False, False, 2)

        self.profile_backup_label = Gtk.Label(
            halign=Gtk.Align.START, use_markup=True
        )
        profile_box.pack_start(self.profile_backup_label, False, False, 0)

        content.pack_start(profile_frame, False, False, 0)

        # --- Hinweis ---
        hint = Gtk.Label(
            halign=Gtk.Align.START,
            wrap=True,
            xalign=0,
            use_markup=True,
            label=(
                "<b>Hinweise:</b> Nach dem Wiederherstellen "
                "aktualisiert das Programm die Nemo-Anzeige "
                "automatisch. Im Sicherungsordner bleiben pro "
                f"Profil die {KEEP_BACKUPS} neuesten Sicherungen "
                "erhalten; ältere werden beim Sichern gelöscht."
            ),
        )
        hint.set_margin_start(4)
        hint.set_margin_end(4)
        content.pack_start(hint, False, False, 0)

        # --- Aktionen ---
        actions = Gtk.Box(spacing=8, homogeneous=True)
        actions.set_margin_top(4)

        backup_button = Gtk.Button.new_with_mnemonic("_Jetzt sichern")
        backup_button.get_style_context().add_class("accent-button")
        backup_button.connect("clicked", self.backup)
        actions.pack_start(backup_button, True, True, 0)

        restore_button = Gtk.Button.new_with_mnemonic("_Wiederherstellen")
        restore_button.connect("clicked", self.restore)
        actions.pack_start(restore_button, True, True, 0)

        content.pack_start(actions, False, False, 2)

        # --- Statuskarte (unten) ---
        status_frame = Gtk.Frame()
        status_frame.set_shadow_type(Gtk.ShadowType.NONE)
        status_frame.get_style_context().add_class("card")
        status_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        status_box.set_margin_start(16)
        status_box.set_margin_end(16)
        status_box.set_margin_top(12)
        status_box.set_margin_bottom(12)
        status_frame.add(status_box)

        status_box.pack_start(
            Gtk.Label(
                halign=Gtk.Align.START,
                use_markup=True,
                label="<b>STATUS</b>",
            ),
            False, False, 0,
        )

        self.status_label = Gtk.Label(halign=Gtk.Align.START, wrap=True)
        self.status_label.set_text("Bereit für eine Sicherung.")
        status_box.pack_start(self.status_label, False, False, 0)

        content.pack_start(status_frame, False, False, 0)

        # --- Fußzeile ---
        footer = Gtk.Box(spacing=8)
        footer.pack_start(
            Gtk.Label(
                halign=Gtk.Align.START,
                use_markup=True,
                label=(
                    f"<small>Version {VERSION} · "
                    "Linux Mint Cinnamon · GTK</small>"
                ),
            ),
            True, True, 0,
        )

        quit_button = Gtk.Button.new_with_mnemonic("_Beenden")
        quit_button.get_style_context().add_class("destructive-action")
        quit_button.get_style_context().add_class("big-button")
        quit_button.connect("clicked", self._quit_clicked)
        footer.pack_start(quit_button, False, False, 0)

        content.pack_start(footer, False, False, 0)

        self.refresh_profile_ui()
        self.window.show_all()

    # --------------------------------------------------------
    # Profil-Verwaltung
    # --------------------------------------------------------

    def refresh_profile_ui(self):
        """Aktualisiert Profil-Auswahl und Anzeige der letzten Sicherung."""
        self._updating_profile_ui = True

        self.profile_combo.remove_all()
        names = list(self.profiles)
        for name in names:
            self.profile_combo.append_text(name)

        if self.active_profile in names:
            self.profile_combo.set_active(names.index(self.active_profile))

        info = self.profiles.get(self.active_profile) or {}
        last = info.get("last_backup")

        if isinstance(last, str) and last:
            self.profile_backup_label.set_markup(
                f"<small>Letzte Sicherung dieses Profils:\n{last}</small>"
            )
        else:
            self.profile_backup_label.set_markup(
                "<small>Für dieses Profil liegt noch keine "
                "Sicherung vor.</small>"
            )

        self._updating_profile_ui = False

    def on_profile_change(self, combo):
        """Übernimmt die Auswahl der Profil-Combobox."""
        if self._updating_profile_ui:
            return

        name = combo.get_active_text()
        if not name or name not in self.profiles:
            return

        if name == self.active_profile:
            return

        self.active_profile = name
        try:
            save_config(self.folder, self.profiles, self.active_profile)
        except OSError as exc:
            show_message(
                self.window, "Konfigurationsfehler",
                f"Profil konnte nicht gespeichert werden:\n{exc}",
                kind="error",
            )
            return

        self.refresh_profile_ui()
        self.status_label.set_text(f"Aktives Profil: {name}")

    def new_profile(self, _button):
        """Legt ein neues Positionsprofil an."""
        monitor_window = self.window.get_window()
        suggested = "Profil"
        if monitor_window is not None:
            geo = monitor_window.get_display().get_monitor_at_window(
                monitor_window
            ).get_geometry()
            suggested = f"{geo.width}x{geo.height}"

        dialog = EntryDialog(
            self.window,
            "Neues Profil",
            "Neues Profil anlegen",
            "Name des neuen Profils:",
            initial=suggested,
        )
        name = dialog.run_and_get()

        if name is None:
            return

        name = name.strip()

        if not is_safe_name(name) or len(name) > 60:
            show_message(
                self.window, "Ungültiger Profilname",
                "Bitte einen gültigen Namen ohne Pfadangaben "
                "eingeben.", kind="error",
            )
            return

        if name in self.profiles:
            show_message(
                self.window, "Profil existiert bereits",
                f"Ein Profil mit diesem Namen existiert bereits:\n{name}",
                kind="error",
            )
            return

        previous = self.active_profile
        self.profiles[name] = {"last_backup": None}
        self.active_profile = name

        try:
            save_config(self.folder, self.profiles, self.active_profile)
        except OSError as exc:
            del self.profiles[name]
            self.active_profile = previous
            show_message(
                self.window, "Konfigurationsfehler",
                f"Profil konnte nicht erstellt werden:\n{exc}",
                kind="error",
            )
            return

        self.refresh_profile_ui()
        self.status_label.set_text(f"Neues Profil erstellt: {name}")

    def rename_profile(self, _button):
        """Benennt das aktive Profil um."""
        current = self.active_profile

        dialog = EntryDialog(
            self.window,
            "Profil umbenennen",
            "Profil umbenennen",
            "Neuer Name des Profils:",
            initial=current,
        )
        name = dialog.run_and_get()

        if name is None:
            return

        name = name.strip()

        if name == current:
            return

        if not is_safe_name(name) or len(name) > 60:
            show_message(
                self.window, "Ungültiger Profilname",
                "Bitte einen gültigen Namen ohne Pfadangaben "
                "eingeben.", kind="error",
            )
            return

        if name in self.profiles:
            show_message(
                self.window, "Profil existiert bereits",
                f"Ein Profil mit diesem Namen existiert bereits:\n{name}",
                kind="error",
            )
            return

        info = self.profiles.pop(current)
        self.profiles[name] = info
        self.active_profile = name

        try:
            save_config(self.folder, self.profiles, self.active_profile)
        except OSError as exc:
            del self.profiles[name]
            self.profiles[current] = info
            self.active_profile = current
            show_message(
                self.window, "Konfigurationsfehler",
                f"Profil konnte nicht umbenannt werden:\n{exc}",
                kind="error",
            )
            return

        self.refresh_profile_ui()
        self.status_label.set_text(
            f"Profil umbenannt: {current} → {name}"
        )

    def delete_profile(self, _button):
        """Löscht das aktive Profil."""
        name = self.active_profile

        if len(self.profiles) <= 1:
            show_message(
                self.window, "Löschen nicht möglich",
                "Es muss mindestens ein Profil bestehen bleiben.",
                kind="error",
            )
            return

        confirmed = ask_yes_no(
            self.window,
            f"Profil '{name}' löschen?",
            "Das Profil wird aus der Konfiguration entfernt.\n"
            "Erstellte Sicherungsdateien bleiben erhalten.",
            ok_label="Löschen",
            danger=True,
        )
        if not confirmed:
            return

        del self.profiles[name]
        self.active_profile = next(iter(self.profiles))

        try:
            save_config(self.folder, self.profiles, self.active_profile)
        except OSError as exc:
            self.profiles[name] = {"last_backup": None}
            self.active_profile = name
            show_message(
                self.window, "Konfigurationsfehler",
                f"Profil konnte nicht gelöscht werden:\n{exc}",
                kind="error",
            )
            return

        self.refresh_profile_ui()
        self.status_label.set_text(f"Profil gelöscht: {name}")

    # --------------------------------------------------------
    # Sicherung und Wiederherstellung
    # --------------------------------------------------------

    def create_backup_folder(self, _button):
        """Erstellt einen neuen Unterordner im Sicherungsordner."""
        dialog = EntryDialog(
            self.window,
            "Neuen Sicherungsordner erstellen",
            "Neuen Sicherungsordner anlegen",
            "Name des neuen Ordners:",
        )
        name = dialog.run_and_get()

        if name is None:
            return

        name = name.strip()

        if not is_safe_name(name):
            show_message(
                self.window, "Ungültiger Ordnername",
                "Bitte einen gültigen Ordnernamen ohne "
                "Pfadangaben eingeben.", kind="error",
            )
            return

        target = self.folder / name
        try:
            target.mkdir(parents=True, exist_ok=False)
            self.folder = target
            self.folder_label.set_text(str(target))
            save_config(self.folder, self.profiles, self.active_profile)
            self.status_label.set_text(
                "Neuer Sicherungsordner erstellt und gespeichert."
            )
        except FileExistsError:
            show_message(
                self.window, "Ordner existiert bereits",
                f"Der Ordner existiert bereits:\n{target}",
                kind="error",
            )
        except OSError as exc:
            show_message(
                self.window, "Ordner konnte nicht erstellt werden",
                str(exc), kind="error",
            )

    def choose_folder(self, _button):
        """Wählt den Sicherungsordner über den nativen Dialog."""
        selected = choose_file(self.window, "folder", self.folder)

        if not selected:
            return

        new_folder = Path(selected).expanduser()

        try:
            save_config(
                new_folder, self.profiles, self.active_profile
            )
            self.folder = new_folder
            self.folder_label.set_text(str(new_folder))
            self.status_label.set_text("Sicherungsordner gespeichert.")
        except OSError as exc:
            show_message(
                self.window, "Konfigurationsfehler",
                f"Ordner konnte nicht gespeichert werden:\n{exc}",
                kind="error",
            )

    def backup(self, _button):
        """Erstellt eine ZIP-Sicherung."""
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            show_message(
                self.window, "Sicherungsfehler",
                f"Sicherungsordner nicht verfügbar:\n{exc}",
                kind="error",
            )
            return

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        prefix = (
            "" if self.active_profile == DEFAULT_PROFILE
            else f"{self.active_profile}_"
        )

        # Nativer Speichern-Dialog (bestätigt Überschreiben selbst).
        filename = choose_file(
            self.window, "save", self.folder,
            initial_name=f"{prefix}Desktop-Sicherung_{timestamp}.zip",
        )

        if not filename:
            self.status_label.set_text("Sicherung abgebrochen.")
            return

        archive_path = Path(filename).expanduser()

        try:
            count = backup_positions(archive_path)

            self.folder = archive_path.parent
            self.folder_label.set_text(str(self.folder))
            self.profiles.setdefault(
                self.active_profile, {}
            )["last_backup"] = str(archive_path)
            save_config(self.folder, self.profiles, self.active_profile)
            self.refresh_profile_ui()

            # Automatisches Aufräumen: nur die neuesten
            # KEEP_BACKUPS Sicherungen dieses Profils behalten.
            deleted = cleanup_old_backups(
                self.folder, self.active_profile
            )

            status_text = (
                f"Sicherung erfolgreich: {count} Symbolpositionen"
            )
            if deleted:
                status_text += (
                    f" · {len(deleted)} ältere Sicherung(en) gelöscht:"
                )
                status_text += "\n" + "\n".join(deleted[:5])
                if len(deleted) > 5:
                    status_text += "..."

            self.status_label.set_text(status_text)

            message = f"Gesicherte Symbolpositionen: {count}\n\nDatei:\n{archive_path}"
            if deleted:
                message += (
                    f"\n\nÄltere Sicherungen dieses Profils "
                    f"gelöscht (nur {KEEP_BACKUPS} bleiben "
                    f"erhalten):\n" + "\n".join(deleted)
                )

            show_message(
                self.window,
                "Deine Sicherung wurde erstellt",
                message,
                kind="success",
            )

        except (
            OSError,
            RuntimeError,
            zipfile.BadZipFile,
            subprocess.SubprocessError,
        ) as exc:
            self.status_label.set_text("Die Sicherung ist fehlgeschlagen.")
            show_message(
                self.window, "Sicherung fehlgeschlagen", str(exc),
                kind="error",
            )

    def restore(self, _button):
        """Stellt eine ausgewählte ZIP-Sicherung wieder her."""
        archive_path = choose_file(self.window, "open", self.folder)

        if not archive_path:
            self.status_label.set_text("Wiederherstellung abgebrochen.")
            return

        self._restore_from(archive_path)

    def _restore_from(self, archive_path):
        """Zeigt die Vorschau an und stellt bei Bestätigung wieder her."""
        try:
            preview = PreviewWindow(self.window, archive_path)
        except (
            OSError,
            RuntimeError,
            zipfile.BadZipFile,
            KeyError,
            ValueError,
            UnicodeDecodeError,
        ) as exc:
            self.status_label.set_text(
                "Die Wiederherstellung ist fehlgeschlagen."
            )
            show_message(
                self.window,
                "Sicherungsdatei konnte nicht gelesen werden",
                str(exc), kind="error",
            )
            return

        response = preview.run()
        preview.destroy()

        if response != Gtk.ResponseType.OK:
            self.status_label.set_text("Wiederherstellung abgebrochen.")
            return

        try:
            restored, missing, failed, warnings = restore_positions(
                archive_path
            )

            self.profiles.setdefault(
                self.active_profile, {}
            )["last_backup"] = str(archive_path)
            save_config(self.folder, self.profiles, self.active_profile)
            self.refresh_profile_ui()

            self.status_label.set_text(
                f"Wiederhergestellt: {restored} Symbolpositionen"
            )

            details = [
                f"Wiederhergestellte Symbolpositionen: {restored}"
            ]

            if missing:
                details.append(
                    f"\nFehlende Einträge "
                    f"(auf dem Desktop nicht vorhanden): {len(missing)}"
                )
                details.extend(missing[:15])
                if len(missing) > 15:
                    details.append("...")

            if failed:
                details.append(f"\nFehlgeschlagene Einträge: {len(failed)}")
                details.extend(failed[:15])
                if len(failed) > 15:
                    details.append("...")

            if warnings:
                details.append("\nWarnungen:")
                details.extend(warnings[:10])
                if len(warnings) > 10:
                    details.append("...")

            # Desktop-Anzeige automatisch aktualisieren
            # (entspricht F5 auf dem Desktop).
            time.sleep(0.3)
            refreshed = refresh_desktop()

            if refreshed:
                details.append(
                    "\nDie Desktop-Anzeige wurde automatisch "
                    "aktualisiert."
                )
            else:
                details.append(
                    "\nBitte anschließend auf dem Desktop F5 drücken."
                )

            show_message(
                self.window,
                "Wiederherstellung beendet",
                "\n".join(details),
                kind="success",
            )

        except (
            OSError,
            RuntimeError,
            zipfile.BadZipFile,
            KeyError,
            ValueError,
            UnicodeDecodeError,
            subprocess.SubprocessError,
        ) as exc:
            self.status_label.set_text(
                "Die Wiederherstellung ist fehlgeschlagen."
            )
            show_message(
                self.window, "Wiederherstellung fehlgeschlagen",
                str(exc), kind="error",
            )

    # --------------------------------------------------------
    # Beenden
    # --------------------------------------------------------

    def _quit_clicked(self, _button):
        if ask_yes_no(
            self.window,
            "Anwendung schließen?",
            f"Möchtest du {APP_NAME} beenden?",
            ok_label="Beenden",
            danger=True,
        ):
            self.window.destroy()

    def _on_delete_event(self, _widget, _event):
        if ask_yes_no(
            self.window,
            "Anwendung schließen?",
            f"Möchtest du {APP_NAME} beenden?",
            ok_label="Beenden",
            danger=True,
        ):
            return False  # Fenster darf geschlossen werden
        return True       # Schließen blockieren


# ============================================================
# Programmstart
# ============================================================

def main():
    DesktopApp()
    Gtk.main()


if __name__ == "__main__":
    main()
