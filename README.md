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

Unter **Unterricht → Sequenzen** Fach, Jahrgang und nummerierten Lehrplanpunkt wählen.
Kapitelüberschriften werden nicht als zusätzliche Ebene angezeigt. Die Vorschau
folgt der Auswahl. Mit Tab in die Vorschau wechseln, mit ↑/↓ eine Stunde auswählen
und mit Enter den Unterrichtsviewer öffnen. `e` auf einer Sequenz öffnet ihre
TOML-Datei im Editor; nach der Rückkehr wird sie neu geladen und validiert.

Unter **Unterricht → Lehrplan** wählst du direkt Fach und Jahrgang. Die Fächer
sind beim Öffnen eingeklappt. Der vollständige
Lehrplan erscheint im gemeinsamen Dokumentbetrachter. Persönliche Dateien unter
`curriculum/` haben Vorrang vor den Defaults; weitere Gliederungsebenen entfallen.

Die mitgelieferten Sequenzen enthalten die Lehrplanstruktur und Stunden-IDs.
Eine gemeinsame Routine legt die fünf kurzen Musterdateien jeder Stunde bei der
Einrichtung an, ohne persönliche Dateien zu überschreiben. Dateiformat und
Validierung beschreibt der [Materialvertrag](src/pult/defaults/vorbereitung/materialvertrag.md);
ein [neutrales Beispiel](examples/unterricht/README.md) zeigt eigene Inhalte.

### Unterrichts- und Aufgabenansicht

Links stehen einzeilige Stundentitel und ein immer sichtbarer Materialkasten.
Rechts steht das breite Dokument, mit dem Sequenznamen als Rahmentitel.

- **Leertaste:** Vorbereitung / Planung mit Zielen und Verlauf wechseln.
- **e:** Vorbereitung bearbeiten; in der Planung Ziele oder Verlauf auswählen.
- **r:** Materialliste bearbeiten; Links sind im Materialkasten direkt zu öffnen.
- **m:** `stunde.toml` mit Titel, Aufgabenverweisen und optionalen `hinweise` bearbeiten (z. B. `hinweise = "Computerraum · Übungstheke"`).
- **a:** Aufgabenbibliothek der Sequenz öffnen; die erste vorgemerkte Aufgabe wird ausgewählt.
- **Escape:** Zurückkehren; beim Rückweg aus Aufgaben bleiben Modus und Leseposition erhalten.

`vorbereitung.md` ist frei gestaltbar. Als Konvention steht der Stundentitel als
`#`-Überschrift am Anfang. `ziele.md` enthält eine ungeordnete Liste.
`verlauf.md` verwendet ausschließlich `#` als Phasenüberschrift; die Inhalte
erscheinen in einer Tabelle. `material.md` enthält eine ungeordnete Liste aus
Dingen und benannten Datei- oder Webseitenlinks. Materiallinks gehören hierher.

Auch aus der Sequenzbibliothek öffnet **a** alle Aufgaben. Dort bearbeitet **e**
eine Aufgabe oder Lösung; **n** legt eine neue Aufgabe an. **s** blendet gezielt
die Lösung ein. Mit Stundenkontext merkt **v** eine Aufgabe vor oder entfernt
sie aus der Stunde. Die Auswahl allein verändert keine Zuordnung.
Die Vorschau der Sequenzbibliothek zeigt Ziele, keine Aufgaben-IDs.

Nach dem Editor lädt PULT die Dateien neu. Bei Fehlern bleibt der letzte gültige
Stand sichtbar; die betroffene Datei wird gemeldet.

### Schöne Dokumente im Terminal

Der gemeinsame Betrachter setzt Markdown, Tabellen, TeX (`$...$`, `$$...$$`)
und lokale Bilder mit **Playwright und Chromium**. Ein Browserfenster öffnet sich
dabei nicht. Einmalig nach der Installation:

```sh
python -m playwright install chromium --only-shell
```

Unter Linux gegebenenfalls `python -m playwright install-deps chromium` für die
Browser-Systembibliotheken ausführen. Das Dokument wird in voller verfügbarer
Breite gesetzt, in Bildabschnitte geteilt und in lesbarer Größe gescrollt.
Theme- und Breitenänderungen lösen eine neue Darstellung aus. **Ghostty** nutzt
das Kitty-Grafikprotokoll, **Foot** Sixel. Ohne passenden Grafikmodus oder Browser
bleibt PULT mit einer Textansicht nutzbar; TeX wird dann als Quelltext angezeigt.

MathJax ist lokal enthalten. Eigene Node.js-/npm-Projekte und `rsvg-convert` sind
nicht mehr nötig. Playwright bringt intern eine Node-Laufzeit mit, MathJax läuft
als JavaScript im unsichtbaren Browser. Dokumente werden offline gerendert;
Bilder müssen relativ zur Markdown-Datei im jeweiligen Sequenz- bzw.
Lehrplanordner liegen. Links im Dokumentbild öffnen sich nicht; nutze dafür
`material.md`. Der Cache liegt unter `$XDG_CACHE_HOME/pult/documents` bzw.
`~/.cache/pult/documents`.

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


### Dokumentschrift

Unter **Einstellungen → Dokumentschrift** gilt die Auswahl gemeinsam für
Vorbereitung, Planung, Aufgaben, Lösungen und Lehrpläne:

- **Automatisch** (Standard): Avenir Next, wenn alle benötigten Schriftschnitte
  verfügbar sind; sonst Source Sans 3.
- **Avenir Next**: nur auswählbar, wenn im lokalen Renderer verfügbar.
- **Source Sans 3**: immer verfügbar, lokal mitgeliefert.

Die Wahl wird in der globalen `config.toml` als `document_font` gespeichert
(`auto`, `avenir-next` oder `source-sans-3`). Bestehende Konfigurationen ohne
Eintrag verwenden automatisch den Standard. Falls eine gespeicherte Avenir-Wahl
auf einem anderen Gerät nicht verfügbar ist, greift Source Sans 3.
Ein Wechsel wirkt ohne Neustart auf die Dokumentansichten.

Fließtext und Überschriften verwenden dieselbe Schriftfamilie, Überschriften
Halbfett (600), Hervorhebungen Medium (500). Code verwendet die mitgelieferte
JetBrains Mono und Pygments-Syntaxfarben; MathJax behält seine Formelschrift.
Alle Schriftdateien und Renderer-Bestandteile funktionieren offline.
Avenir Next wird ausschließlich aus einer vorhandenen lokalen Installation
verwendet und nicht mitgeliefert. Quellen und Lizenzen: siehe `SOURCES.md` und
`src/pult/assets/fonts/`.

### Stoffverteilungsplan

Unter **UNTERRICHT → Stoffverteilungsplan** zeigt PULT den Jahresplan für die
ausgewählte Klasse und das Fach. Protokollierter Unterricht bleibt erhalten;
offene Stunden werden ab der aktiven Sequenz in Lehrplanreihenfolge auf die
verbleibenden Termine verteilt. Fortsetzungen und Zusatzunterricht zählen als
Unterrichtszeit; übersprungene Stunden, Ausfälle und Leistungsnachweise nicht.
Die Nummerierung beginnt bei jedem Sequenzwechsel erneut bei 1.

Ferien erscheinen als eine Abschnittszeile, Feiertage und lokale Ausfälle als
Termine ohne Nummer. Alle Leistungsnachweise der Klasse werden angezeigt, auch
Termine anderer Fächer oder außerhalb eigener Unterrichtsstunden. Nur belegte
eigene Stunden verdrängen Unterricht. Die Anmerkungen stammen aus optionalen
`hinweise` in `stunde.toml` und vorhandenen Protokoll-/Kalenderangaben.

Die Prognose folgt dem letzten verbuchten Unterrichtstermin,
nicht dem heutigen Datum. Frühere Lücken heißen „Nicht protokolliert“; nach
Ausschöpfen der Sequenzstunden bleiben Termine als „Noch nicht verplant“ sichtbar.
Der Plan wird beim erneuten Öffnen aus aktuellen Daten berechnet und nicht als
eigene Datei gespeichert. Ein PDF-Export folgt separat.
