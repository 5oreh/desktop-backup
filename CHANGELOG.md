# Änderungsprotokoll

## Version 2.5 (2026-11-24)

- Explizite Versionsfestlegung erweitert: `gi.require_version("Gdk", "3.0")` vor dem Import
- Dokumentation für ein eigenes GitHub-Repository ergänzt (dieses Repo)

## Version 2.4 (2026-11-23)

- **Automatisches Aufräumen im Sicherungsordner:** pro Profil werden nur die **5 neuesten** Sicherungen aufbewahrt; ältere Dateien desselben Profils werden nach jeder erfolgreichen Sicherung gelöscht
- Sortierung nach Änderungsdatum (neueste bleibt immer erhalten); Löschfehler einzelner Dateien werden ignoriert
- Hinweise auf der Ordner-Karte und in der Statusmeldung angepasst

## Version 2.3 (2026-11-23)

- Vorschau: Nummern der Positionen werden jetzt **einheitlich unten rechts neben dem Punkt** gezeichnet (keine wandelnde Platzierung mehr)
- Am rechten/unteren Rand verschiebt sich die Zahl leicht nach innen, damit nichts abgeschnitten wird
- Überflüssige Ausweichlogik (links/rechts/über/unter dem Punkt) entfernt

## Version 2.2

- Vorschaufenster vergrößert (+ Standardgröße 1150 × 780, beliebig skalierbar/maximierbar)
- Vorschau-Diagramm auf 620 px Breite vergrößert; Dateiliste wächst entsprechend mit

## Version 2.1

- GTK-Fehler behoben: Tippfehler in EntryDialog (`hactivates_default` → `activates_default`), fehlerhafte Restbedingung in `_card()` entfernt
- Button-Styling nach Vorgabe: „Jetzt sichern“ hellblau hervorgehoben, „Beenden“ als destruktive Fläche inkl. rot bestätigter Beenden-Dialoge

## Version 2.0 (GTK-Version)

- Vollständige Neuentwicklung unter PyGObject / GTK 3 (native Dialoge statt Tkinter)
- Cairo-Vorschau der Positionen, TreeView-Dateiliste, HeaderBar, Karten-Design (CSS)
- Konfigurationsdatei blieb abwärtskompatibel zu den 1.x-Versionen (Automigration)

## Version 1.x (Tkinter-Versionen)

- 1.3 → 1.3.1: Trennung von `failed` und `missing` bei der Wiederherstellung; `"positions": null` in Sicherungen als leerer Zustand behandelt
- 1.4 → 1.4.1: Profilverwaltung (mehrere Desktop-/Monitor-Layouts), Vorschau-Dialog, Fenstergröße vergrößert
- 1.5: Automatische Desktop-Aktualisierung nach dem Wiederherstellen (xdotool, Fallback Neustart von `nemo-desktop`)
