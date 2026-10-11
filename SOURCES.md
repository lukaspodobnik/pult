# Quellen und Fremdbestandteile

Bestandsabgleich für 1.3.0: 11. Oktober 2026. Die bisherigen Herkunftsangaben
bleiben erhalten; eine erneute rechtliche Gesamtprüfung ist damit nicht verbunden.
Die Lizenz des eigenen Programmcodes steht in [COPYRIGHT](COPYRIGHT) und
[LICENSE](LICENSE). Fremde Rechte werden dadurch nicht neu lizenziert.

## Lehrplanvorlagen

`src/pult/defaults/sequences/` enthält 116 Vorlagen mit 1.645 leeren
Unterrichtsstunden. Übernommen wurden Abschnitts- und Kapitelbezeichnungen,
Lehrplankennungen und gegebenenfalls empfohlene Stundenanzahlen. Die Vorlagen
enthalten Stunden-IDs; kurze Musterdateien werden erst in der Datenablage erzeugt.
`src/pult/defaults/curriculum/` enthält die Fachlehrplantexte als Markdown.
Original-PDFs, fremde Abbildungen und ergänzende Unterrichtsmaterialien werden
nicht mitgeliefert.

Quelle: **Staatsinstitut für Schulqualität und Bildungsforschung (ISB),
LehrplanPLUS Bayern, Gymnasium**. Grundlage waren die für das Projekt bereitgestellten
PDF-Exporte der offiziellen Fachlehrpläne, keine Schulbücher oder Verlagsmaterialien.

| Vorlagen | Jahrgangsstufen |
| --- | --- |
| Mathematik | 5–13 |
| Mathematik, Vertiefungskurs | 12 |
| Natur und Technik, nur Informatikanteil | 6–7 |
| Informatik NTG | 9–11 |
| Informatik, spät beginnend | 11–12 |
| Informatik, grundlegendes Anforderungsniveau | 12–13 |
| Informatik, erhöhtes Anforderungsniveau | 12–13 |

- [Offizieller Zugang zum LehrplanPLUS Gymnasium](https://www.isb.bayern.de/schularten/gymnasium/lehrplan/)
- [LehrplanPLUS](https://www.lehrplanplus.bayern.de/)
- [Nutzungsbedingungen des ISB](https://www.lehrplanplus.bayern.de/seite/impressum)

Das ISB erklärt ausdrücklich: „Die Texte der Lehrpläne unterliegen nicht dem
Urheberrechtsschutz.“ Die Originaltexte sind auch von der dortigen Beschränkung
kommerzieller Nutzung ausgenommen. Das gilt nicht pauschal für Servicematerialien,
Bilder und andere Inhalte der Website.

PULT überführt die Lehrplanstruktur in eigene technische Vorlagen; es ist kein
offizielles Angebot des ISB. Eine Empfehlung oder Unterstützung durch das ISB
wird nicht behauptet. Die unveränderliche Zuordnung jedes ursprünglichen PDF-Exports
zu einem archivierten Download ist im Repository nicht dokumentiert.

## Ferien und Feiertage

`src/pult/defaults/calendars/` enthält fünf Kalender für 2025/26 bis 2029/30.
Gespeichert sind Namen, Daten, Kategorien und der erste bzw. letzte Schultag.
Die Dateien sind eigene TOML-Zusammenstellungen, keine Kopien der Kalenderdateien
oder des Layouts der Anbieter.

Bisher dokumentierte Quellen:

- [Bayerisches Kultusministerium: Ferien und Feiertage](https://www.km.bayern.de/termine/ferien-und-feiertage)
- [Bayerisches Innenministerium: Feiertage](https://www.stmi.bayern.de/staat-und-verfassung/feiertage/)

Amtliche Grundlagen zur Nachprüfung:

- [Ferienordnung 2024/2025 bis 2029/2030, BayMBl. 2022 Nr. 747](https://www.verkuendung-bayern.de/baymbl/2022-747/)
- [Bayerisches Feiertagsgesetz, Art. 1](https://www.gesetze-bayern.de/Content/Document/BayFTG-1)
- [§ 5 UrhG: Amtliche Werke](https://www.gesetze-im-internet.de/urhg/__5.html)

Einzelne Datumsangaben sind Tatsachen; die amtlichen Rechts- und Bekanntmachungstexte
sind nach § 5 Abs. 1 UrhG nicht urheberrechtlich geschützt. Daraus folgt keine
pauschale Freigabe fremder Kalendergestaltungen oder beliebiger Datenbanken.
Die GPL beansprucht keine ausschließlichen Rechte an den Terminen.

PULT verwendet die alltagsübliche Bezeichnung „Herbstferien“, speichert keine
Sommerferien als Ausfälle und lässt Feiertage innerhalb von Ferien oder an
Wochenenden weg. Es handelt sich daher nicht um eine vollständige amtliche
Kalenderwiedergabe. Die Rechteprüfung ersetzt keine erneute Prüfung der Termine.

## Weitere Standarddaten

`subjects.toml` enthält die für PULT eingerichteten Fachnamen, Kürzel und
Jahrgangsstufen. `periods.toml` enthält die im Projekt festgelegten Stundenzeiten.
Es werden keine fremden Unterrichtsaufgaben oder ausgefüllten Sequenzpläne mitgeliefert.

## Python-Bibliotheken

Geprüft wurden die Metadaten und Lizenzdateien der installierten Laufzeitpakete
des aktuellen Entwicklungsstands:

| Paket | Version | Lizenz |
| --- | --- | --- |
| textual | 8.2.8 | MIT |
| textual-image | 0.12.0 | LGPL-3.0-or-later |
| Pillow | 12.3.0 | MIT-CMU |
| tomli-w | 1.2.0 | MIT |
| rich | 15.0.0 | MIT |
| markdown-it-py | 4.2.0 | MIT |
| mdit-py-plugins | 0.6.1 | MIT |
| linkify-it-py | 2.2.0 | MIT |
| mdurl | 0.1.2 | MIT |
| platformdirs | 4.11.5 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| typing_extensions | 4.16.0 | PSF-2.0 |
| playwright | 1.63.0 | Apache-2.0 |
| pyee | 13.0.1 | MIT |
| greenlet | 3.5.6 | MIT AND PSF-2.0 |

Diese Lizenzen sind mit GPLv3 vereinbar
([GNU-Lizenzübersicht](https://www.gnu.org/licenses/license-list.html)).
Die Bibliotheken behalten ihre eigenen Lizenzen und Urheberhinweise. Sie werden
als Abhängigkeiten installiert, nicht als PULT-eigener Code ausgegeben.
Bei einer gebündelten Weitergabe müssen ihre vollständigen Lizenz- und gegebenenfalls
weiteren Hinweistexte erhalten bleiben; diese Tabelle ersetzt sie nicht.
Für eine AUR-Veröffentlichung sind die tatsächlich paketierten Versionen erneut
zu prüfen. Entwicklungswerkzeuge wie pytest, Ruff und Pyright sind keine
Laufzeitbestandteile von PULT.

## Logo

Der PULT-Schriftzug in `src/pult/widgets/app_logo.py` und der README wurde mit
[TAAG von patorjk](https://patorjk.com/software/taag/) erzeugt, Kategorie
TheDraw Fonts, Schrift **Calvin** von **Stevonnie Ross**.

- [Originalquelle des Autors](https://www.syaross.org/thedraw/)
- [Originalarchiv TDCALVIN.ZIP, mit FONTS.TXT](https://www.syaross.org/thedraw/tdcalvin.zip)

Die ältere Archivdokumentation verwendet einen früheren Namen; auf ausdrücklichen
Wunsch erfolgt die Namensnennung hier als Stevonnie Ross.

### Erhaltene Nutzungserlaubnis

Stevonnie Ross hat per E-Mail die Nutzung für das Logo, in der App und ihren
Dateien sowie in Screenshots erlaubt, ausdrücklich einschließlich abgeleiteter
Werke unter der GPL. Die Namensnennung ist freiwillig.

Originalauszug aus der von der Projektpflege bereitgestellten Antwort
(Zeilenumbrüche normalisiert):

> You're welcome to use my font for the logo of your app, using it in that app
> and its files as you see fit, and to include it in screenshots of the app.
> I acknowledge that you're releasing the app under the GPL and this blanket
> permission also applies to derivative works made under that license.
> I don't require any credit.

Dies ist keine allgemeine Neulizenzierung der Schriftdateien. Die ergänzende
Bemerkung in der Antwort nimmt deren Verkauf ausdrücklich aus.
PULT liefert nur den erzeugten Schriftzug mit, nicht die Schriftdateien oder
den Generator. Die Herkunftsangabe beansprucht keine Urheberschaft an der Schrift.

## Dokumentrenderer

MathJax 3.2.2 wird als lokales Browser-Bundle `tex-svg-full.js` unter
`src/pult/assets/mathjax/` mitgeliefert, unter Apache-2.0.
Quelle: https://github.com/mathjax/MathJax/tree/3.2.2 und
https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg-full.js.
Der Lizenztext liegt neben dem Bundle sowie unter
`src/pult/legal/MathJax-Apache-2.0.txt`; der Herkunftshinweis unter
`src/pult/legal/MathJax-NOTICE.txt` bleibt erhalten.

Playwright ist eine externe Python-Abhängigkeit unter Apache-2.0. Seine interne
Node-Laufzeit gehört zur Playwright-Distribution. Chromium wird gesondert durch
Playwright installiert und nicht mit dem PULT-Wheel gebündelt.

## Dokumentschriften und Syntaxhervorhebung

Source Sans 3 und JetBrains Mono (normal und kursiv als variable
TrueType-Schriften) werden unter `src/pult/assets/fonts/` mitgeliefert.

- Source Sans 3: https://github.com/adobe-fonts/source-sans/tree/release/VF.
  Lizenz: SIL Open Font License 1.1; unveränderter Lizenztext mit
  Urheberrechtsangabe: `src/pult/assets/fonts/SourceSans3-OFL.txt`.
- JetBrains Mono 2.304:
  https://github.com/JetBrains/JetBrainsMono/tree/v2.304/fonts/variable.
  Lizenz: SIL Open Font License 1.1; unveränderter Lizenztext mit
  Urheberrechtsangabe: `src/pult/assets/fonts/JetBrainsMono-OFL.txt`.

Avenir Next wird ausschließlich aus lokal installierten Systemschriften geladen;
PULT liefert keine Avenir-Schriftdateien mit.

Die Syntaxhervorhebung verwendet die externe Python-Abhängigkeit Pygments
(BSD-2-Clause): https://pygments.org/.
