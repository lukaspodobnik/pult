# Änderungen

## Noch nicht veröffentlicht

- Definitionen und Merksätze als Markdown-Callouts: blaue bzw. orange Akzente
  passend zum Theme, mit Beschriftung auch in der Textansicht.
- Aufgaben besitzen eine `aufgabe.toml` mit Titel, ein bis drei Hauptkompetenzen
  und einem Anforderungsbereich (höchster Bereich der Teilaufgaben). Anlage,
  Bearbeitung und Aufgabenbibliothek berücksichtigen die Metadaten.
- Bestehende Aufgaben benötigen die neue Metadatendatei ebenfalls; keine
  automatische fachliche Einordnung.

## 1.3.1

- Integrierte Einrichtung der Dokumentdarstellung beim Start und in den
  Einstellungen: Chromium-Download, Abbruch, erneute Prüfung und Linux-Hilfe.
- Schriftprüfung und offene Dokumente aktualisieren sich nach erfolgreicher
  Einrichtung ohne Neustart; die Textansicht bleibt ohne Chromium verfügbar.

## 1.3.0

- Gemeinsamer Dokumentbetrachter für Unterricht, Planung, Aufgaben und Lehrpläne:
  Markdown, TeX, Syntaxfarben und lokale Bilder; Avenir Next mit Source Sans 3
  als mitgelieferter Ersatzschrift.
- Überarbeitete Unterrichtsansicht mit eigenem Materialbereich, Aufgaben mit
  Lösungen und vereinfachter Navigation durch Sequenzen und Lehrpläne.
- Stoffverteilungsplan aus Unterrichtsprotokoll und offenen Planstunden, mit
  Ferien, Ausfällen und Leistungsnachweisen. PDF-Exporte für Stoffverteilung
  und Stundenplan in einer gemeinsamen Ablage.
- Spontanunterricht mit Pflichtbeschreibung; „Zusatzstunde“ heißt nun
  „Zusätzlicher Termin“. Der nächste LNW wird in der Übersicht hervorgehoben.
- Vereinheitlichtes sicheres Speichern, bereinigte Paketdateien sowie überarbeitete
  README und Materialvertrag.

**Materialformat:** Jede Stunde verwendet `stunde.toml`, `vorbereitung.md`,
`ziele.md`, `verlauf.md` und `material.md`. Muster werden bei Bedarf erzeugt.
Das frühere Materialformat wird nicht automatisch migriert; bestehende Ablagen
müssen bereits dem [Materialvertrag](src/pult/defaults/vorbereitung/materialvertrag.md)
entsprechen.

**Installation:** Dokumentgrafik und PDF-Export benötigen den zur installierten
Playwright-Version passenden Chromium-Browser; Einrichtung siehe [README](README.md).
