# Quellen und Fremdbestandteile

Prüfstand: 7. September 2026. Diese Übersicht dokumentiert den geprüften Bestand;
sie ist keine anwaltliche Freigabe und keine Prüfung von Markenrechten.
Die Lizenz des eigenen Programmcodes steht in [COPYRIGHT](COPYRIGHT) und
[LICENSE](LICENSE). Fremde Rechte werden dadurch nicht neu lizenziert.

## Lehrplanvorlagen

`src/pult/defaults/sequences/` enthält 116 Vorlagen mit 1.645 leeren
Unterrichtsstunden. Übernommen wurden Abschnitts- und Kapitelbezeichnungen,
Lehrplankennungen und gegebenenfalls empfohlene Stundenanzahlen. Die Felder für
Stundentitel, Aufgaben und Notizen sind leer. Vollständige PDFs, Abbildungen und
ergänzende Unterrichtsmaterialien werden nicht mitgeliefert.

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
| tomli-w | 1.2.0 | MIT |
| rich | 15.0.0 | MIT |
| markdown-it-py | 4.2.0 | MIT |
| mdit-py-plugins | 0.6.1 | MIT |
| linkify-it-py | 2.2.0 | MIT |
| mdurl | 0.1.2 | MIT |
| platformdirs | 4.11.5 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| typing_extensions | 4.16.0 | PSF-2.0 |

Diese Lizenzen sind mit GPLv3 vereinbar
([GNU-Lizenzübersicht](https://www.gnu.org/licenses/license-list.html)).
Die Bibliotheken behalten ihre eigenen Lizenzen und Urheberhinweise. Sie werden
als Abhängigkeiten installiert, nicht als PULT-eigener Code ausgegeben.
Bei einer gebündelten Weitergabe müssen ihre vollständigen Lizenz- und gegebenenfalls
weiteren Hinweistexte erhalten bleiben; diese Tabelle ersetzt sie nicht.
Für eine AUR-Veröffentlichung sind die tatsächlich paketierten Versionen erneut
zu prüfen. Entwicklungswerkzeuge wie pytest, Ruff und Pyright sind keine
Laufzeitbestandteile von PULT.

## Logo: Nutzungserlaubnis noch offen

Der PULT-Schriftzug in `src/pult/widgets/app_logo.py` und der README wurde mit
[TAAG von patorjk](https://patorjk.com/software/taag/) erzeugt, Kategorie
TheDraw Fonts, Schrift **Calvin** von **Shmuel Ross**.

- [Originalquelle des Autors](https://www.syaross.org/thedraw/)
- [Originalarchiv TDCALVIN.ZIP, mit FONTS.TXT](https://www.syaross.org/thedraw/tdcalvin.zip)

`FONTS.TXT` nennt Copyright 1994 Shmuel Ross und begrüßt die Weitergabe der
Schriftensammlung, enthält aber keine eindeutige moderne Open-Source-Lizenz
oder ausdrückliche Regelung für die hier geplante Logo-Nutzung.
PULT liefert nur den erzeugten Schriftzug mit, nicht die Schriftdateien oder
den Generator. Dessen Lizenz ist keine automatische Freigabe des Schriftzugs.

Eine Erlaubnis wurde angefragt; eine Bestätigung liegt bislang nicht vor.
Die Herkunftsangabe ersetzt keine gegebenenfalls notwendige Erlaubnis.
Vor der Veröffentlichung muss die Nutzung und Weitergabe geklärt oder der
Schriftzug ersetzt werden. Aus der GPL-Angabe des Programmcodes darf keine
bestätigte GPL-Freigabe dieses Fremdbestandteils abgeleitet werden.
