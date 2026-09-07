# Schooltools TUI

Eine persönliche TUI zur Planung und Begleitung des Schulalltags.

## Entwicklung

Mit `uv sync` werden die App und die Entwicklungswerkzeuge installiert.
Mit installiertem `just` führt `just check` alle vier Prüfungen unten
nacheinander aus. Beim ersten Fehler stoppt die Prüfung; Dateien werden
dabei nicht automatisch korrigiert.

```bash
uv run schooltools-tui       # App starten
uv run pytest               # Tests ausführen
uv run ruff check .          # Code und Imports prüfen
uv run ruff format --check . # Formatierung prüfen
uv run pyright              # Typen im Anwendungscode prüfen
```

Automatische Bereinigung: `uv run ruff check . --fix`, danach
`uv run ruff format .`. Ruff prüft auch die Tests; Pyright prüft `src`.

## Geplanter Funktionsumfang für Version 1

### Einrichtung und Verwaltung

- Datenverzeichnis, Editor und aktives Schuljahr einrichten.
- Schuljahre anlegen und wechseln.
- Klassen mit ihren Fächern anlegen und verwalten.

### Stundenplan

- Stundenplan direkt in der TUI bearbeiten.
- Einträge anlegen, ändern und löschen.
- Aktuellen Wochentag und aktuelle Unterrichtsstunde hervorheben.

### Unterrichtssequenzen

- Wiederverwendbare Sequenzpläne pro Fach anlegen und pflegen.
- Sequenzen aus geordneten Stunden mit Titel, Aufgaben und Notizen aufbauen.
- Sequenzpläne einer Klasse als eigenen Stand zuweisen.
- Fortschritt pro Sequenz mit `next` und `previous` verwalten.

### Kalender und Ausfälle

- Bayerische Ferien und gesetzliche Feiertage berücksichtigen.
- Schulweite lokale Ausfälle verwalten.
- Klassenbezogene Ausfälle verwalten.
- Tatsächlich verfügbare Unterrichtsstunden berechnen.

### Ansichten

- Home-Ansicht mit Stundenplan und Fortschritt des Schuljahres.
- Klassenansichten mit nächster Stunde, Sequenzfortschritt und Stundenbilanz.

## Bedienung und Design

- Dauerhafte Navigation links, reine Inhaltsansichten rechts.
- Zwei Navigationsbereiche: `Ansichten` mit Home und Klassen sowie `Verwaltung` mit den zentralen Werkzeugen.
- `Tab` und `Shift+Tab` wechseln nur zwischen den beiden Navigationsbereichen; der Inhaltsbereich liegt nicht in der Fokusreihenfolge.
- Das Hervorheben unter `Ansichten` wechselt sofort die View; Einträge unter `Verwaltung` werden erst mit `Enter` geöffnet.
- Home zeigt den Stundenplan nur an; die Bearbeitung erfolgt über eine eigene Verwaltungsansicht.
- Die Sequenzbibliothek wird über `Verwaltung` geöffnet und bearbeitet Sequenzdateien im konfigurierten Editor.
- Bedienung mit Pfeiltasten, Vim-Motions und kurzen Commands.
- Häufige Aktionen mit möglichst wenigen Eingaben erreichen.
- Fokus, Auswahl und mögliche Aktionen jederzeit klar darstellen.
- Layout für unterschiedliche Terminalgrößen optimieren.
- Omarchy-Palette beim Start übernehmen und im Betrieb jede Sekunde auf Änderungen prüfen; bei vorübergehend ungültigen Dateien die letzten Farben behalten. Ohne verfügbare Palette zunächst Gruvbox verwenden.

## Datenspeicherung

- Lokale, lesbare Dateien ohne externe Datenbank.
- Stundenpläne als CSV-Dateien.
- Konfiguration, Klassen, Sequenzen, Status und Ausfälle als TOML-Dateien.
