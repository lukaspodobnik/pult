# PULT

```text
╔══╗ ╦  ╦ ╦  ╔═╦═╗
║  ║ ║  ║ ║    ║
╠══╝ ║  ║ ║    ║
║    ║  ║ ║    ║
╩    ╚══╝ ╚══╝ ╩
```

Unterricht planen und im Blick behalten: Stundenplan, wiederverwendbare Sequenzen,
Materialien, Leistungsnachweise und Fortschritt pro Klasse und Fach.
PULT läuft lokal im Terminal, ohne Konto und im Alltag offline. Ein persönliches
Projekt mit Python und Textual, mit Vorlagen für Mathematik und Informatik am
bayerischen Gymnasium.

## Installieren

Benötigt werden [uv](https://docs.astral.sh/uv/), ein Terminal mit Unicode und ein
Editor, etwa Neovim oder VS Code. Für die grafische Dokumentansicht eignen sich
**Ghostty** und **Foot**. Andere Terminals können die Textansicht verwenden.

PULT 1.3.1 nach Veröffentlichung aus dem GitHub-Release installieren:

```sh
uv tool install --python 3.11 https://github.com/lukaspodobnik/pult/releases/download/v1.3.1/pult-1.3.1-py3-none-any.whl
```

`pult` starten und **Dokumentdarstellung einrichten** wählen. PULT lädt den passenden
Chromium-Browser für Dokumentgrafik und PDF-Export selbst herunter. Die Einrichtung
ist auch unter **Einstellungen → Dokumentdarstellung einrichten** erreichbar.
Es öffnet sich kein Browserfenster. Mit **Später** bleibt die Textansicht nutzbar;
nach einem Playwright-Update wird die Einrichtung bei Bedarf erneut angeboten.

Unter Linux können zusätzliche Systembibliotheken nötig sein. PULT zeigt dafür
auf unterstützten Debian-/Ubuntu-Versionen einen kopierbaren Installationsbefehl.
Auf Arch/Omarchy gibt PULT Hinweise zu `pacman` und bietet bei bekannten
Bibliotheksnamen eine Dateisuche mit `pacman -F` an. Systempakete installiert man selbst im Terminal;
anschließend **Erneut prüfen** wählen. Arch wird von Playwright nicht offiziell
unterstützt; die vollständige Einrichtung auf einem frischen Arch-System ist
noch nicht verifiziert. Darstellung und Export funktionieren danach offline.

Alternativ im geklonten Projektordner `uv tool install .` ausführen; ein Update
übernimmt `uv tool install --force .`. Bei fehlendem Suchpfad hilft
`uv tool update-shell` und ein neues Terminal. `uv tool uninstall pult` entfernt
die Installation, lässt Konfiguration und Unterrichtsdaten bestehen.

## Einrichten und navigieren

Beim ersten Start Datenordner, Editor und Schuljahr auswählen. Danach unter
**Verwaltung → Klassen** Klassen und Fächer anlegen und den **Stundenplan** füllen.
Die führende Zahl einer Klasse, etwa `7D`, bestimmt ihre Jahrgangsstufe.

| Taste | Aktion |
| --- | --- |
| F1 | Hilfe für die aktuelle Ansicht und den Fokus |
| Tab / Shift+Tab | Fokus wechseln |
| Pfeile oder h/j/k/l | Navigieren; Textfelder behalten normale Buchstabeneingaben |
| Enter | Auswahl öffnen oder bestätigen |
| `o` | Mit Fokus auf **Ansichten** die nächste Stunde bzw. LNW-Verwaltung öffnen |
| F2 | Zur Übersicht und Ansichtenauswahl |
| Escape | Zurück oder abbrechen |
| `q` | Beenden, außer in Texteingaben |

Die **Übersicht** zeigt den heutigen Tag, Stundenplan, nächste Stunde und alle
Klassen. Der zeitlich nächste LNW ist hervorgehoben. In den **Klassenansichten**
stehen Fortschritt und Stundenbilanz je Fach. Unter **Verwaltung** werden Klassen,
Stundenplan, Ausfälle und Leistungsnachweise gepflegt; Änderungen werden beim
Speichern im jeweiligen Dialog gesichert.

## Unterricht protokollieren

Diese Tasten gelten mit Fokus auf **Ansichten**: in der Übersicht für den nächsten
offenen Termin, in einer Klassenansicht für das ausgewählte Fach. Vergangene
ungebuchte Termine bleiben offen und lassen sich nachtragen.

| Taste | Aktion |
| --- | --- |
| `n` | Stunde abschließen und zur nächsten Planstunde weitergehen |
| `c` | Termin verbuchen; die bearbeitete Planstunde bleibt offen |
| `s` | Planstunde überspringen, ohne einen Termin zu verbrauchen |
| `a` | Spontanen Unterrichtsausfall mit Begründung eintragen |
| `t` | Spontanunterricht mit Beschreibung eintragen; Planstunde bleibt offen |
| `z` | Zusätzlichen Termin außerhalb des Stundenplans eintragen |
| `p` | Letzte Buchung des Fachs nach Bestätigung zurücknehmen |
| `w` / `u` | In einer Klassenansicht Sequenz wechseln / Unterrichtsprotokoll öffnen |

`t` passt beispielsweise für eine ungeplante Übungsstunde vor einer Schulaufgabe.
Die Beschreibung wird im Stoffverteilungsplan zum Stundenthema. Bei `z` kann
optional die nächste Planstunde abgeschlossen werden. Nach Abschluss einer Sequenz
bietet PULT die nächste offene Sequenz an.

Bei einem LNW protokolliert `n` dessen Durchführung, ohne eine Planstunde zu
verbrauchen. `p` in der Übersicht nimmt den dort zuletzt abgeschlossenen LNW
zurück. Ausgefallene LNWs werden in der Verwaltung verschoben oder gelöscht.

## Sequenzen, Materialien und Lehrpläne

Unter **Unterricht → Sequenzen** Fach, Jahrgang und Lehrplanabschnitt wählen.
Die Vorschau zeigt Stunden und Ziele. Mit Tab in die Vorschau wechseln und eine
Stunde mit Enter öffnen. `e` auf einer Sequenz bearbeitet ihre `sequenz.toml`.
**Unterricht → Lehrplan** zeigt den vollständigen Fachlehrplan eines Jahrgangs.

In der **Stundenansicht** stehen links die Stunden und das Material, rechts das
Dokument. Die Vorbereitung ist freies Markdown für Hefteinträge, Übungen oder Notizen.

| Taste | Aktion in der Stundenansicht |
| --- | --- |
| Leertaste | Vorbereitung / Planung mit Zielen und Verlauf wechseln |
| `e` | Sichtbaren Inhalt bearbeiten; bei Planung Ziele oder Verlauf auswählen |
| `r` | Materialliste bearbeiten; ihre Links lassen sich direkt öffnen |
| `m` | Titel, Aufgabenverweise und optionale Hinweise bearbeiten |
| `a` | Aufgabenbibliothek der Sequenz öffnen |

Aufgaben werden einzeln mit optionaler Lösung gespeichert. In der
**Aufgabenbibliothek** legt `n` eine Aufgabe an, `e` bearbeitet sie und `s` wechselt
zur Lösung. Aus einer Stunde heraus merkt `v` die ausgewählte Aufgabe für diese
Stunde vor oder entfernt die Zuordnung. Die Auswahl allein ändert nichts.
Auch aus der Sequenzbibliothek öffnet `a` die Aufgaben.

Dateien und Regeln stehen im [Materialvertrag](src/pult/defaults/vorbereitung/materialvertrag.md);
ein [Unterrichtsbeispiel](examples/unterricht/README.md) zeigt das Format.
Bei der Einrichtung und beim Ergänzen von Stunden-IDs über den Sequenzeditor legt
PULT kurze Musterdateien an, ohne vorhandene Inhalte zu überschreiben.
Nach dem Editor werden Änderungen validiert; bei Fehlern bleibt die letzte gültige
Ansicht sichtbar. Stabile IDs erhalten, sobald Klassen darauf verweisen.

### Dokumentdarstellung

Der gemeinsame Betrachter setzt Markdown, Tabellen, TeX (`$…$`, `$$…$$`), Code mit
Syntaxfarben und lokale Bilder in einem unsichtbaren Chromium-Prozess. Ghostty
zeigt das Ergebnis über Kitty-Grafik, Foot über Sixel. Im Textmodus bleiben
Formeln als TeX-Quelltext lesbar. Links im Dokumentbild sind nicht anklickbar;
Materiallinks gehören deshalb in den eigenen Materialkasten.

Unter **Einstellungen → Dokumentschrift** gilt eine Auswahl für Dokumente und
Exporte: automatisch **Avenir Next**, wenn alle benötigten Schnitte installiert
sind, sonst die mitgelieferte **Source Sans 3**. Beide sind auch gezielt wählbar,
Avenir nur bei Verfügbarkeit. Code verwendet JetBrains Mono. Schriftdateien und
MathJax sind lokal enthalten; Avenir Next wird nicht mitgeliefert.

## Stoffverteilungsplan und PDF-Export

**Unterricht → Stoffverteilungsplan** zeigt den Jahresverlauf je Klasse und Fach:
protokollierte Stunden und eine Prognose der noch offenen Planstunden. Die
Prognose folgt dem letzten gebuchten Termin. Fortsetzungen, Spontanunterricht und
zusätzliche Termine zählen als Unterrichtszeit; Ausfälle und LNWs erhöhen die
Nummerierung nicht. Jede Sequenz beginnt wieder bei 1.

Ferien, neue Sequenzen und LNWs sind farblich erkennbar. Auch LNWs anderer Fächer
oder außerhalb eigener Stunden erscheinen; nur belegte eigene Termine verdrängen
Unterricht. Anmerkungen stammen aus den vorhandenen Daten, etwa `hinweise` in
`stunde.toml`. Die Tabelle wird mit der Maus gescrollt.

Mit **x** exportieren Stoffverteilungsplan und Stundenplanverwaltung die jeweilige
Ansicht als durchsuchbare A4-PDF mit Seitenzahlen und gewählter Dokumentschrift:

| Export | Format | Ablage im Datenordner |
| --- | --- | --- |
| Stoffverteilungsplan | Hochformat | `exports/<Jahr>/<Klasse>/stoffverteilungsplan-<Fach-ID>.pdf` |
| Stundenplan | Querformat | `exports/<Jahr>/uebersichten/stundenplan.pdf` |

Ein erneuter Export ersetzt die gleichnamige Datei erst nach erfolgreicher Erstellung.

## Leistungsnachweise und Einstellungen

PULT verwaltet Schulaufgaben, Stegreifaufgaben, angekündigte kleine LNWs und
Jahrgangsstufentests. Datum, Startstunde und Dauer bestimmen den Termin; belegte
Unterrichtsstunden werden gesondert ausgewählt. Termine ohne eigenen Unterricht
sind ebenfalls möglich. Konflikte mit Ferien, Ausfällen oder Vorgaben werden angezeigt.

Unter **Einstellungen** lassen sich erlaubte LNW-Arten und Mindestzahlen je Fach
und Jahrgang, Stundenzeiten, Editor, Dokumentschrift und Schuljahr anpassen.
Die Klassenübersicht zählt durchgeführte LNWs; „Noch zu planen“ berücksichtigt
zusätzlich konfliktfrei geplante LNWs. Jahrgangsstufentests erfüllen keine Mindestzahl.
Neue Schuljahre übernehmen die bisherigen LNW-Vorgaben, aber keine Klassen oder Stundenpläne.

## Eigene Daten

Die Konfiguration liegt in `~/.config/pult/config.toml`. Der gewählte Datenordner enthält:

- `sequences/`, `curriculum/`, `vorbereitung/`: Materialien, Lehrpläne und Anleitungen.
- `subjects.toml`, `periods.toml`: Fächer und gemeinsame Stundenzeiten.
- `calendars/`: Schuljahreskalender; mitgeliefert werden 2025/26 bis 2029/30.
- `school-years/<Jahr>/`: Klassen, Stundenplan, Protokolle, Ausfälle und LNWs.
- `exports/<Jahr>/`: erzeugte PDFs.

**Sichere den gesamten Datenordner.** Persönliche Dateien werden bei der Einrichtung
nicht überschrieben. Der Dokumentcache liegt unter `$XDG_CACHE_HOME/pult/documents`
bzw. `~/.cache/pult/documents`. Auf Omarchy folgt PULT dem aktuellen Theme;
sonst verwendet es sein dunkles Standardtheme. Das Layout ist für große
Terminalfenster ausgelegt, etwa 206 × 46 Zeichen.

## Entwicklung und Lizenz

```sh
uv sync --locked
uv run pult
just check        # Ruff, Formatprüfung, Pyright und Tests
uv build          # Wheel und Quellarchiv unter dist/
```

Code liegt in `src/pult/`, Tests in `tests/`. `PULT_TEST_BROWSER=1 uv run pytest
tests/test_material_rendering.py` prüft zusätzlich den echten Browserrenderer.
Die [Release-Notizen](CHANGELOG.md) beschreiben die Änderungen.

Der eigene Code steht unter **GPL-3.0-or-later** ([Lizenz](LICENSE),
[Urheberhinweise](COPYRIGHT)), ohne Gewährleistung. [Quellen und Fremdbestandteile](SOURCES.md)
dokumentiert Vorlagen, Kalender, Bibliotheken und Schriften.
**Einstellungen → Über PULT / Lizenz** zeigt die Hinweise auch offline.
