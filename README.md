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

## Lizenz und Quellen

Der eigene Programmcode steht unter **GNU GPL Version 3 oder später**
([Lizenztext](LICENSE), [Urheber- und Lizenzhinweise](COPYRIGHT)). PULT wird ohne
Gewährleistung bereitgestellt, soweit gesetzlich zulässig.
Die Herkunft der Lehrplanvorlagen, Kalenderdaten und Bibliotheken ist in
[Quellen und Fremdbestandteile](SOURCES.md) dokumentiert.

## Starten

Voraussetzungen: [uv](https://docs.astral.sh/uv/) und ein Terminal mit
Unicode-Unterstützung. PULT 1.0.1 direkt aus dem GitHub-Release installieren
(kein Klonen des Projekts nötig):

```sh
uv tool install --python 3.11 https://github.com/lukaspodobnik/pult/releases/download/v1.0.1/pult-1.0.1-py3-none-any.whl
```

Eine fehlende Python-Version lädt uv bei Bedarf herunter. Anschließend starten:

```sh
pult
```

Danach ist `pult` aus jedem Verzeichnis aufrufbar, ohne die Projektumgebung zu
aktivieren. Falls uv auf einen fehlenden Suchpfad hinweist: `uv tool update-shell`
ausführen und ein neues Terminal öffnen. Die Shell vervollständigt den Programmnamen
mit Tab. Ein Editor muss zusätzlich installiert sein, beispielsweise Neovim.

Alternativ aus einem heruntergeladenen oder geklonten Projektordner:

```sh
uv tool install .
```

Bei dieser lokalen Installation übernimmt nach einer Aktualisierung des
Projektordners `uv tool install --force .` den neuen Stand.
`uv tool uninstall pult` entfernt die Installation, nicht deine
Konfiguration oder Unterrichtsdaten. Ein AUR-Paket ist noch nicht veröffentlicht.

Beim ersten Start Datenverzeichnis, Editor und Schuljahr auswählen. Danach unter
**Verwaltung → Klassen** Klassen anlegen (z. B. `9B`); die führende Zahl bestimmt
die Jahrgangsstufe und die angebotenen Fächer. Anschließend den Stundenplan füllen.

## Bedienung

- **Tab / Shift+Tab:** Fokus wechseln. Im Hauptbildschirm zwischen Ansichten, Unterricht und Verwaltung.
- **Pfeiltasten oder h/j/k/l:** Navigieren; in Textfeldern bleiben Buchstaben normale Eingaben.
- **Enter:** Werkzeug öffnen, Auswahl bestätigen oder Stundenplanzelle bearbeiten.
- **o:** Mit Fokus auf Ansichten die angezeigte nächste Stunde im Unterrichtsviewer öffnen; Escape führt zurück. Ohne nächste Stunde ist die Aktion deaktiviert.
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
  Mit Tab in die rechte Vorschau wechseln und mit ↑/↓ ganze Stundenblöcke auswählen.
  Enter öffnet die ausgewählte Stunde im Unterrichtsviewer; Esc führt zur Vorschau zurück.
  **e** auf einer Sequenz öffnet ihre TOML-Datei im Editor. Nach der Rückkehr wird sie
  neu geladen und validiert. Die Datei `sequenz.toml` enthält Metadaten und geordnete
  Stunden-IDs; die Stunden liegen in eigenen Ordnern. IDs bleiben stabil, da
  Protokolle darauf verweisen. Das neue Format ist im
  [Materialvertrag](docs/materialvertrag.md) beschrieben.
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

Enthalten sind Mathematik- und Informatiksequenzen der hinterlegten bayerischen
Gymnasiallehrpläne und Kalender von **2025/26 bis 2029/30**. Nur Jahre mit gültigem lokalem
Kalender sind auswählbar. Quellen stehen in den Kalenderdateien.

Auf Omarchy folgt das Farbschema automatisch dem aktuellen Theme; sonst wird Gruvbox
verwendet. Das Layout ist für etwa **206 × 46 Zeichen** ausgelegt. Die Standardzeiten
umfassen acht Stunden. Eine flexiblere Darstellung längerer Unterrichtstage und die
Feinausrichtung mit echten Unterrichtsinhalten sind für später vorgesehen.

## Weitere Einstellungen

Unter **Einstellungen → Stundenzeiten** lassen sich Beginn und Ende jeder Stunde
im Format `HH:MM` ändern. Die Zeiten gelten für alle Schuljahre und werden direkt
im eigenen Dialog gespeichert; Anzahl und Nummerierung bleiben unverändert.
Ohne Anpassung gelten die mitgelieferten Standardzeiten.
**Einstellungen → Über PULT / Lizenz** zeigt Version, Quellen und den vollständigen
GPL-Lizenztext auch offline.

## Entwicklung

```sh
uv sync
uv run pult                      # aus der Entwicklungsumgebung starten
just check                       # Ruff, Formatprüfung, Pyright und pytest
uv run pytest                    # nur Tests
uv run ruff check . --fix         # automatische Codekorrekturen
uv run ruff format .              # Formatierung
```

Für einen überall verfügbaren Entwicklungsstand: `uv tool install --editable .`.
Dabei bleibt die Installation mit diesem Projektordner verbunden.

Tests verwenden temporäre Datenverzeichnisse. Quellcode liegt in `src/pult/`, Tests in
`tests/`. Fachlogik und Darstellung sind getrennt; die Sequenzbibliothek wird gemeinsam
gecacht, Jahresdaten bleiben getrennt.

### Eigene Unterrichtsmaterialien

Die Defaults liefern Lehrplanstruktur und leere Planungsstunden. Bei der
Einrichtung werden pro Sequenz leere Ordner für Aufgaben und Begleitdateien
angelegt. Deine ausgearbeiteten Inhalte bleiben im persönlichen Datenverzeichnis
außerhalb dieses Repositorys. Sie werden nicht in die Defaults zurückübertragen.
Ein [neutrales Formatbeispiel](examples/unterricht/README.md) zeigt den Aufbau,
ohne automatisch in deine Sequenzbibliothek übernommen zu werden.

### Unterrichtsviewer (Entwicklungsstand)

In der Sequenzbibliothek mit Tab in die rechte Vorschau wechseln, die Stunde
mit ↑/↓ auswählen und Enter drücken. Der Viewer lädt die Dateien dieser Stunde.
Links bleiben die Stunden derselben Sequenz erreichbar. Esc kehrt zur bisherigen
Auswahl der Sequenzvorschau zurück.

- **Leertaste:** Vorbereitung / Aufgaben. Lösungen stehen direkt unter den Aufgaben.
- **Tab:** Zwischen Stundenliste, Inhalt, Zielen und Verlauf wechseln.
- **e:** Vorbereitung im konfigurierten Editor bearbeiten; eine fehlende Datei wird
  erst beim Bearbeiten angelegt. Die automatisch angezeigte Materialliste bleibt in TOML.
- **m:** `stunde.toml` für Titel, Ziele, benötigtes Material, Aufgabenverweise und Phasen bearbeiten.

Nach dem Editor werden die Dateien neu geladen. Bei Fehlern bleibt der letzte
 gültige Stand sichtbar und Pult meldet die betroffene Datei. Die fehlerhafte Datei
wird nicht automatisch zurückgesetzt.

Grafische Formeln und SVG-Abbildungen benötigen **Node.js** und **rsvg-convert**
(unter Arch: `nodejs` und `librsvg`) sowie ein Terminal mit passender Bildunterstützung,
beispielsweise Foot mit Sixel. MathJax ist im Pult-Paket enthalten; npm ist zur
Benutzung nicht nötig. Es wird kein Browser geöffnet und nichts ins Internet gesendet.
Ohne Grafikunterstützung erscheinen Formelquellen beziehungsweise Bildhinweise;
das ist keine gleichwertige mathematische Darstellung. Codeblöcke mit Sprachangabe
werden als normaler Terminaltext mit Syntaxhervorhebung dargestellt.

Formeln nutzen eine Computer-Modern-basierte TeX-Schrift und unterstützen etwa
`aligned`. Bilder werden relativ zur jeweiligen Markdown-Datei innerhalb des
Sequenzordners aufgelöst. Die erste Integration unterstützt Formeln in normalen
Absätzen und eigenen Blöcken; Mathematik in verschachtelten Listen und Tabellen
ist noch nicht vollständig umgesetzt. Das Layout bleibt auf Vollbild ausgelegt.

Der Unterrichtsviewer ist über die Sequenzvorschau sowie mit **o** direkt aus
der Übersicht und den Klassenansichten erreichbar. Die Darstellung benötigt keine Dateien
aus `prototypes/`; gerenderte Bilder liegen im lokalen Cache unter
`$XDG_CACHE_HOME/pult/materials` beziehungsweise `~/.cache/pult/materials`.
