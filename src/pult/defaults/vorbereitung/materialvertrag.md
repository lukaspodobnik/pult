# Unterrichtsmaterialien in PULT

Jede Sequenz liegt unter `sequences/<Jahrgang>/<Fach>/<Sequenz-ID>/`.
`sequenz.toml` beschreibt die Sequenz und ihre geordneten Stunden-IDs. Klassen und
Schuljahre verweisen auf diese IDs; Unterrichtsinhalte gehören zur Sequenzbibliothek.
IDs bestehen aus Kleinbuchstaben, Zahlen und einzelnen Bindestrichen.

## Dateien einer Stunde

Unter `stunden/<Stunden-ID>/` liegen fünf Dateien:

- `stunde.toml`: `titel`, `aufgaben` (geordnete Aufgaben-IDs) und optional `hinweise`.
- `vorbereitung.md`: freies Markdown für Hefteinträge, Übungen und Notizen.
- `ziele.md`: eine flache ungeordnete Liste; Inline-Markdown ist erlaubt.
- `verlauf.md`: Phasen als `# Überschrift`, darunter beliebiger Markdown-Inhalt.
- `material.md`: eine flache ungeordnete Liste aus Dingen und benannten Links.

Die Vorbereitung beginnt als Konvention mit `# Stundentitel`. Das wird nicht
validiert. Markdown-Tabellen, Code, lokale Abbildungen und TeX sind erlaubt.
Materiallinks gehören in `material.md`, nicht in die Vorbereitung.

```toml
titel = "Brüche vergleichen"
aufgaben = ["vergleichen", "vertiefen"]
hinweise = "Übungstheke · Computerraum"
```

```markdown
- Die Schüler können gleichwertige Brüche erkennen.
- Die Schüler können ihre Ergebnisse begründen.
```

Der Verlauf beginnt mit einer nicht leeren `#`-Überschrift. Weitere Überschriften
müssen ebenfalls `#` verwenden; `##`, `###` und Setext-Überschriften sind nicht
erlaubt. Überschriften innerhalb von Codeblöcken zählen nicht als Phasen.
Eine Phase darf zunächst leer bleiben. Eine vollständig leere Planungsdatei ist
auch gültig. PULT zeigt Ziele und Verlauf zusammen, den Verlauf als Tabelle
mit den Spalten Phase und Inhalt.

```markdown
# Einstieg

- Brüche mit Papierstreifen vergleichen.

# Übung

Die Aufgabe aus der Bibliothek gemeinsam besprechen.
```

Materialeinträge dürfen höchstens einen Link enthalten. Dateilinks beziehen sich
auf die Materialdatei und müssen innerhalb des Sequenzordners bleiben.
Externe Links verwenden `https://` oder `http://`. Lokale Dateien öffnen sich mit
der dafür eingerichteten Anwendung, Webseiten mit dem Standardbrowser.

```markdown
- Schere
- Kleber
- [Präsentation](../../dateien/brueche.key)
- [Übungsseite](https://example.org/uebung)
```

## Aufgaben

Aufgaben liegen unter `aufgaben/<Aufgaben-ID>/aufgabe.md`; `loesung.md` ist optional.
Beide Dateien sind freies Markdown. Ein `# Titel` im Aufgabentext liefert den
Anzeigenamen. Eine Aufgabe darf in mehreren Stunden verwendet werden.

In der Sequenzbibliothek und der Unterrichtsansicht öffnet **a** die Aufgaben.
Von einer Stunde aus wird ihre erste vorgemerkte Aufgabe ausgewählt. **v** merkt
die ausgewählte Aufgabe für diese Stunde vor oder entfernt die Zuordnung.
Die Reihenfolge entspricht der Reihenfolge des Vormerkens. Die reine Auswahl
ändert keine Zuordnung. **s** wechselt zwischen Aufgabe und Lösung.

## Darstellung und Bedienung

Die Unterrichtsansicht zeigt links die einzeiligen, bei Bedarf abgeschnittenen
Stundentitel und darunter immer das Material. Rechts steht das Dokument; der
Rahmentitel ist der Sequenzname. **Leertaste** wechselt zwischen Vorbereitung
und Planung. **e** bearbeitet den sichtbaren Inhalt, bei Planung nach Dateiauswahl.
**r** bearbeitet Material, **m** Titel und Hinweise. **Tab** wechselt den Fokus;
Pfeile und Bildtasten scrollen den fokussierten Bereich. Die Rückkehr aus den
Aufgaben erhält Modus und Leseposition der Stunde.

Der gemeinsame Dokumentbetrachter wird auch für Aufgaben, Lösungen und Lehrpläne
verwendet. Der Lehrplanbaum enthält nur Fach und Jahrgang. Eine Sprungfunktion
innerhalb der Dokumente gibt es nicht.

Markdown, TeX und Bilder werden offline in einem unsichtbaren Chromium-Prozess
zusammen gesetzt. Das Dokument wird in voller Breite und lesbarer Größe als
scrollbare Bildabschnitte angezeigt. Ghostty verwendet das Kitty-Grafikprotokoll,
Foot Sixel. In anderen Terminals ohne passende Grafikunterstützung sowie bei
fehlendem Renderer verwendet PULT eine Textansicht. Formeln bleiben dort als
TeX-Quelltext lesbar. Links im Dokumentbild sind nicht anklickbar; dafür gibt es
den separaten Materialbereich.

## Neue Stunden und Muster

Die mitgelieferten Sequenzen enthalten nur die Stunden-IDs. Bei der Einrichtung
entstehen die fünf Dateien durch eine gemeinsame Routine; vorhandene Dateien
werden nicht überschrieben. Neue Stunden-IDs in einer bearbeiteten Sequenz werden
nach der Validierung mit derselben Routine ergänzt.

Die Muster sind bewusst kurz:

- TOML: Titel „Noch nicht vorbereitet“, leere Aufgabenliste, keine Kommentare.
- Vorbereitung: `# Noch nicht vorbereitet`.
- Ziele: zweimal `- Die Schüler können`.
- Verlauf: `# Einstieg`.
- Material: leer.

Nach dem Editor lädt PULT die Dateien neu und validiert sie. Bei Fehlern bleibt
die letzte gültige Ansicht geöffnet. PULT repariert persönliche Dateien nicht
automatisch. Eine Übernahme alter TOML-Ziele oder -Phasen ist nicht vorgesehen.
