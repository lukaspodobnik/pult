# Materialvertrag für Unterrichtsmaterialien

Status: vereinbarte Grundlage für die nächste Pult-Erweiterung.
Datenmodell, Laden/Speichern und Defaults sind umgesetzt. Home, Klassenansicht
und Sequenzvorschau lesen Materiallisten aus dem Stundenmodell. Die Unterrichtsansicht ist über Enter in der Sequenzvorschau erreichbar, einschließlich
Vorbereitungs-Editor und lokalem Formelrenderer. Weitere Zugangswege folgen separat.
Die Beispieldaten des Darstellungsprototyps verwenden weiterhin ihr eigenes Format.

## Grundprinzip

TOML beschreibt die Struktur; Markdown enthält die Inhalte. Pult dient der
Organisation, Darstellung und dem Öffnen der Dateien im konfigurierten Editor.
Das Format schreibt keine Unterrichtsform vor und gilt fachübergreifend.
Unterricht wird allgemein vorbereitet, nicht für eine konkrete Klasse.

Es gibt drei Einheiten: Sequenz, Stunde und Aufgabe.

## Ordnerstruktur

```text
bruchzahlen/
├── sequenz.toml
├── stunden/
│   ├── brueche-erweitern/
│   │   ├── stunde.toml
│   │   └── vorbereitung.md
│   └── brueche-kuerzen/
│       ├── stunde.toml
│       └── vorbereitung.md
├── aufgaben/
│   ├── anteile-vergleichen/
│   │   ├── aufgabe.md
│   │   └── loesung.md
│   └── gezielt-erweitern/
│       ├── aufgabe.md
│       └── loesung.md
└── dateien/
    └── bruchstreifen.svg
```

Ordnernamen entsprechen den stabilen IDs. Stunden- und Aufgaben-IDs werden
innerhalb ihrer Sequenz aufgelöst. Titeländerungen und Umsortierungen verändern
keine IDs. Lesbare Nummerierungen sind Anzeigeinformationen, keine Identität.

## Sequenz

Die Sequenz behält ihre Angaben wie Titel, Fach und Jahrgang. Ihre geordnete
Stundenliste enthält künftig IDs statt eingebetteter Stundenbeschreibungen.

```toml
id = "bruchzahlen"
curriculum_section_id = "M6 1"
subject_id = "mathematik"
grade_level = 6
titel = "Bruchzahlen"
stunden = ["brueche-erweitern", "brueche-kuerzen"]
```

Die äußere Ablage bleibt `sequences/<Jahrgang>/<Fach-ID>/<Sequenz-ID>/`.
`curriculum_section_id`, `subject_id` und `grade_level` behalten die bisherigen
Feldnamen. Optional bleiben `recommended_lesson_count` sowie das gemeinsame Paar
`chapter_id`/`chapter_title` erhalten. Bei angegebener empfohlener Stundenzahl muss
weiterhin mindestens eine Planungsstunde existieren. Die geladenen
`Sequence.lessons` enthalten aufgelöste `Lesson`-Objekte; `Lesson.tasks` enthält
sequenzweit gemeinsam geladene `Task`-Objekte. Die Datei selbst speichert nur IDs.
Die Sequenzbibliothek bleibt der zentrale Überblick und lädt die referenzierten
Stunden. Zusammenfassungen werden aus den Stundendaten erzeugt, nicht zusätzlich
als eigener Überblick gepflegt.

## Stunde

Die ID ergibt sich aus dem Stundenordner. `stunde.toml` enthält den Titel,
Lernziele, benötigtes Material, geordnete Aufgabenverweise und geordnete Phasen.

```toml
titel = "Brüche erweitern"

ziele = [
    "Gleichwertige Brüche am Flächenmodell erklären.",
    "Brüche mit einem vorgegebenen Faktor erweitern.",
]

material = [
    "Zwei gleich große Papierstreifen",
    "Schere",
    "Arbeitsblatt „Bruchteile“, ein Exemplar pro Schüler",
]

aufgaben = ["anteile-vergleichen", "gezielt-erweitern"]

[[phasen]]
titel = "Einstieg"
text = "Zwei gleich große Papierstreifen unterschiedlich einteilen lassen."

[[phasen]]
titel = "Erarbeitung"
text = "Die Einteilungen vergleichen und gemeinsam die Erweiterungsregel entwickeln."

[[phasen]]
titel = "Sicherung"
text = "Regel und Beispiel an der Tafel festhalten."
```

`titel` ist erforderlich. `ziele`, `material`, `aufgaben` und `phasen` sind
optional und werden bei Fehlen als leere Listen geladen. Jede angegebene Phase
hat einen Titel und einen Text. Zeitangaben sind nicht Bestandteil des Verlaufs.
Die Reihenfolge der Phasen und Aufgaben entspricht der jeweiligen Liste.

Aufgaben sind direkt über die Stunde erreichbar; Verweise über Phasen sind
nicht erforderlich. Klassen, konkrete Termine, Fortschritt, Ausfälle und
Unterrichtsprotokolle gehören nicht in diese Materialdateien. Pults bestehende
Organisation einschließlich `skip`, `continue` und Zusatzstunden bleibt zuständig.

## Vorbereitung

`vorbereitung.md` ist der feste, aber optionale Begleiter einer Stunde. Sie hat
keine vorgeschriebenen Abschnitte. Möglich sind Definitionen, Merksätze,
Beispiele, Abbildungen, Gesprächsimpulse, Hinweise zur Verwendung von Material
oder Fundorte externer Dateien, etwa einer Präsentation auf dem iPad.

Pult öffnet die Datei zur Bearbeitung im konfigurierten Editor. Eine Stunde darf
auch ohne Vorbereitungsdatei existieren. Leere Inhalte ändern das Layout nicht;
wo nötig erscheint ein kurzer Leerhinweis.

## Benötigtes Material

Die einzige strukturierte Quelle ist `material` in `stunde.toml`. Die
Stunden-Dataclass erhält dafür eine Liste von Zeichenketten, standardmäßig leer.
Gemeint sind Dinge zum Bereitlegen oder Mitnehmen; Aufgabenverweise bleiben
separat. Es gibt keine Auswertung bestimmter Markdown-Überschriften.

Die Liste wird einmal gepflegt und mehrfach angezeigt:

- **Stundenansicht:** Pult setzt am Anfang der Vorbereitungsansicht automatisch
  einen kompakten Abschnitt „Benötigtes Material“. Danach folgt der Inhalt von
  `vorbereitung.md`. Es entsteht kein zusätzlicher Rahmen.
- **Home/Classview, nächste Stunde:** kurze Materialzeile in der Zusammenfassung.
- **Sequenzplan:** Material in der Zusammenfassung der jeweiligen Stunde.

Bei leerer Liste entfällt der Materialabschnitt beziehungsweise die Materialzeile.
Auch ohne `vorbereitung.md` wird eine vorhandene Materialliste angezeigt.
Der automatisch angezeigte Abschnitt wird nicht in die Markdown-Datei geschrieben.
Hinweise zur Verwendung des Materials stehen weiterhin in der Vorbereitung;
eine doppelte Pflege der Liste ist nicht vorgesehen.

## Aufgaben und Lösungen

Aufgaben liegen auf Sequenzebene und können aus mehreren Stunden referenziert
werden. Jeder Aufgabenordner enthält `aufgabe.md` und optional `loesung.md`.
Die Ordner-ID bleibt stabil. Die Aufgabenliste der Stunde bestimmt die
Anzeigereihenfolge. Eine spätere Arbeitsheftnummerierung verändert keine IDs.

In der Aufgabenansicht folgt die Lösung unmittelbar auf ihren Aufgabentext.
Ein zusätzlicher Knopf zum Einblenden ist nicht nötig, da die Ansicht für die
Lehrkraft bestimmt ist. Fehlt eine Lösung, wird kein Lösungsinhalt erfunden.

## Gemeinsamer Markdown-Vertrag

Für Vorbereitung, Aufgabentext und Lösung gilt dieselbe Darstellung:

- Überschriften, Absätze, Hervorhebungen, Listen, Links und einfache Tabellen.
- Inline-Mathematik mit `$…$`, abgesetzte Mathematik mit `$$…$$`.
- Mehrzeilige Umformungen, beispielsweise mit LaTeX-`aligned`.
- Codeblöcke mit Sprachangabe, etwa `python` oder `java`, mit Syntaxhervorhebung.
- Bilder über relative Dateipfade, bezogen auf die jeweilige Markdown-Datei.

Gewöhnlicher Text und Code bleiben Terminaltext. Mathematische Formeln erhalten
die vereinbarte Computer-Modern-basierte Schrift. Der Renderer verwendet einen
etablierten Markdown-Parser. Die Unterstützung konkreter Bildformate wird bei
der Integration geprüft; der Beispielpfad legt noch keine vollständige
Terminalunterstützung für SVG fest.

Lokale Begleitdateien liegen unter `dateien/`. Fundorte auf anderen Geräten
können einfache Hinweise im Vorbereitungstext sein. Pult muss externe
Präsentationen oder andere Begleitdateien nicht selbst darstellen können.

## Stundenansicht und Zusammenfassungen

Das gemeinsam erprobte Layout bleibt die Grundlage:

- Links: eigener Sequenzrahmen mit Metainformationen, darunter Stundenliste.
- Mitte: Vorbereitung oder Aufgaben; Stundentitel im Rahmen und dezenter
  Hinweis auf die aktive Ansicht. Lösungen direkt unter den Aufgaben.
- Rechts: getrennte Rahmen für Ziele und Verlauf. Der Verlauf zeigt fette
  Phasenüberschriften und darunter Text, ohne Zeitspalte.
- Oben und unten bleibt je eine Terminalzeile frei.

Die Anordnung ist fachübergreifend gleich. Benötigtes Material erscheint im
Vorbereitungsbereich wie oben beschrieben. Zusammenfassungen in anderen Views
nutzen dieselben strukturierten Stundendaten. Die optischen Feinheiten werden
bei der Integration an das bestehende Pult-Styling angepasst.

## Auslieferung und Umfang

Die öffentlichen Defaults enthalten die allgemeine Lehrplanstruktur und leere
Planungsstunden, keine persönliche Unterrichtsvorbereitung. Ein neutrales,
vollständiges Formatmuster liegt unter `examples/unterricht/`, außerhalb der
Defaults und der automatisch eingerichteten Sequenzbibliothek.

Bei der Einrichtung werden die Defaults weiterhin nach den bisherigen Kopierregeln
übernommen. Zusätzlich entstehen in jedem Sequenzordner die leeren Verzeichnisse
`stunden/`, `aufgaben/` und `dateien/`, sofern sie fehlen. Vorhandene Dateien
bleiben erhalten; Beispielaufgaben werden nicht in jede Sequenz kopiert.

Eigene Vorbereitungen, Aufgaben, Lösungen und Begleitdateien werden ausschließlich
in der persönlichen Datenablage außerhalb des Repositorys gepflegt. Es gibt
keine Rückübertragung in die Defaults und keine Veröffentlichung durch Pult.
Eine Migration bestehender Unterrichtsmaterialien ist nicht vorgesehen.

Nicht Bestandteil dieser Erweiterung sind KI-Erzeugung innerhalb von Pult,
KI-Kontextdateien, gesonderte fachliche oder didaktische Hintergrunddateien und
Export. Unterrichtsmaterialien können außerhalb von Pult mit KI-Unterstützung
erstellt und anschließend von der Lehrkraft geprüft und weiterentwickelt werden.


## Verhalten der Datenablage

Unbekannte TOML-Felder, leere Pflichttitel, ungültige oder doppelte Verweise und
fehlende referenzierte Stunden-/Aufgabendateien werden als Fehler mit Dateipfad
angezeigt. Referenz-IDs müssen bereits der kanonischen Kleinschreibung entsprechen.
Optionale Markdown-Dateien dürfen fehlen; vorhandener Markdown-Quelltext wird
unverändert geladen und gespeichert. Relative Bildverweise bleiben dadurch erhalten.
Entfernte Referenzen löschen keine verwaisten Stunden- oder Aufgabenordner.
Wird eine optionale Datei im Modell ausdrücklich auf `None` gesetzt und dieses
Modell gespeichert, wird diese Datei entfernt. Leerer Text bleibt eine leere Datei.

Die 116 mitgelieferten Sequenzen behalten ihre bisherigen Metadaten und 1645
Planungsstunden-IDs. Die bisherigen leeren Titel heißen jetzt „Noch nicht
vorbereitet“, weil `titel` im Vertrag ein nicht leerer Pflichttext ist.

Alte flache Sequenzdateien werden ausdrücklich als altes Format gemeldet.
Bestehende persönliche Daten werden nicht automatisch umgeschrieben. Zum
Ausprobieren dieser Entwicklung ist eine frisch eingerichtete Datenablage nötig;
die bisherigen Kopierregeln bleiben erhalten; leere Materialordner werden ergänzt.
