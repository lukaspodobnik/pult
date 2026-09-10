# AUR-Paketierung

Paket: `pult`, Version `1.0.1-1`. Für das kommende GitHub-Release vorbereitet; noch nicht ins AUR hochgeladen.

- `PKGBUILD`: Bauanleitung für das veröffentlichte Quellpaket.
- `.SRCINFO`: mit `makepkg --printsrcinfo > .SRCINFO` erzeugte Metadaten.
- Die optionale Editorauswahl erzwingt keine Installation eines bestimmten Editors.

## Vorbereitung für 1.0.1

`pkgver` wurde auf `1.0.1` gesetzt und `pkgrel` auf `1` zurückgesetzt.
Die SHA-256-Prüfsumme stammt aus dem lokal gebauten Release-Quellarchiv
`dist/pult-1.0.1.tar.gz`. `.SRCINFO` wurde mit `makepkg --printsrcinfo` neu erzeugt.
Bash-Syntax und Metadaten wurden geprüft. Der Download-Link funktioniert erst,
wenn genau dieses Quellarchiv beim GitHub-Release `v1.0.1` veröffentlicht ist.

Ein neuer vollständiger Arch-Chroot-Bau und eine pacman-Installation von 1.0.1
stehen noch aus. Die früheren Prüfungen unten sind historische Ergebnisse.
Nach einem erneuten Archivbau muss die Prüfsumme erneut abgeglichen werden.

## Prüfung vom 8. September 2026

- Download und SHA-256-Prüfung des Release-Quellpakets erfolgreich.
- Bash-Syntax und Übereinstimmung von `.SRCINFO` mit `PKGBUILD` geprüft.
- Arch-Paket erfolgreich mit `makepkg` und `/usr/bin/python` (3.14.7) gebaut.
- Build-Werkzeuge und Laufzeitabhängigkeiten für diesen Vorabtest ausschließlich
  nach `/tmp` installiert; deshalb `makepkg --nodeps` verwendet. Das ist kein
  Nachweis der vollständigen Arch-Abhängigkeitsauflösung.
- Paket entpackt und Einstiegspunkt headless getestet: Setup, Neustart aus einem
  anderen Verzeichnis, 116 Sequenzvorlagen und Lizenzdialog funktionieren.
- Installationspfade unter `/usr`, Startskript und mitgelieferte Lizenzdateien geprüft.
- Keine echte Konfiguration verändert und kein Paket auf dem Host installiert.

Anschließend hat der Nutzer Installation, Bedienung und Deinstallation mit pacman
sowie den sauberen Chroot-Bau von `1.0.0-1` erfolgreich durchgeführt.
Namcap meldete dabei Rich als nur indirekt erfüllte Abhängigkeit. `1.0.0-2`
deklariert deshalb `python-rich` direkt; der Chroot-Bau ist damit erneut auszuführen.
Der übersprungene checkpkg-Vergleich ist beim ersten Paket ohne vorhandene
Repository-Version erwartbar.

Auch die Python-Projektmetadaten deklarieren Rich nun direkt. Diese Änderung
gilt für den nächsten Python-Release; das veröffentlichte Quellarchiv `1.0.0`
und seine Prüfsumme bleiben unverändert. Die Arch-Abhängigkeit wird unabhängig
davon bereits durch dieses PKGBUILD korrekt angegeben.

## Sauberer Arch-Test

Mit installierten Arch-`devtools` im Verzeichnis dieser Datei:

```sh
extra-x86_64-build
```

Dabei werden die deklarierten Abhängigkeiten im Chroot installiert. Anschließend
das erzeugte Paket in einer Testumgebung mit pacman installieren und wieder
entfernen; Programmstart und Erhalt der Nutzerdaten prüfen.
Die Testsuite ist im Release-Quellpaket nicht enthalten, deshalb besitzt dieses
PKGBUILD keine `check()`-Funktion. Der separate Installationstest liegt im
Projekt unter `scripts/smoke_installed.py` und verwendet nur temporäre Nutzerdaten.

## AUR-Upload und Updates

Nach erfolgreichem vollständigem Test nur `PKGBUILD` und `.SRCINFO` in das separate
AUR-Repository übernehmen, nicht Quellarchive, gebaute Pakete oder diese Anleitung.
Der Upload erfordert einen AUR-Account mit SSH-Schlüssel.

Für eine neue PULT-Version `pkgver` und Prüfsumme aktualisieren, `pkgrel` wieder
auf `1` setzen, `.SRCINFO` neu erzeugen und erneut bauen und testen.
Bei reinen Paketierungsänderungen nur `pkgrel` erhöhen.
Veröffentlichte Release-Archive oder Tags nicht nachträglich ersetzen.
