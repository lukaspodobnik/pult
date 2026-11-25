# Änderungen

## 1.4.0

- Aufgaben- und Lösungshefte als PDF: `x` exportiert die Aufgaben der aktuellen
  Stunde, `X` die zugeordneten Aufgaben der Sequenz. Antwortbereiche, Druckspalten,
  Bildgrößen, Buchquellen und eine optionale Namenszeile sind einstellbar.
- Aufgaben erhalten Metadaten für Titel, Hauptkompetenzen und Anforderungsbereich.
  Buchaufgaben können Quellenangaben tragen und werden nach Seite und Nummer
  sortiert; eigene Aufgaben nach ihrer Titelnummer.
- Nach `c` bietet `n` einen kurzen Restabschluss an. Der Termin bleibt für die
  nächste Planstunde frei; SVP und PDF führen den Rest als Anmerkung beim selben
  Termin. Protokoll, Stundenbilanz und Rückgängig berücksichtigen den Unterschied.
- Stoffverteilungsplan mit dezenten Sequenzüberschriften, deutlicheren Ferien und
  Aktionssymbolen, auch im PDF. Scrollpositionen bleiben je Klasse und Fach beim
  Wechsel erhalten; `X` exportiert die Pläne aller Klassen und Fächer.
- LNW-Übersicht nach Klassen gruppiert. „Zuletzt“ zeigt so viele Buchungen, wie
  Platz haben; „Nächste Stunde“ nennt benötigte Materialien.
- GeoGebra-Dateien öffnen unter macOS in der Calculator Suite. Dabei wird der
  Dateiinhalt importiert; die Originaldatei wird nicht verändert.
- Dokumente unterstützen Definitionen und Merksätze, mehrspaltige Teilaufgaben,
  Abbildungen neben Text und anpassbare Textersetzungen. Leertaste wechselt
  zwischen Aufgabe und Lösung; Verlaufspläne zeigen Zeiten in einer eigenen Spalte.
- Benachbarte Stunden werden vorgeladen; der Dokumentcache ist auf 500 MB begrenzt.
- Darstellungsfehler bei Tagesmarkierung, Navigation und der Rückkehr aus der
  Aufgabenbibliothek behoben.
- Lokale Diagnoseprotokolle mit Rotation und zusätzlicher Ausgabe bei `pult --debug`.

**Update von 1.3.1:** Bestehende Aufgaben brauchen ebenfalls eine `aufgabe.toml`
mit Titel, Hauptkompetenzen und Anforderungsbereich. Diese Angaben werden nicht
automatisch ergänzt. Das [Materialformat](src/pult/defaults/vorbereitung/materialvertrag.md)
beschreibt die Felder. Neue Einstellungen besitzen Standardwerte; bestehende
Klassenprotokolle bleiben lesbar. Ein mit 1.4.0 gespeicherter Restabschluss wird
von älteren PULT-Versionen nicht unterstützt.

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
