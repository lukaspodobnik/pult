# Unterrichtsansicht · Prototyp

Der vereinbarte [Materialvertrag](../../docs/materialvertrag.md) beschreibt das
Zielmodell für die Integration. Die Beispieldaten dieses Darstellungsprototyps
verwenden noch ihr bisheriges, davon abweichendes Format.

Separater Darstellungsversuch im Vollbild. Der Pult-Anwendungscode und das
persönliche Datenverzeichnis werden nicht verändert.

## Start in Foot

Im Projektordner:

```bash
prototypes/unterricht/.venv/bin/python prototypes/unterricht/app.py --graphics sixel
```

Die Abhängigkeiten sind auf diesem Rechner eingerichtet. Für eine neue Einrichtung
werden Python 3.11+, Node.js und `rsvg-convert` benötigt:

```bash
uv venv prototypes/unterricht/.venv
uv pip install --python prototypes/unterricht/.venv/bin/python -r prototypes/unterricht/requirements.txt
npm ci --prefix prototypes/unterricht
```

Die Grafik wird lokal erzeugt und zwischengespeichert; zur Laufzeit sind weder
Browser noch Internet nötig. `--graphics off` zeigt zur Fehlersuche Formelquellen
und Bildbeschreibungen, keine gleichwertige Unterrichtsdarstellung.

## Aufbau und Bedienung

Links steht die Stundenliste der aktuellen Sequenz mit Fach und Jahrgang. In der Mitte steht die Vorbereitung oder die Aufgabenliste. Jede Lösung folgt unmittelbar
auf ihre Aufgabe. Rechts stehen Ziele und Verlauf in getrennten Rahmen. Der Stundentitel steht im Materialrahmen; dessen unterer Rand benennt die aktive Ansicht.
Alle Beispiele verwenden denselben Aufbau: Brüche (zwei Stunden), Integralrechnung, Python.

| Taste | Funktion |
|---|---|
| Leertaste | Vorbereitung / Aufgaben umschalten |
| Tab | Fokus zwischen Material, Zielen, Verlauf und Stundenliste wechseln |
| ↑ / ↓, Enter in der Stundenliste | Stunde auswählen und öffnen |
| Pfeile, Bild auf/ab, Mausrad | Fokussierten Bereich scrollen |
| j / k | Drei Zeilen abwärts / aufwärts |
| b | Nächste Beispielstunde, auch über Sequenzgrenzen (Prototyp) |
| q | Beenden |

Jede Materialansicht behält beim Umschalten ihre Scrollposition. Es gibt keine
besonderen Layouts für kleine Fenster, keine Maximierung und keine Hintergrundmodals.

## Materialien und Darstellung

`lessons.toml` enthält Beispieldaten, Ziele, Phasen und Aufgabenverweise.
Vorbereitung, Aufgabentext und Lösung sind eigene Markdown-Dateien. Die Aufgaben
liegen paarweise in `materials/taskN/task.md` und `solution.md`.
Die Beispieldaten sind noch kein endgültiger Materialvertrag und keine fertige Sequenz.

- CommonMark wird mit markdown-it-py gelesen. Standardblöcke werden von Textual
  Markdown dargestellt, einschließlich Listen, Hervorhebungen und Codeblöcken.
- `$...$` setzt Mathematik zwischen Terminaltext. Text und Teilaufgabenbezeichnungen
  bleiben in der Terminalschrift. Kurze Formeln werden beim Zeilenumbruch zusammengehalten.
- `$$...$$` setzt eine abgesetzte Formel. MathJax unterstützt beispielsweise
  `aligned`, Brüche, Integrale und Matrizen. Es ist kein vollständiger LaTeX-Dokumentcompiler.
- MathJax verwendet seine auf Computer Modern beruhende TeX-Schrift. Mathematische
  Beschriftungen der Beispielgrafiken verwenden Matplotlibs Computer Modern.
- Python-/Java-Code in entsprechend bezeichneten Markdown-Codeblöcken erhält
  Syntaxhervorhebung. Der Code wird nicht ausgeführt.
- Abbildungen sind bisher die beiden benannten Beispiele `bruchteile` und `parabel`.
  Verweise auf iPad-Material sind einfache Notizen, keine Gerätesteuerung.

Mathematik in verschachtelten Listen oder Tabellen und beliebige externe Bilder
sind noch nicht ausgearbeitet. Der Prototyp prüft zunächst normale Absätze,
Formelblöcke, Abbildungen und Code. Lange Formeln müssen sinnvoll mehrzeilig
geschrieben werden. Eine Editor-Anbindung, Export und die Integration in Pult
folgen erst nach der Layoutentscheidung.

`sixel.py` bewahrt die Foot-Korrektur: vollständige Palette vor den Bilddaten,
transparenter Sixel-Hintergrund und eine feste Formelpalette ohne Dithering.

## Prüfung

```bash
uv pip install --python prototypes/unterricht/.venv/bin/python pytest
prototypes/unterricht/.venv/bin/python -m pytest prototypes/unterricht/test_prototype.py -q
```

Geprüft werden Parsergrenzen gegenüber Code, mehrzeilige Formeln, Asset-Erzeugung,
Sixel-Palette, Widgetaufbau, Aufgaben-/Lösungsreihenfolge und Navigation.
Headless-Screenshots zeigen den Aufbau, aber keine Sixel-Bilder. Die tatsächliche
Schriftgröße und Bilddarstellung müssen zusätzlich in Foot beurteilt werden.
