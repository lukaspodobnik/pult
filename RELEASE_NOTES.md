# PULT 1.4.0

- Aufgaben- und Lösungshefte als PDF: für eine Stunde oder eine ganze Sequenz,
  mit Antwortbereichen und Quellenangaben.
- Kurze Reste nach einer Fortsetzung abschließen, ohne einen weiteren Termin
  zu verbuchen. Der SVP erhält eine Anmerkung beim selben Termin.
- Überarbeiteter Stoffverteilungsplan mit klareren Ferienabschnitten,
  Scrollposition je Klasse und Fach sowie gesammelt exportierbaren Plänen.
- LNW-Übersicht nach Klassen gruppiert; „Zuletzt“ zeigt mehrere Buchungen.
- GeoGebra-Dateien aus PULT unter macOS öffnen.
- Verbesserte Dokumentdarstellung und behobene Anzeigefehler beim Start
  und beim Wechsel zwischen Stunden und Aufgaben.
- Lokale Diagnoseprotokolle; ausführlicher Modus mit `pult --debug`.

## Installation und Update

```sh
uv tool install --force --python 3.11 https://github.com/lukaspodobnik/pult/releases/download/v1.4.0/pult-1.4.0-py3-none-any.whl
```

Bestehende Aufgaben benötigen eine `aufgabe.toml` mit Titel, Hauptkompetenzen und
Anforderungsbereich. Ältere Aufgaben ohne diese Metadaten werden nicht automatisch
migriert. Bereits entsprechend gepflegte Unterrichtsdaten können weiterverwendet
werden. Falls PULT die Dokumenteinrichtung anbietet, den Chromium-Download ausführen.

[Alle Änderungen und Materialformat](https://github.com/lukaspodobnik/pult/blob/v1.4.0/CHANGELOG.md)
