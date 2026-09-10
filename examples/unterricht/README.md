# Neutrales Formatbeispiel

Dieses kleine Beispiel zeigt den Materialvertrag, keine ausgearbeitete
Unterrichtssequenz. Es gehört nicht zu den Defaults und wird bei der Einrichtung
nicht in die persönliche Sequenzbibliothek kopiert.

`stunde-vorlage.toml` zeigt eine leere Stunde mit allen optionalen Feldern
und fünf kommentierten Phasenvorschlägen. Sie ist eine Kopiervorlage, keine
zusätzliche Stunde der Beispielsequenz.

Unter `sequences/6/mathematik/formatbeispiel/` stehen:

- `sequenz.toml`: Metadaten und geordnete Stundenverweise.
- `stunden/anteile/stunde.toml`: Ziele, benötigtes Material, Aufgaben und Phasen.
- `stunden/anteile/vorbereitung.md`: freier Markdown-Inhalt mit relativer Abbildung.
- `aufgaben/vergleichen/aufgabe.md` und `loesung.md`: Aufgabe und zugehörige Lösung.
- `dateien/anteile.svg`: kleine, neutrale Beispielabbildung. Die tatsächliche
  Terminaldarstellung von SVG wird bei der Renderer-Integration umgesetzt.

Persönliche Vorbereitung gehört in dein konfiguriertes Pult-Datenverzeichnis
außerhalb dieses Repositorys. Bearbeite dafür nicht dieses Muster oder die
versionierten Defaults. Falls du das Muster ausprobieren möchtest, kopiere nur
seinen Sequenzordner in `sequences/6/mathematik/` deiner persönlichen Datenablage,
sofern dort noch kein Ordner `formatbeispiel` existiert.

Die öffentlich mitgelieferten Defaults enthalten weiterhin lediglich
Lehrplanstruktur und leere Planungsstunden. Persönliche Inhalte werden nicht
zurück ins Repository synchronisiert und nicht durch Git-Push veröffentlicht.
