# Desktop-Symbolpositionen

Sichern und Wiederherstellen der Desktop-Symbolpositionen unter **Linux Mint 22.3 (Cinnamon / Nemo)**.

Das Programm ist eine kleine GTK-3-Anwendung: Es liest die Symbolpositionen des Nemo-Desktops aus, speichert sie als ZIP-Archiv und stellt sie später wieder her – zum Beispiel nach einer Neuinstallation, einem Distributionswechsel oder beim Umstieg auf ein anderes Monitor-Layout.

---

## Funktionen

- **Sichern** aller Desktop-Symbolpositionen (`metadata::nemo-icon-position`) als ZIP-Datei im Sicherungsordner
- **Wiederherstellen** mit grafischer Vorschau: Nummern auf einem skalierten Desktop-Schema neben jedem Punkt, plus Dateiliste (fehlende Dateien werden rot markiert)
- **Automatische Desktop-Aktualisierung** nach dem Wiederherstellen (xdotool-F5 bzw. Neustart von `nemo-desktop`)
- **Desktop-Profile** (z. B. Laptop-Layout, Monitor-Ausbaustufen) – jedes mit eigener letzter Sicherung
- **Aufräumautomatik:** pro Profil bleiben nur die **5 neuesten Sicherungen** im Sicherungsordner, ältere werden beim Sichern gelöscht
- **Nur native GTK-Dialoge:** Dateiauswahl, Meldungen und Eingabedialoge im Systemdesign
- Kompatibilität der Konfigurationsdatei mit Programmversionen ≥ 1.x (automatische Migration beim Start)

## Installation

Unter Linux Mint 22.3 ist alles Notwendige vorinstalliert, Sichtprüfung empfohlen:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0
```

Start:

```bash
python3 Pfad/zum/desktop-symbolpositionen.py
```

Empfehlung: eine kleine Verknüpfung im Hauptmenü anlegen („Hauptmenü bearbeiten“ → Neuer Eintrag, Befehl wie oben), als Symbol kann manuell ein SVG gewählt werden.

## Benutzung

1. **Jetzt sichern** – erzeugt eine ZIP-Datei im Sicherungsordner (Name: Profil-Präfix + Zeitstempel; Profil „Standard“ erhält kein Präfix).
2. **Wiederherstellen** – Archiv auswählen, Vorschau prüfen (grüne/rote Markierung beachten), mit „Wiederherstellen“ bestätigen.
3. **Neues Profil / Umbenennen / Löschen** – für mehrere Monitor-Szenarien bzw. Laptop-Layouts.

### Sicherungsdateien

ZIP-Dateien mit dem Standard-Namensmuster:

```
[Profil_]Desktop-Sicherung_JJJJ-MM-TT_HH-MM-SS.zip
```

Inhalt:

- `positions.json` – Manifest mit Erstellungszeit, Desktop-Ordner und allen Positionen (`"name": "x,y"`)
- `nemo-desktop.dconf` – dconf-Dump von `/org/nemo/desktop/`
- `nemo-icon-view.dconf` – dconf-Dump von `/org/nemo/icon-view/`

### Konfiguration

`~/.config/desktop-symbolpositionen/config.json`

```json
{
  "folder": "/home/user/Dokumente/Desktop-Sicherungen",
  "profiles": {
    "Standard":   { "last_backup": null },
    "1920x1080":  { "last_backup": "/pfad/zu/…/1920x1080_Desktop-Sicherung_….zip" }
  },
  "active_profile": "Standard"
}
```

## Sicherheit & Schutzmechanismen

- Externe Aufrufe (`gio`, `dconf`, `xdotool`, `pkill`) ausschließlich ohne Shell, mit Argumentlisten → kein Injection-Risiko
- Namensprüfung (`is_safe_name`) gegen Pfad-Traversal aus manipulierten Archiven (`/`, `\\`, `.`-Einträge werden abgelehnt)
- Schreibzugriff auf die Konfiguration atomar (`.tmp` + `rename`)
- Löschen betrifft nur Sicherungsmuster des aktuellen Profils – andere Dateien im Ordner werden nicht angerührt

## Änderungsprotokoll

Siehe [CHANGELOG.md](CHANGELOG.md). Derzeitige Version: **2.5**.

## Technische Voraussetzungen

- Linux Mint 22.3 „Cinnamon“ (bzw. jede Distribution mit Python 3.8+, GTK 3, Nemo)
- Python 3, PyGObject (`gi`), Cairo
- Empfohlen: `xdotool` (für die automatische Desktop-Aktualisierung; andernfalls genügt F5 auf dem Desktop)

## License

Dieses Projekt ist unter der **GNU General Public License Version 3.0 oder einer späteren Version (GPL-3.0-or-later)** lizenziert.

Du darfst diese Software gemäß den Bedingungen der Lizenz frei verwenden, untersuchen, verändern und weiterverbreiten. Wenn du diese Software oder veränderte Versionen davon weiterverbreitest, musst du die Bedingungen der Lizenz **GPL-3.0-or-later** einhalten. Dazu gehört auch, den entsprechenden Quellcode zugänglich zu machen.

Den vollständigen Lizenztext findest du in der Datei LICENSE.md.

Copyright (c) 2026 - 5oreh
