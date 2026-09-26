# PULT 1.2.0

## Neu

- Schriftliche Leistungsnachweise planen: Schulaufgaben, Stegreifaufgaben,
  angekündigte kleine Leistungsnachweise und Jahrgangsstufentests.
- Termine mit Beginn, Dauer und belegten Unterrichtsstunden verwalten;
  Konflikte mit Ausfällen und Ferien erkennen.
- Leistungsnachweise mit `n` abschließen und im Unterrichtsprotokoll erfassen,
  ohne den Sequenzfortschritt weiterzuschalten. Abschlüsse lassen sich zurücknehmen.
- Erlaubte Arten und jährliche Mindestzahlen je Fach und Jahrgangsstufe unter
  Einstellungen festlegen. Neue Schuljahre übernehmen die bisherigen Vorgaben.
- Klassenübersicht mit Stundendifferenz, nächstem Leistungsnachweis und Zählern
  für große und kleine schriftliche Leistungsnachweise. Die Verwaltung zeigt,
  welche Leistungsnachweise noch zu planen sind. Jahrgangsstufentests zählen
  nicht zu den Mindestzahlen.

## Verbessert

- Dashboard mit sechs sichtbaren Stunden und scrollbaren weiteren Einträgen.
- Erweiterte Klassen- und Ausfallverwaltung mit Unterrichtsterminen.
- Einheitlichere Rahmen, kompaktere Dialoge und dezente Fokusmarkierungen.
- Sanfter Start mit großem PULT-Logo und anschließendem Einblenden des Dashboards.
- Ergänzte Lehrplanreferenzen sowie überarbeitete Dokumentation.

## Installation und Update

```sh
uv tool install --force --python 3.11 https://github.com/lukaspodobnik/pult/releases/download/v1.2.0/pult-1.2.0-py3-none-any.whl
```

Persönliche Unterrichtsdaten bleiben erhalten. Eine Sicherung des Datenverzeichnisses
vor dem Update ist empfehlenswert. Fehlende LNW-Vorgaben bestehender Schuljahre
verwenden die letzte frühere Konfiguration oder die mitgelieferten Standards;
bestehende Vorgaben werden nicht überschrieben.
