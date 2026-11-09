# Materialvertrag

Dieser Vertrag beschreibt das Dateiformat für PULT. Didaktische Vorgaben und der
Ablauf einer KI-gestützten Vorbereitung werden gesondert festgelegt.

## Sequenz

Eine Sequenz liegt unter `sequences/<Jahrgang>/<Fach-ID>/<Sequenz-ID>/`.
`sequenz.toml` enthält `id`, `curriculum_section_id`, `subject_id`, `grade_level`,
`titel` und die geordnete Liste `stunden` mit Stunden-IDs. Optional sind
`recommended_lesson_count`, gemeinsam `chapter_id` und `chapter_title` sowie
die Buchtabelle `buecher` (siehe Herkunft einer Aufgabe).
Die Angaben müssen zum Ablageort passen; weitere Felder sind nicht erlaubt.

Stunden-, Aufgaben-, Fach- und Sequenz-IDs bestehen aus Kleinbuchstaben, Zahlen
und einzelnen Bindestrichen, etwa `brueche-vergleichen`. Referenzlisten enthalten
keine Duplikate. Bestehende IDs erhalten: Klassenfortschritt und Zuordnungen
verweisen darauf. Materialien bleiben unabhängig von konkreten Klassen und Terminen.

## Stunde

Unter `stunden/<Stunden-ID>/` liegen fünf Dateien:

| Datei | Inhalt und Validierung |
| --- | --- |
| `stunde.toml` | Nicht leerer `titel`, optionale Liste `aufgaben` und optionaler Text `hinweise`; keine weiteren Felder. |
| `vorbereitung.md` | Freies Markdown; als Konvention beginnt es mit `# Stundentitel`. |
| `ziele.md` | Flache ungeordnete Liste; pro Eintrag genau ein Absatz, Inline-Markdown erlaubt. |
| `verlauf.md` | Beginnt mit einer nicht leeren `#`-Phasenüberschrift; darunter freies Markdown. Weitere Überschriften ausschließlich als `#`, keine Unterüberschriften oder Setext-Überschriften. |
| `material.md` | Flache ungeordnete Liste aus Dingen und benannten Links; pro Eintrag ein Absatz und höchstens ein Link. |

Leere Markdown-Dateien sind gültig. Fehlende Markdown-Dateien werden als leer
behandelt. Leere Phasen sind erlaubt; Überschriften in Codeblöcken zählen nicht
als Phasen. Ziele und Verlauf erscheinen gemeinsam in der Planung, der Verlauf
als Tabelle mit den Spalten Zeit, Phase und Inhalt. Die Dauer in Minuten steht
als führende fett gesetzte Zahl im Phasentext, etwa `**5**`. In der Zeitspalte
erscheint nur die Zahl; ohne Zeitangabe bleibt sie leer. Materiallinks stehen
ausschließlich in `material.md`.

```toml
titel = "Brüche vergleichen"
aufgaben = ["vergleichen"]
hinweise = "Übungstheke · Computerraum"
```

`aufgaben` verweist auf vorhandene Aufgaben dieser Sequenz; ihre Reihenfolge ist
die Reihenfolge des Vormerkens. PULT kann die Zuordnung verwalten. `hinweise`
enthält kurze organisatorische Angaben für den Stoffverteilungsplan.

```markdown
- Schere
- [Präsentation](../../dateien/brueche.key)
- [Übungsseite](https://example.org/uebung)
```

Dateilinks beziehen sich auf `material.md` und bleiben innerhalb der Sequenz.
Weblinks verwenden `https://` oder `http://`. Dateien öffnen sich in der
zugeordneten Anwendung, Webseiten im Standardbrowser.

## Aufgaben und Markdown

Unter `aufgaben/<Aufgaben-ID>/` liegen `aufgabe.toml`, `aufgabe.md` und optional
`loesung.md`. Beide Markdown-Dateien sind frei gestaltbar. Der Anzeigename stammt
aus `aufgabe.toml`; eine Überschrift im Aufgabentext ist optional. Aufgaben können
mehreren Stunden derselben Sequenz zugeordnet sein.

Buchaufgaben haben keine laufende PULT-Nummer. Titel enthalten die Buchfundstelle,
etwa `Trainieren, S. 32 A. 8`, passend zu `[quelle]`. PULT prüft Seite und Nummer
und sortiert numerisch nach Buchseite und Aufgabe. Innerhalb einer Seite stehen
unnummerierte Einstiege zuerst, dann arabisch und danach römisch nummerierte
Aufgaben. Bei Einstiegen ersetzt die Bezeichnung die Aufgabennummer. Eigene
Aufgaben folgen danach: führende Titelnummern numerisch, sonst alphabetisch.
Bestehende Aufgaben-IDs und die Reihenfolge von Vormerklisten bleiben erhalten.

```toml
titel = "Nullstellen bestimmen"
kompetenzen = ["K5"]
anforderungsbereich = "I"
```

Alle drei Felder sind Pflicht: ein nicht leerer Titel, eine Liste aus ein bis drei
verschiedenen, nicht leeren Kompetenzbezeichnungen und genau ein Anforderungsbereich
als `"I"`, `"II"` oder `"III"`. Optional sind die Tabellen `quelle` und `export` (siehe unten).
Weitere Felder sind nicht erlaubt. Kompetenzbezeichnungen
richten sich nach dem Fach; vorzugsweise eine oder zwei Hauptkompetenzen wählen.

Die Gesamtaufgabe erhält den höchsten Bereich ihrer Teilaufgaben: III vor II vor I.
Gemischte Teilaufgaben bleiben zusammen. Diese grobe Einordnung wird von der
Lehrkraft oder der vorbereitenden KI angegeben; PULT prüft die Form, nicht den
fachlichen Inhalt. Für LNWs ist eine gesonderte Einordnung der Teilaufgaben nötig.
Kompetenzen und Anforderungsbereich gehören nicht in den Schülertext.

### Zuordnung zu Stunden

Die Vormerkung für Stunden bestimmt die Unterrichtsauswahl und den Export.
In der Aufgabenbibliothek ordnet `v` eine Aufgabe der aktuellen Stunde zu oder
entfernt die Zuordnung. Der Haken kennzeichnet die Vormerkung; eine zusätzliche
Sequenzauswahl gibt es nicht. Beim Vorbereiten die Aufgaben bereits den geplanten
Stunden zuordnen, damit der Sequenzexport zu Beginn vollständig verfügbar ist.
Dafür müssen noch keine Verlaufspläne angelegt werden. Nicht zugeordnete Aufgaben
bleiben im Bestand verfügbar. Alle Teilaufgaben bleiben vollständig erhalten.

### Herkunft einer Aufgabe

Buchtitel werden einmal in `sequenz.toml` registriert:

```toml
[buecher]
fokus-7 = "Fokus Mathematik 7"
```

Die Schlüssel folgen denselben ID-Regeln wie Aufgaben. Jeder Titel ist ein nicht
leerer Text. Buchaufgaben erhalten in `aufgabe.toml` eine strukturierte Quelle:

```toml
[quelle]
art = "buch"
buch = "fokus-7"
seite = 32
nummer = "8"
rubrik = "Trainieren"
```

`buch` verweist auf einen registrierten Buchtitel; `seite` ist eine positive
Ganzzahl. `nummer` ist eine positive arabische Zahl ohne führende Nullen oder
eine gültige römische Zahl in Großbuchstaben, jeweils als Text (`"8"`, `"II"`). Unnummerierte Einstiege verwenden stattdessen `bezeichnung`, etwa
`bezeichnung = "Äquivalente Terme"`. Genau eines der beiden Felder ist nötig.
`rubrik` ist optional. Titel, Seite und Nummer bzw. Bezeichnung reichen aus;
Ausgabejahr und ISBN werden nicht benötigt und nicht erfragt.

Eigene Aufgaben können ausdrücklich `[quelle]` mit `art = "eigen"` erhalten;
Buchfelder sind dann nicht erlaubt. Ohne `quelle` bleiben ältere Aufgaben beim
bisherigen Exportverhalten für eigene Aufgaben. Die Herkunft wird nicht aus
Titel, Jahrgang oder ID erraten. Vor dem Export älterer Buchbestände die Quellen
nachtragen. Aufgaben-IDs und Stundenverknüpfungen bleiben dabei erhalten.

Markdown unterstützt Tabellen, Codeblöcke mit Sprachangabe, TeX als `$…$` bzw.
`$$…$$` und lokale Bilder (SVG, PNG, JPEG, WebP). Bildpfade sind relativ zur
Markdown-Datei und bleiben innerhalb des Sequenzordners; gemeinsame Dateien
können in `dateien/` liegen. HTML wird nicht ausgeführt, entfernte Bilder werden
nicht geladen. Links innerhalb gerenderter Dokumentbilder sind nicht anklickbar.

Teilaufgaben lassen sich als Block mit festen Abständen zwischen Buchstaben und
Inhalt setzen. Ohne `spalten` stehen sie untereinander; `spalten=2` oder `spalten=3`
wünscht zwei bzw. drei gleich breite Spalten in zeilenweiser Reihenfolge. Bei wenig
Platz werden es automatisch weniger Spalten. In der Textansicht bleiben sie untereinander.

```markdown
:::teilaufgaben spalten=3
a) $4a \cdot 3b$

b) $2x \cdot 5x$

c) $3a \cdot b \cdot 2a \cdot b$
:::
```

Jede Teilaufgabe beginnt in einem neuen Absatz mit `a)`, `b)`, …; dazwischen steht
eine Leerzeile. Weitere Absätze, Formeln, Listen oder Bilder gehören bis zur nächsten
Beschriftung zur selben Teilaufgabe. `:::` beendet den Block. Außerhalb solcher
Blöcke bleibt die Darstellung unverändert. Aufgabe und Lösung können unterschiedliche
Spaltenzahlen verwenden. Beim Arbeitsheftexport wird dieselbe Struktur verwendet; Antwortbereiche
werden ausschließlich für das Aufgabenheft ergänzt.

Abbildungen lassen sich kompakt neben den zugehörigen Text setzen:

```markdown
:::abbildung
Bestimme den Flächeninhalt des Rechtecks.

![Rechteck mit den Seiten a und b](../../dateien/rechteck.svg)
:::
```

Der Block enthält genau ein freistehendes Bild und den zugehörigen Text;
bei wenig Breite steht das Bild darunter. Text, Formeln und Teilaufgaben bleiben
normales Markdown. Bei verschachtelten Blöcken außen vier Doppelpunkte (`::::`)
verwenden. In der Textansicht entfällt nur die Anordnung nebeneinander.

Definitionen und Merksätze lassen sich als beschriftete Blöcke hervorheben:

```markdown
> [!definition] Gerade Zahl
> Eine durch $2$ teilbare ganze Zahl heißt **gerade**.

> [!merksatz] Distributivgesetz
> Für Zahlen $a$, $b$ und $c$ gilt: $a(b+c)=ab+ac$.
```

Der Titel nach der Markierung ist optional. Alle Zeilen des Blocks beginnen mit
`>`, auch Leerzeilen. Darin sind normales Markdown und TeX möglich. Definitionen
sind blau mit der Beschriftung „Definition“, Merksätze orange mit „Merke“.
Die Farbtöne passen sich dem Theme an. In der
Textansicht bleiben die Beschriftungen erhalten. Diese Schreibweise ist in allen
frei gestaltbaren Markdown-Dokumenten verfügbar; sie schreibt keinen Aufbau vor.

Eine freistehende Markdown-Trennlinie (`---`) markiert eine Fortsetzung; bei
einem wachsenden Kasten steht sie davor. Passt `vorbereitung.md` nicht vollständig
in die Unterrichtsansicht, rückt die erste solche Linie beim Öffnen möglichst in
die Mitte, begrenzt durch das Dokumentende. Vollständig sichtbare Einträge und
Einträge ohne Trennlinie beginnen oben.

## Aufgabenexport

In der Aufgabenbibliothek exportiert `x` die vorgemerkten Aufgaben der aktuellen
Stunde in der Reihenfolge ihrer Vormerkungen. Ohne Stundenkontext ist `x` nicht
verfügbar. `X` (Umschalt+x) exportiert die Aufgaben aller Stunden dieser Sequenz,
jede Aufgaben-ID nur einmal, in der Reihenfolge der Aufgabenbibliothek. Nicht
zugeordnete Aufgaben werden nicht exportiert. Ohne Vormerkungen meldet PULT dies
und lässt vorhandene Exporte unverändert.

Die Ablage ist `exports/<Schuljahr>/materialien/<Fach-ID>/<Jahrgang>/<Sequenz-ID>/`.
Der Sequenzexport erzeugt `aufgaben.pdf` und `loesungen.pdf`, der Stundenexport
`<Stunden-ID>-aufgaben.pdf` und `<Stunden-ID>-loesungen.pdf`.
So bleiben Exporte verschiedener Stunden und der gesamten Sequenz getrennt.
Das Exportprofil folgt den Quellen der tatsächlich exportierten Aufgaben:

- Nur Buchaufgaben: „S. 32 · Aufgabe 8“ statt einer fortlaufenden Exportnummer.
  Unnummerierte Einstiege zeigen ihre Bezeichnung. Die Buchrubrik steht dezent
  darunter. Der Buchtitel erscheint einmal am Anfang; bei mehreren Büchern
  zusätzlich bei jeder Aufgabe. Der persönliche Name entfällt.
- Nur eigene Aufgaben: bisherige Nummerierung „1. Aufgabe“, „2. Aufgabe“ usw.
  und der konfigurierte Name in der Fußzeile.
- Gemischter Bestand: fortlaufende Exportnummern; Buchaufgaben zeigen zusätzlich
  Buchtitel, Seite und Buchnummer. Kein persönlicher Name für die gesamte Sammlung.

Aufgaben und Lösungen erhalten dieselben Nummern und Quellenangaben. Im
Lösungsheft lautet die Quellenzeile „Lösungen zu Aufgaben aus“, denn die Lösungen
werden eigenständig erstellt. Eine führende `#`-Überschrift wird durch die
Profilbeschriftung ersetzt; weitere Überschriften bleiben erhalten. Die internen
PULT-Titel und ihre Sortierung ändern sich nicht. Kompetenzen und
Anforderungsbereiche werden nicht gedruckt. Bei zugeordneten Aufgaben verhindern
leere Texte oder fehlende/leere Lösungen den Export mit Hinweis auf die betroffene
Aufgabe. Nicht zugeordnete Aufgaben benötigen für diesen Export keine Lösung.

Antwortbereiche stehen optional in `aufgabe.toml`:

```toml
[export]
antwortbereich = "kariert"
zeilen = 6
pro_teilaufgabe = true
```

- `antwortbereich`: `"kariert"`, `"linien"` oder `"keiner"`. Pro Teilaufgabe wird
  nur eine Art verwendet; Linien und Karofelder werden nicht gemischt.
- `zeilen`: 1 bis 40. Bei Karofeldern zählt eine Zeile ein Kästchen (etwa 5 mm),
  Schreiblinien haben 7 mm Abstand; die erste Linie folgt Textaufträgen enger.
  Ohne Bereich gilt 0. Überhohe Felder werden mit einer Fehlermeldung abgelehnt,
  damit nichts abgeschnitten wird.
- `pro_teilaufgabe`: `true` ergänzt einen Bereich nach jeder Teilaufgabe eines
  `:::teilaufgaben`-Blocks; `false` einen gemeinsamen Bereich unter der Aufgabe.
  Ohne Teilaufgabenblock `false` verwenden. Karofelder reichen immer über die
  volle Inhaltsbreite, links bündig mit dem Teilaufgabenbuchstaben und rechts
  bis zum Inhaltsrand. Ganze quadratische Kästchen füllen die Breite; ihre Größe
  wird minimal an 5 mm angenähert. Mit Karofeldern je Teilaufgabe ist der Druck
  einspaltig.
  Teilaufgabe und Feld bleiben auf derselben Seite.
- `spalten`: optionale Druckspaltenzahl (1–3). Bei Schreiblinien gilt standardmäßig
  1, höchstens 2; bei Karofeldern je Teilaufgabe ausschließlich 1. Ohne eigene
  Angabe folgt die übrige Darstellung den Markdown-Spalten.
- `gleichheitszeichen = true`: ergänzt nur im Aufgabenexport ein `=` hinter
  einem einzelnen mathematischen Ausdruck, ohne ein vorhandenes zu verdoppeln.
  Erfordert Schreiblinien je Teilaufgabe; nicht für Textaufträge verwenden.
- `bildbreite_mm`: optionale maximale Bildbreite/-höhe (10–167 mm) für Aufgaben
  und Lösungen. Ohne Angabe gilt 65 mm. Für große Diagramme eine gut lesbare
  Größe wählen; die verfügbare Inhaltsbreite bleibt die obere Grenze.
- `[export.teilaufgaben.a]` (entsprechend `b`, …): überschreibt `zeilen` und/oder
  `bildbreite_mm` für diese Teilaufgabe. Abweichende Zeilen benötigen
  `pro_teilaufgabe = true`. Die Buchstaben beziehen sich auf die äußeren
  Teilaufgaben und müssen eindeutig vorhanden sein.

Ohne `export` gilt ein gemeinsames Karofeld mit acht Zeilen. Fehlende Einzelwerte
verwenden `kariert`, `false` und acht Zeilen (für `linien` eine, für `keiner` null).
Schreiblinien folgen einzelnen Formeln bei Platz direkt in derselben Zeile,
Textaufträgen darunter. Linien nicht durch Unterstriche vortäuschen.
Druckspalten, ergänzte Gleichheitszeichen und Bildgrößen verändern weder die
Markdown-Dateien noch die PULT-Ansicht. Die globale Bildgröße gilt auch für
Lösungen; die übrigen Exportoptionen und teilaufgabenspezifischen Größen gelten
nur im Aufgabenheft. Lösungen erhalten keine Antwortbereiche. Umfang und Art je Teilaufgabe aus einer knappen, vollständigen
und altersgerechten Musterlösung ableiten: nötige Zwischenschritte, Begründungen,
Skizzen und Handschrift berücksichtigen, mit nur kleiner Reserve. Abgedruckte
Ausdrücke müssen nicht nochmals abgeschrieben werden. Keine pauschalen
Mindestflächen; acht Standardzeilen ersetzen diese Einschätzung nicht.

Zwischen Teilaufgaben sind Seitenumbrüche möglich. Überschrift, Einleitung und
erste Teilaufgabe bleiben zusammen, ebenso jede Teilaufgabe mit ihrem
Antwortbereich. Gemeinsame Bereiche bleiben beim zugehörigen Auftrag. Bei der
Ausarbeitung den gesamten Export auf unnötige Umbrüche und übergroße
Antwortbereiche prüfen.

Das A4-Hochformat hat 25 mm linken und 18 mm rechten Rand. Es verwendet die
Dokumentschrift, klassische mathematische Schrift, dezente graue Tabellenköpfe
und feine Rechenraster. Aufgabenüberschriften haben dieselbe Größe wie der
Fließtext (11,5 pt), in Halbfett. Die Kopfzeile nennt Fach, Jahrgang und Sequenz.
Kopf- und Fußzeile einschließlich Name und Seitenzahl erscheinen in sanftem,
gut lesbarem Grau (`#647282`), auch im gedruckten PDF. Der Name für die Fußzeile
wird unter **Einstellungen → Name auf Arbeitsblättern** gesetzt; ein leeres Feld
lässt ihn weg. Bei Buch- und Mischprofilen wird er unabhängig von dieser
Einstellung weggelassen. Bestehende PDFs werden erst nach erfolgreicher Erzeugung beider
Dokumente ersetzt.

## Muster und Änderungen

Beim Einrichten und beim Ergänzen von Stunden im Sequenzeditor legt PULT fehlende
Dateien an. Vorhandene Inhalte bleiben erhalten. Die Muster enthalten nur:

- `stunde.toml`: `titel = "Noch nicht vorbereitet"` und `aufgaben = []`.
- `vorbereitung.md`: `# Noch nicht vorbereitet`.
- `ziele.md`: zweimal `- Die Schüler können`.
- `verlauf.md`: `# Einstieg`.
- `material.md`: leer.

Beim Anlegen einer Aufgabe werden Titel, Hauptkompetenzen und Anforderungsbereich
abgefragt. PULT erstellt die drei Aufgabendateien und öffnet sie im Editor.
Unter „Bearbeiten → Titel, Einordnung und Export“ lässt sich `aufgabe.toml` später ändern.
Bestehende Aufgaben benötigen ebenfalls diese Datei; PULT ergänzt keine
fachlichen Angaben automatisch.

Nach dem Bearbeiten validiert PULT die Dateien. Bei Fehlern bleibt die letzte
gültige Ansicht sichtbar; die Datei wird nicht automatisch korrigiert.
Das frühere Format mit Zielen und Verlauf in TOML wird nicht übernommen.
