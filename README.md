# PULT

```text
╔══╗ ╦  ╦ ╦  ╔═╦═╗
║  ║ ║  ║ ║    ║
╠══╝ ║  ║ ║    ║
║    ║  ║ ║    ║
╩    ╚══╝ ╚══╝ ╩
```

Dein Unterrichtsplaner im Terminal: Stundenplan, wiederverwendbare Sequenzen,
Leistungsnachweise und Unterrichtsprotokoll mit Fortschritt pro Klasse und Fach.
Lokal, ohne Konto und im Alltag offline nutzbar. Ein persönliches Lernprojekt
auf Basis von Textual, mit Vorlagen für Mathematik und Informatik am bayerischen Gymnasium.

## Starten

Voraussetzungen: [uv](https://docs.astral.sh/uv/) und ein Terminal mit
Unicode-Unterstützung. PULT 1.2.0 nach Veröffentlichung direkt aus dem GitHub-Release installieren:

```sh
uv tool install --python 3.11 https://github.com/lukaspodobnik/pult/releases/download/v1.2.0/pult-1.2.0-py3-none-any.whl
pult
```

Eine fehlende Python-Version lädt uv bei Bedarf herunter. Falls uv auf einen
fehlenden Suchpfad hinweist: `uv tool update-shell` ausführen und ein neues
Terminal öffnen. Zum Bearbeiten von Unterrichtsmaterialien wird zusätzlich ein
Editor benötigt, beispielsweise Neovim.

Alternativ aus einem heruntergeladenen oder geklonten Projektordner installieren:

```sh
uv tool install .
```

Nach einer Aktualisierung des Projektordners übernimmt `uv tool install --force .`
den neuen Stand. `uv tool uninstall pult` entfernt die Installation, nicht deine
Konfiguration oder Unterrichtsdaten. Ein AUR-Paket ist noch nicht veröffentlicht.

Beim ersten Start Datenverzeichnis, Editor und Schuljahr auswählen. Unter
**Verwaltung → Klassen** Klassen anlegen (z. B. `9B`); die führende Zahl bestimmt
die Jahrgangsstufe und die angebotenen Fächer. Anschließend den Stundenplan füllen.

## Bedienung und Ansichten

| Taste | Aktion |
| --- | --- |
| F1 | Hilfe zur aktuellen Ansicht und zum aktuellen Fokus |
| Tab / Shift+Tab | Fokus wechseln |
| Pfeiltasten oder h/j/k/l | Navigieren; in Textfeldern bleiben Buchstaben normale Eingaben |
| Enter | Werkzeug öffnen, Auswahl bestätigen oder Stundenplanzelle bearbeiten |
| `o` | Mit Fokus auf **Ansichten** die nächste Stunde öffnen; bei einem LNW dessen Verwaltung |
| F2 | Zur Übersicht und zur Ansichtenauswahl zurückkehren |
| Escape | Zurück bzw. abbrechen |
| `q` | Beenden, außer in Texteingaben |

Die Ansichten wechseln beim Hervorheben. Die Übersicht zeigt **HEUTE**, den
Stundenplan, die **NÄCHSTE STUNDE** und eine **KLASSENÜBERSICHT** mit Fach,
Stundendifferenz, nächstem Leistungsnachweis sowie den Zählern **Groß** und **Klein**.
Stundenplan und Tagesplan bieten Platz für sechs Stunden; weitere Einträge sind scrollbar.
Die Klassenansichten zeigen je Fach Sequenzfortschritt, Stundenbilanz und nächste
Stunde. Bei vorhandenen LNWs wird die Bilanz zur **ÜBERSICHT** mit LNW-Informationen.

### Unterricht protokollieren

Die folgenden Befehle gelten mit Fokus auf **Ansichten**: in der Übersicht für den
global nächsten offenen Termin, in einer Klassenansicht für das gewählte Fach.
Vergangene, nicht protokollierte Termine bleiben offen und können nachgetragen werden.

| Taste | Aktion |
| --- | --- |
| `n` | Stunde abschließen und Sequenzfortschritt weiterführen; einen LNW als durchgeführt protokollieren, ohne die Sequenz weiterzuschalten |
| `s` | Sequenzstunde überspringen, ohne einen Termin zu verbrauchen |
| `c` | Termin verbuchen; Sequenzstunde bleibt offen |
| `a` | Spontanen Unterrichtsausfall mit Begründung verbuchen |
| `z` | Zusatzunterricht eintragen |
| `p` | Letzten Eintrag des Fachs nach Bestätigung zurücknehmen; in der Übersicht den dort zuletzt abgeschlossenen LNW zurücknehmen |
| `w` | Aktive Sequenz wechseln, nur in der Klassenansicht |
| `u` | Unterrichtsprotokoll des Fachs öffnen, nur in der Klassenansicht |

Die Unterrichtsaktionen `s`, `c` und `a` gelten nicht für LNWs. Einen ausgefallenen
LNW stattdessen in der Verwaltung verschieben oder löschen. Nach Abschluss einer
Sequenz wird die nächste offene Sequenz zur Auswahl angeboten.

## Verwaltung und Einstellungen

- **Klassen:** Klassen und Fächer verwalten; zugehörige Unterrichtstermine einsehen.
- **Stundenplan:** Enter bearbeitet eine Zelle. Speichern und Löschen sichern sofort;
  Abbrechen verwirft die Eingabe. Die Verwaltung zeigt alle konfigurierten Stunden.
- **Ausfälle:** Ganztägige Ausfälle schulweit oder für eine Klasse anlegen und
  betroffene Unterrichtstermine einsehen. Ausfälle werden wie Ferien berücksichtigt.
- **Leistungsnachweise:** Termine planen, bearbeiten, löschen und als durchgeführt
  markieren; siehe unten.
- **Protokoll:** Chronologische Einträge nach Klasse und Fach; der neueste steht unten.
- **Einstellungen:** Editor und Schuljahr wählen sowie Stundenzeiten und LNW-Vorgaben
  bearbeiten. Neue Jahre werden automatisch vorbereitet; Klassen und Stundenplan
  werden nicht automatisch übernommen. Ab dem ersten Schultag bietet PULT den Wechsel
  ins aktuelle neuere Schuljahr an.

Unter **Einstellungen → Stundenzeiten** lassen sich Beginn und Ende jeder Stunde
im Format `HH:MM` ändern. Sie gelten für alle Schuljahre und werden direkt im Dialog
gespeichert. Neue Datenablagen enthalten elf voreingestellte Stundenzeiten.

### Leistungsnachweise planen

PULT unterstützt Schulaufgaben (**SA**), Stegreifaufgaben (**EX**), angekündigte
kleine Leistungsnachweise (**AKL**) und Jahrgangsstufentests (**JST**, etwa den BMT).
Im Dialog werden nur die für Fach und Jahrgangsstufe erlaubten Arten angeboten;
beim Speichern werden die Vorgaben erneut geprüft.

Ein Termin enthält Klasse, Fach, Art, Datum, Beginn als Stundennummer und Dauer
in Minuten. Belegte Unterrichtsstunden werden gesondert ausgewählt und in der
Stundenbilanz berücksichtigt. Passender regulärer Unterricht zur gewählten
Startstunde wird automatisch markiert. Auch Termine ohne belegte Unterrichtsstunden
sind möglich. Die Nummer, etwa „2. Schulaufgabe“, wird aus der Terminreihenfolge abgeleitet.

LNWs erscheinen in **HEUTE** und **NÄCHSTE STUNDE**. Mit `n` oder **Abschließen**
in der LNW-Verwaltung werden sie im Unterrichtsprotokoll erfasst. **Rückgängig**
öffnet sie wieder; vor dem Bearbeiten oder Löschen eines durchgeführten LNWs muss
sein Abschluss zurückgenommen werden. Konflikte mit Ferien oder Ausfällen und
Widersprüche zu erlaubten Arten werden angezeigt, ohne bestehende Termine automatisch zu ändern.

Unter **Einstellungen → Leistungsnachweise** gelten Vorgaben je Fach und
Jahrgangsstufe für das ausgewählte Schuljahr: erlaubte Arten sowie jährliche
Mindestzahlen für große schriftliche LNWs (SA) und kleine schriftliche LNWs
(EX und AKL gemeinsam). Leere Mindestfelder bedeuten keine Mindestvorgabe.
Informatik bis Jahrgangsstufe 11 startet mit zwei kleinen schriftlichen LNWs pro
Jahr als anpassbarem Schulstandard. Beim Einrichten eines Schuljahres werden die
letzten früheren Vorgaben übernommen; andernfalls gelten die mitgelieferten Standards.

Die Klassenübersicht zählt **durchgeführte** LNWs:

- `x/y`: durchgeführt / Mindestzahl; auch mehr als die Mindestzahl ist möglich.
- Eine Zahl: durchgeführt, ohne Mindestvorgabe.
- `—`: Für diese Kategorie ist keine Art erlaubt.

Der nächste LNW steht daneben mit Datum. Jahrgangsstufentests erscheinen weder
in dieser Terminspalte noch in den Zählern und erfüllen keine Mindestzahl.
**NOCH ZU PLANEN** in der LNW-Verwaltung zeigt dagegen, was nach Anrechnung bereits
durchgeführter und konfliktfrei geplanter, erlaubter LNWs zur Jahresmindestzahl fehlt.

## Sequenzen und Unterrichtsmaterialien

Unter **Unterricht → Sequenzen** Fach, Jahrgang und Abschnitt wählen. Die Vorschau
folgt der Auswahl. Mit Tab in die Vorschau wechseln, mit ↑/↓ eine Stunde auswählen
und mit Enter den Unterrichtsviewer öffnen. `e` auf einer Sequenz öffnet ihre
TOML-Datei im Editor; nach der Rückkehr wird sie neu geladen und validiert.

Unter **Unterricht → Lehrplan** folgt die Leseansicht der Auswahl im Baum.
Mathematik enthält zusätzlich Leitideen, Kompetenzen, Anforderungsbereiche und
Operatoren. Persönliche Dateien unter `curriculum/` haben Vorrang vor den Defaults.

Die mitgelieferten Sequenzen enthalten Lehrplanstruktur und leere Planungsstunden.
Eigene Inhalte bleiben im persönlichen Datenverzeichnis. Aufbau und stabile IDs
sind im [Materialvertrag](src/pult/defaults/vorbereitung/materialvertrag.md) beschrieben;
ein [neutrales Beispiel](examples/unterricht/README.md) zeigt das Dateiformat.

### Unterrichts- und Aufgabenviewer

- **Leertaste:** Zwischen Vorbereitung und Aufgaben wechseln; Lösungen stehen unter den Aufgaben.
- **e:** Den sichtbaren Inhalt im Editor bearbeiten, bei Aufgaben nach Auswahl von Aufgabe oder Lösung.
- **m:** `stunde.toml` für Titel, Ziele, Material, Aufgabenverweise und Phasen bearbeiten.
- **Escape:** Zur vorherigen Ansicht zurückkehren.

In der Sequenzbibliothek öffnet `a` alle Aufgaben der Sequenz, auch noch keiner
Stunde zugeordnete. Dort bearbeitet `e` eine Aufgabe oder Lösung; `n` legt nach
Eingabe eines Titels eine neue Aufgabe an und öffnet beide Dateien im Editor.
Die Zuordnung zu Stunden erfolgt in `stunde.toml` unter `aufgaben`. Änderungen an
einer Aufgabe gelten für alle Stunden, die darauf verweisen. Längere Inhalte lassen
sich mit der Maus scrollen.

Nach dem Editor lädt PULT die Dateien neu. Bei Fehlern bleibt der letzte gültige
Stand sichtbar; die betroffene Datei wird gemeldet und nicht automatisch zurückgesetzt.

Grafische Formeln und SVG-Abbildungen benötigen **Node.js**, **rsvg-convert**
(unter Arch: `nodejs` und `librsvg`) und ein Terminal mit passender Bildunterstützung,
etwa Foot mit Sixel. MathJax ist enthalten; npm und Browser sind zur Benutzung
nicht nötig. Ohne Grafikunterstützung erscheinen Formelquellen bzw. Bildhinweise.
Mathematik in verschachtelten Listen und Tabellen ist noch nicht vollständig unterstützt.
Bilder werden relativ zur Markdown-Datei innerhalb des Sequenzordners aufgelöst.
Gerenderte Bilder liegen unter `$XDG_CACHE_HOME/pult/materials` bzw.
`~/.cache/pult/materials`.

## Daten und Darstellung

Die Konfiguration liegt unter `~/.config/pult/config.toml`. Das gewählte
Datenverzeichnis enthält:

- `subjects.toml` und `periods.toml`: Fächer und gemeinsame Stundenzeiten.
- `sequences/`, `curriculum/` und `vorbereitung/`: Unterrichtsmaterialien und Referenzen.
- `calendars/`: Kalender; enthalten sind **2025/26 bis 2029/30**. Nur Jahre mit gültigem lokalem Kalender sind auswählbar.
- `school-years/<Jahr>/`: Jahresdaten, darunter `assessment-requirements.toml`
  mit LNW-Vorgaben sowie je Klasse eine `assessments.toml` mit LNW-Terminen.

Stundenpläne sind CSV, übrige Fachdaten TOML. Vorhandene Dateien werden bei der
Einrichtung nicht überschrieben. **Sichere das gesamte Datenverzeichnis** vor
größeren manuellen Änderungen.

Auf Omarchy folgt das Farbschema dem aktuellen Theme; sonst verwendet PULT sein
eigenes dunkles Theme. Das Layout ist für etwa **206 × 46 Zeichen** ausgelegt;
zusätzliche Inhalte sind scrollbar.

## Entwicklung

```sh
uv sync
uv run pult                      # aus der Entwicklungsumgebung starten
just check                       # Ruff, Formatprüfung, Pyright und pytest
uv run pytest                    # nur Tests
uv run ruff check . --fix         # automatische Codekorrekturen
uv run ruff format .              # Formatierung
```

`uv tool install --editable .` macht den Entwicklungsstand überall aufrufbar.
Quellcode liegt in `src/pult/`, Tests in `tests/`. Tests verwenden temporäre
Datenverzeichnisse; eigene Unterrichtsdaten gehören nicht ins Repository.

## Lizenz und Quellen

Der eigene Programmcode steht unter **GNU GPL Version 3 oder später**
([Lizenztext](LICENSE), [Urheber- und Lizenzhinweise](COPYRIGHT)). PULT wird ohne
Gewährleistung bereitgestellt, soweit gesetzlich zulässig.
[Quellen und Fremdbestandteile](SOURCES.md) dokumentiert Lehrplanvorlagen,
Kalenderdaten und Bibliotheken. **Einstellungen → Über PULT / Lizenz** zeigt
Version, Quellen und Lizenztext auch offline.
