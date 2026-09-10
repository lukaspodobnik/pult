# Veröffentlichungsprüfung

## Release 1.0.1 — Vorbereitung

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
