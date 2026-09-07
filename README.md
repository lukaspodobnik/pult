# PULT

```text
╔══╗ ╦  ╦ ╦  ╔═╦═╗
║  ║ ║  ║ ║    ║
╠══╝ ║  ║ ║    ║
║    ║  ║ ║    ║
╩    ╚══╝ ╚══╝ ╩
```

Dein Unterrichtsplaner im Terminal: Stundenplan, wiederverwendbare Sequenzen,
Unterrichtsprotokoll und Fortschritt pro Klasse und Fach. Lokal, ohne Konto und
im Alltag offline nutzbar. Ein persönliches Lernprojekt auf Basis von Textual.

## Starten

Voraussetzungen: Python ab 3.11, [uv](https://docs.astral.sh/uv/) und ein Terminal
mit Unicode-Unterstützung. Im Projektverzeichnis:

```sh
uv sync
uv run pult
```

Beim ersten Start Datenverzeichnis, Editor und Schuljahr auswählen. Danach unter
**Verwaltung → Klassen** Klassen anlegen (z. B. `9B`); die führende Zahl bestimmt
die Jahrgangsstufe und die angebotenen Fächer. Anschließend den Stundenplan füllen.

## Bedienung

- **Tab / Shift+Tab:** Fokus wechseln. Im Hauptbildschirm nur zwischen Ansichten und Verwaltung.
- **Pfeiltasten oder h/j/k/l:** Navigieren; in Textfeldern bleiben Buchstaben normale Eingaben.
- **Enter:** Werkzeug öffnen, Auswahl bestätigen oder Stundenplanzelle bearbeiten.
- **F2:** Im Hauptbildschirm zur Übersicht und zum Ansichtenpicker zurückkehren.
- **Escape:** Zurück bzw. abbrechen. **q:** Beenden (außer in Texteingaben).
- Der Footer zeigt verfügbare Befehle. Kleine Terminals können mit der Maus gescrollt werden.

**Ansichten** wechseln beim Hervorheben: Die Übersicht zeigt Tagesplan, Stundenplan,
Schuljahresfortschritt und die nächste offene Unterrichtsstunde. Klassen sind nach
Fach aufgeteilt und zeigen Sequenzfortschritt und verbleibende Stundenbilanz.

### Unterricht protokollieren

Die Fortschrittsbefehle gelten nur mit Fokus auf **Ansichten**: in der Übersicht für die
global nächste offene Stunde, in einer Klassenansicht für das gewählte Klassen-Fach-Paar.
Vergangene, nicht protokollierte Termine bleiben offen – so ist Nachtragen möglich.

| Taste | Aktion |
| --- | --- |
| `n` | Stunde abschließen; Sequenzfortschritt und Unterrichtstermin weiterführen |
| `s` | Sequenzstunde überspringen, ohne einen Termin zu verbrauchen |
| `c` | Fortsetzen: Termin verbuchen, Sequenzstunde bleibt offen |
| `a` | Spontanen Ausfall mit Begründung verbuchen; Sequenzstunde bleibt offen |
| `z` | Zusatzunterricht eintragen, auch an zusätzlichen Terminen |
| `p` | Letzten Eintrag des Fachs nach Bestätigung zurücknehmen (nur Klassenansicht) |
| `w` | Aktive Sequenz wechseln (nur Klassenansicht) |
| `u` | Unterrichtsprotokoll des Fachs öffnen (nur Klassenansicht) |

Nach Abschluss einer Sequenz wird die nächste offene Sequenz zur Auswahl angeboten.
Balken unterscheiden abgeschlossene und übersprungene Stunden.

### Verwaltung

- **Sequenzen:** Fach → Jahrgang → Abschnitt wählen; die Vorschau folgt der Auswahl.
  Enter auf einer Sequenz öffnet ihre TOML-Datei im Editor. Nach der Rückkehr wird sie
  neu geladen und validiert. Titel, Aufgaben, Notizen und Stunden können bearbeitet
  werden. Bestehende IDs möglichst erhalten: Protokolle verweisen darauf.
- **Stundenplan:** Enter bearbeitet eine Zelle. „Übernehmen“ ändert den Entwurf;
  erst „Speichern“ schreibt die Datei. Klasse, Fach und Raum werden beim nächsten
  Eintrag vorgeschlagen. Abbrechen fragt nur bei tatsächlichen Änderungen nach.
- **Ausfälle:** Geplante ganztägige Ausfälle schulweit oder für eine Klasse anlegen/löschen.
  Sie werden wie Ferien bei der Terminplanung berücksichtigt.
- **Protokoll:** Chronologische Einträge nach Klasse und Fach; der neueste steht unten.
- **Einstellungen:** Editor und Schuljahr wählen. Neue Jahre werden automatisch vorbereitet;
  vorhandene Jahresdaten bleiben erhalten. Klassen und Stundenplan werden nicht automatisch
  übernommen. Ab dem ersten Schultag bietet PULT beim Start den Wechsel ins aktuelle neuere
  Jahr an. Abbrechen belässt das bisherige Jahr.

## Daten und Darstellung

Konfiguration: `~/.config/pult/config.toml`. Das gewählte Datenverzeichnis enthält
`subjects.toml`, `periods.toml`, die gemeinsame Bibliothek in `sequences/`, Kalender in
`calendars/` und Jahresdaten in `school-years/<Jahr>/`. Stundenpläne sind CSV, übrige
Fachdaten TOML. **Sichere das gesamte Datenverzeichnis** vor größeren manuellen Änderungen.
Die Konfiguration des früheren Projektnamens wird beim Umstieg gelesen, falls noch keine
PULT-Konfiguration existiert; Daten werden nicht verschoben.

Enthalten sind Mathematik- und Informatiksequenzen der hinterlegten bayerischen
Gymnasiallehrpläne und Kalender von **2025/26 bis 2029/30**. Nur Jahre mit gültigem lokalem
Kalender sind auswählbar. Quellen stehen in den Kalenderdateien.

Auf Omarchy folgt das Farbschema automatisch dem aktuellen Theme; sonst wird Gruvbox
verwendet. Das Layout ist für etwa **206 × 46 Zeichen** ausgelegt. Die Standardzeiten
umfassen acht Stunden. Eine flexiblere Darstellung längerer Unterrichtstage und die
Feinausrichtung mit echten Unterrichtsinhalten sind für später vorgesehen.

## Entwicklung

```sh
just check                       # Ruff, Formatprüfung, Pyright und pytest
uv run pytest                    # nur Tests
uv run ruff check . --fix         # automatische Codekorrekturen
uv run ruff format .              # Formatierung
```

Tests verwenden temporäre Datenverzeichnisse. Quellcode liegt in `src/pult/`, Tests in
`tests/`. Fachlogik und Darstellung sind getrennt; die Sequenzbibliothek wird gemeinsam
gecacht, Jahresdaten bleiben getrennt.
