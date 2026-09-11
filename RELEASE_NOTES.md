# PULT 1.1.0

Unterrichtsmaterialien vorbereiten, Aufgaben verwalten und die nächste Stunde
direkt aus dem Dashboard öffnen.

## Neu

- Unterrichtsviewer mit Vorbereitung, Aufgaben und Lösungen, Lernzielen und
  gegliedertem Stundenverlauf. Die Anzeige folgt der markierten Stunde;
  Leertaste wechselt zwischen Vorbereitung und Aufgaben.
- Aufgabenviewer für alle Aufgaben einer Sequenz, auch ohne Zuordnung zu einer
  Stunde. **n** erstellt Aufgabentext und Lösungsdatei und öffnet beide im Editor.
  Eine Aufgabe hat einen Listeneintrag; die Lösung steht direkt unter dem Text.
- Stunden, Aufgaben und Lösungen liegen in eigenen Ordnern nach dem
  Materialvertrag. Markdown unterstützt unter anderem Formeln, Bilder und Code.
- Sequenzbibliothek mit vollständiger Stundenvorschau; **Enter** öffnet die
  markierte Stunde, **a** die Aufgaben der Sequenz. Die Vorschau hebt Stunden nur
  hervor, solange ihr Inhaltsbereich den Fokus hat.
- **o** öffnet die angezeigte nächste Stunde aus Übersicht und Klassenansicht.
- Überarbeitete nächste Stunde: kompakter Aufbau ohne Materialanzeige auf der
  Homeview; Aufgaben, Ziele, Material und Verlauf in der Klassenansicht.
- Einheitliche Sequenzköpfe und Footerpositionen in beiden Viewern.
- Neue Datenablagen enthalten elf Stundenzeiten. Die Übersicht berücksichtigt
  auch spätere belegte Stunden und hält den Stundenplan scrollbar.

## Voraussetzungen und Daten

Python 3.11 oder neuer. Für grafische Formeln und SVG-Bilder werden zusätzlich
Node.js, `rsvg-convert` und ein Terminal mit passender Bildunterstützung benötigt.
MathJax ist enthalten; npm ist zur Nutzung nicht erforderlich. Ohne Grafikrenderer
erscheinen Formelquellen beziehungsweise Bildhinweise.

Dieses Release verwendet das neue Materialformat. Eine Migration alter
Sequenzdateien ist nicht enthalten; für den vorgesehenen Einsatz gibt es keine
bestehenden Daten, die übernommen werden müssen. Persönliche Inhalte werden im
gewählten Datenverzeichnis abgelegt, nicht in den mitgelieferten Vorlagen.

## Installation

Nach Veröffentlichung:

```bash
uv tool install --force --python 3.11 https://github.com/lukaspodobnik/pult/releases/download/v1.1.0/pult-1.1.0-py3-none-any.whl
```

Der Paketierungsstand unter `packaging/aur` gehört noch zu 1.0.1 und ist für dieses
Release separat anzupassen und unter Arch zu prüfen.
