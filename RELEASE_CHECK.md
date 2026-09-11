# Veröffentlichungsprüfung

## Release 1.1.0 — Vorbereitung

Stand: 11. September 2026. Feature-Branch `feature/unterrichtsmaterialien`.

### Erledigt

- Vollständiger Lauf von `just check` erfolgreich: Ruff, Formatprüfung und Pyright
  ohne Fehler; **217 Tests bestanden, 2 übersprungen** (219 gesammelt).
- Der zuvor abbrechende Prüflauf scheiterte an der Formatierung von neun Dateien.
  Keine Testanforderungen wurden für den erfolgreichen Lauf abgeschwächt.
- Version in `pyproject.toml` und `uv.lock` auf `1.1.0` gesetzt.
- README, Release Notes und Materialvertrag auf die aktuelle Bedienung gebracht.
- Keine Migration erforderlich für den vorgesehenen Einsatz ohne bestehende Daten.
  Eine Migration alter Sequenzformate ist nicht implementiert.

### Noch vor der Veröffentlichung

- Die zwei übersprungenen Grafiktests mit Node.js und `rsvg-convert` ausführen;
  Formeln, Bilder und Editoraufrufe im vorgesehenen Terminal manuell prüfen.
- Änderungen prüfen, committen und den Feature-Branch zusammenführen. Den finalen
  Stand mit `just check` prüfen.
- Mit `uv build` Wheel und Quellarchiv aus dem finalen Stand bauen:
  `dist/pult-1.1.0-py3-none-any.whl` und `dist/pult-1.1.0.tar.gz`.
- Archivinhalt, Version, Lizenzdateien, Materialvorlagen und mitgelieferten
  MathJax-Renderer prüfen; keine persönlichen Unterrichtsdaten aufnehmen.
- Wheel separat unter Python 3.11 installieren und `scripts/smoke_installed.py`
  mit dem Python dieser Installation ausführen (nicht über `uv run`).
- Tag `v1.1.0` und GitHub-Release mit Release Notes sowie beiden Archiven erstellen.
- Falls AUR veröffentlicht wird: Version, neue Laufzeitabhängigkeiten und
  Grafikvoraussetzungen in `PKGBUILD` berücksichtigen, Prüfsumme des finalen
  Quellarchivs übernehmen und `.SRCINFO` neu erzeugen. Arch-Bau und Installation
  separat prüfen. Die vorhandenen AUR-Dateien gehören weiterhin zu 1.0.1.

Für 1.1.0 sind Paketbau, Installationstest, Tag und Upload in dieser Prüfung noch
nicht erfolgt. Die folgenden Abschnitte dokumentieren frühere Releases und sind
kein Prüfnachweis für 1.1.0.


## Historischer Stand: Release 1.0.1 — Vorbereitung

- Version in `pyproject.toml` und `uv.lock`: `1.0.1`.
- README-Installationslink und `RELEASE_NOTES.md` für das neue Release vorbereitet.
- Ruff, Formatprüfung und Pyright erfolgreich; alle 177 Tests bestanden.
- Wheel und Quellarchiv aus dem Release-Stand gebaut.
- Paketversion, GPL-Metadaten und mitgelieferte Dateien `LICENSE`, `COPYRIGHT`
  und `SOURCES.md` geprüft; 116 Sequenzvorlagen im Wheel enthalten.
- Keine Prototypen, Node-Abhängigkeiten, virtuelle Umgebung oder Git-Verzeichnisse
  in den gebauten Archiven.
- Wheel in separater Python-3.11-Umgebung unter `/tmp` installiert.
- Installierter Einstiegspunkt, Ersteinrichtung, Neustart aus anderem Verzeichnis,
  Defaults und Lizenzdialog mit temporären Nutzerdaten erfolgreich geprüft.
- AUR auf `1.0.1-1` aktualisiert, SHA-256 aus dem neuen Quellarchiv übernommen,
  `.SRCINFO` neu erzeugt und PKGBUILD-Syntax geprüft.
- Vollständiger neuer Arch-Chroot-Bau und pacman-Installation noch ausstehend;
  die Python-Installationsprüfung ersetzt diese nicht.

Artefakte für die spätere Veröffentlichung:

- `dist/pult-1.0.1-py3-none-any.whl`
- `dist/pult-1.0.1.tar.gz`

Noch kein Release-Commit, Tag oder Upload erstellt. Nach dem Merge den finalen
Stand und die Archivprüfsumme erneut abgleichen. Die AUR-Downloadadresse ist erst
nach Veröffentlichung des Quellarchivs erreichbar. Gebaute Archive werden nicht
in Git eingecheckt, sondern später als Release-Anhänge hochgeladen.

## Historische Prüfung für 0.1.0

Stand: 7. September 2026, Paketversion `0.1.0`.

## Geprüft

- Ruff und Formatprüfung erfolgreich, Pyright ohne Fehler; alle 177 Tests bestanden.
- Wheel und Quellpaket erfolgreich gebaut; Metadaten stimmen mit dem Projekt überein.
- GPL-3.0-or-later, Lizenztext und Quellenhinweise sind im Paket enthalten.
- Alle 116 Sequenzvorlagen und fünf Kalender sind enthalten.
- Keine Git-Verzeichnisse, virtuelle Umgebung oder Unterrichtsdaten im Paket.
- Wheel separat installiert, ohne die Entwicklungsumgebung zu verwenden.
- Installierter Einstiegspunkt: Ersteinrichtung, Lizenzdialog und Neustart aus
  einem anderen Verzeichnis mit temporärer Konfiguration erfolgreich geprüft.
- Relative Datenverzeichnisse werden beim Setup absolut gespeichert;
  Regressionstest ergänzt.
- Jahreswechseltest wartet auf den Startfokus des Modals, bevor er Eingaben sendet.
- 145 lokal erreichbare Commits / 833 unterschiedliche Dateiobjekte geprüft:
  keine Treffer für untersuchte Zugangsschlüssel-Muster, keine eingecheckten
  Unterrichtsdaten oder persönlichen absoluten Dateipfade gefunden.

Die Historienprüfung ist keine Garantie, alle Arten vertraulicher Inhalte zu
erkennen. Name und E-Mail-Adresse des Autors sind in Historie und Metadaten sichtbar.

## Wiederholen

`just check` prüft Code und Tests. `uv build` erstellt die Veröffentlichungspakete.
Für den Installationstest das Wheel in eine separate Tool-Umgebung installieren
und `scripts/smoke_installed.py` mit deren Python starten; optional den installierten
`pult`-Einstiegspunkt als Argument übergeben. Nicht `uv run` verwenden: Der Test
soll ausdrücklich die Installation statt des Projektcodes prüfen.

## Veröffentlichung

Noch nichts hochgeladen, keine Repository-Sichtbarkeit geändert, kein Tag erstellt
und keine Git-Historie umgeschrieben. Nach Commit des geprüften Stands folgen die
öffentliche Freigabe des Repositorys, ein Release-Tag und die AUR-Paketierung.
Nachtrag: Die Logo-Erlaubnis liegt inzwischen per E-Mail von Stevonnie Ross vor,
einschließlich abgeleiteter Werke unter der GPL. Sie ist in SOURCES.md dokumentiert.
Der obige Veröffentlichungsstatus beschreibt den damaligen Prüfzeitpunkt.
