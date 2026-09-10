# PULT 1.0.1

Wartungsupdate mit Verbesserungen der Tastaturbedienung und ergänzten Quellenhinweisen.

- Sequenzen werden mit **e** statt Enter im konfigurierten Editor geöffnet.
- **F2 Übersicht** steht im Footer ganz links, mit Abstand zu den weiteren Befehlen.
- **u Protokoll** ist bei Fokus auf Verwaltung ausgeblendet und deaktiviert.
- Die Namensnennung von Stevonnie Ross für den Logo-Schriftzug „Calvin“ und die
  ausdrückliche Nutzungserlaubnis sind in den Quellenhinweisen und im
  Über-Pult-Fenster dokumentiert.
- Rich wird als direkte Laufzeitabhängigkeit deklariert.

Bestehende Konfiguration und Unterrichtsdaten können weiterverwendet werden.
Die neue Unterrichtsansicht und Unterrichtsmaterialien sind nicht Bestandteil dieses Releases.

## Installation oder Aktualisierung

Nach Veröffentlichung:

```bash
uv tool install --force --python 3.11 https://github.com/lukaspodobnik/pult/releases/download/v1.0.1/pult-1.0.1-py3-none-any.whl
```

Die vorhandenen Nutzerdaten bleiben bei dieser Paketaktualisierung erhalten.
