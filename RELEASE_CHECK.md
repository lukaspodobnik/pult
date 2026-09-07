# Veröffentlichungsprüfung

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
Die Logo-Herkunft bleibt dokumentiert; diese technische Prüfung behauptet keine
tatsächlich erhaltene Zustimmung und ersetzt keine rechtliche Freigabe.
