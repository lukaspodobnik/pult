# Materialvertrag

Dieser Vertrag beschreibt das Dateiformat für PULT. Didaktische Vorgaben und der
Ablauf einer KI-gestützten Vorbereitung werden gesondert festgelegt.

## Sequenz

Eine Sequenz liegt unter `sequences/<Jahrgang>/<Fach-ID>/<Sequenz-ID>/`.
`sequenz.toml` enthält `id`, `curriculum_section_id`, `subject_id`, `grade_level`,
`titel` und die geordnete Liste `stunden` mit Stunden-IDs. Optional sind
`recommended_lesson_count` sowie gemeinsam `chapter_id` und `chapter_title`.
Die Angaben müssen zum Ablageort passen; weitere Felder sind nicht erlaubt.

Stunden-, Aufgaben-, Fach- und Sequenz-IDs bestehen aus Kleinbuchstaben, Zahlen
und einzelnen Bindestrichen, etwa `brueche-vergleichen`. Referenzlisten enthalten
keine Duplikate. Bestehende IDs erhalten: Klassenfortschritt und Zuordnungen
verweisen darauf. Materialien bleiben unabhängig von konkreten Klassen und Terminen.

## Stunde

Unter `stunden/<Stunden-ID>/` liegen fünf Dateien:

| Datei | Inhalt und Validierung |
| --- | --- |
| `stunde.toml` | Nicht leerer `titel`, optionale Liste `aufgaben` und optionaler Text `hinweise`; keine weiteren Felder. |
| `vorbereitung.md` | Freies Markdown; als Konvention beginnt es mit `# Stundentitel`. |
| `ziele.md` | Flache ungeordnete Liste; pro Eintrag genau ein Absatz, Inline-Markdown erlaubt. |
| `verlauf.md` | Beginnt mit einer nicht leeren `#`-Phasenüberschrift; darunter freies Markdown. Weitere Überschriften ausschließlich als `#`, keine Unterüberschriften oder Setext-Überschriften. |
| `material.md` | Flache ungeordnete Liste aus Dingen und benannten Links; pro Eintrag ein Absatz und höchstens ein Link. |

Leere Markdown-Dateien sind gültig. Fehlende Markdown-Dateien werden als leer
behandelt. Leere Phasen sind erlaubt; Überschriften in Codeblöcken zählen nicht
als Phasen. Ziele und Verlauf erscheinen gemeinsam in der Planung, der Verlauf
als Tabelle. Materiallinks stehen ausschließlich in `material.md`.

```toml
titel = "Brüche vergleichen"
aufgaben = ["vergleichen"]
hinweise = "Übungstheke · Computerraum"
```

`aufgaben` verweist auf vorhandene Aufgaben dieser Sequenz; ihre Reihenfolge ist
die Reihenfolge des Vormerkens. PULT kann die Zuordnung verwalten. `hinweise`
enthält kurze organisatorische Angaben für den Stoffverteilungsplan.

```markdown
- Schere
- [Präsentation](../../dateien/brueche.key)
- [Übungsseite](https://example.org/uebung)
```

Dateilinks beziehen sich auf `material.md` und bleiben innerhalb der Sequenz.
Weblinks verwenden `https://` oder `http://`. Dateien öffnen sich in der
zugeordneten Anwendung, Webseiten im Standardbrowser.

## Aufgaben und Markdown

Aufgaben liegen unter `aufgaben/<Aufgaben-ID>/aufgabe.md`; `loesung.md` ist optional.
Beides ist freies Markdown. Eine `#`-Überschrift liefert den Anzeigenamen.
Aufgaben können mehreren Stunden derselben Sequenz zugeordnet sein.

Markdown unterstützt Tabellen, Codeblöcke mit Sprachangabe, TeX als `$…$` bzw.
`$$…$$` und lokale Bilder (SVG, PNG, JPEG, WebP). Bildpfade sind relativ zur
Markdown-Datei und bleiben innerhalb des Sequenzordners; gemeinsame Dateien
können in `dateien/` liegen. HTML wird nicht ausgeführt, entfernte Bilder werden
nicht geladen. Links innerhalb gerenderter Dokumentbilder sind nicht anklickbar.

## Muster und Änderungen

Beim Einrichten und beim Ergänzen von Stunden im Sequenzeditor legt PULT fehlende
Dateien an. Vorhandene Inhalte bleiben erhalten. Die Muster enthalten nur:

- `stunde.toml`: `titel = "Noch nicht vorbereitet"` und `aufgaben = []`.
- `vorbereitung.md`: `# Noch nicht vorbereitet`.
- `ziele.md`: zweimal `- Die Schüler können`.
- `verlauf.md`: `# Einstieg`.
- `material.md`: leer.

Nach dem Bearbeiten validiert PULT die Dateien. Bei Fehlern bleibt die letzte
gültige Ansicht sichtbar; die Datei wird nicht automatisch korrigiert.
Das frühere Format mit Zielen und Verlauf in TOML wird nicht übernommen.
