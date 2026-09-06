# Praxistest – Schooltools TUI v1

Datum: 6. September 2026
Terminal / Fenstergröße: vollbild (normaler laptop)
Editor: nvim
Aktuelles Theme: Omarchy Ristretto

Mit Testdaten arbeiten. Ein Häkchen bedeutet **geprüft**, nicht automatisch fehlerfrei.
Beobachtungen können Fehler, Unklarheiten oder Verbesserungsideen sein.

## 1. Navigation

- [x] Home, Klassen und Verwaltung mit Tab und Pfeiltasten bedienen.
- [x] Fokus ist jederzeit erkennbar; Escape führt nachvollziehbar zurück.
- [x] Klassenwechsel zeigt sofort die passende Ansicht.

**Beobachtungen:**

- Im MainScreen springt TAB nicht nur zwischen den beiden Naviagtionsleitsten hin und her, sondern auch in den Contentbereich.
- klassenwechsel und wechsel zu home zeigt sofort die passende ansicht, aber es hat ein wenig lagg. dieser lagg führt auch dazu, dass man bei schnellem klicken der pfeiltasten (zb nach unten) den fokus in der navigationsleiste nicht verfolgen kann -> die views werden erst geladen, dann wird der fokus aktualisiert (so scheint es mir zumindest)
- gleiches tab-problem in der Sequenzbibliothek. tab sollte nur in den conten springen, wenn da auch wirklich was zu scrollen ist
- escape springt überall sinnvoll zurück
- fokus ist nicht erkennbar, wenn man in den conten bereich der screens springt
- in den modalen screens ist nicht immer intuitiv klar, wo der fokus liegt. zb. beim ausführen von previous -> abbrechen ist zwar hinterlegt, aber der zurücknehmen-button ist rot und zieht die volle aufmerksamkeit an sich.

## 2. Stundenplan

- [x] Eintrag erstellen, Raum ändern und Eintrag löschen.
- [x] Änderungen speichern; separat Änderungen mit Abbrechen verwerfen.
- [x] Bei einer Klasse mit mehreren Fächern einen bestehenden Eintrag öffnen: Das richtige Fach bleibt ausgewählt.
- [ ] Tages- und Stundenmarkierung im Dashboard prüfen, möglichst auch während einer Pause.

**Beobachtungen:**

- Stundenmarkierung im Dashboard nicht prüfbar, weil kein schultag ist.


### Problem: …

- **Bereich / Ausgangssituation:** stundenplanbearbeitung
- **Schritte zum Reproduzieren:**
  1. eine zelle wählen -> enter
  2. eintrag anlegen
- **Erwartetes Verhalten:** stundenplaneintrag wird vollständig angezeigt
- **Tatsächliches Verhalten / Fehlermeldung:** eintrag wird abgeschnitten, solange bis man mit tab den stundenplan verlässt und wieder reinspringt. außerdem ändert sich bei naviagtion durch die einzelnen zellen die darstellung des plans: klickt man einmal durch den plan, dann nimmt er nach und nach seine "volle form" an.
- **Wiederholbar?** ja
- **Auswirkung:** störend und optisch
- **Screenshot oder weitere Hinweise:**

## 3. Fortschritt

- [x] Abschließen, Überspringen, Fortsetzen und spontanen Ausfall ausprobieren.
- [x] Nächste Stunde, Fortschrittsbalken und Protokoll ändern sich nachvollziehbar.
- [x] Befehle auf Home wirken global, in der Klassenansicht nur auf diese Klasse.
- [x] Letzte Stunde einer Sequenz abschließen: Auswahl der Folgesequenz und Abbrechen ausprobieren.
- [x] Aktive Sequenz in der Klassenansicht manuell wechseln.

**Beobachtungen:**

- änderungen in einer view führt zu sichtbarer neuberechnung (kurz schwarz -> richtige anzeige)
- ausfall eintragen funktioniert auch auf der homeview - das ist ein problem, da er für eine klasse eingetragen wird; dabei ist nicht klar, für welche klasse
- zurücknehmen (previous) zeigt im modal nicht an, was der letzte eintrag war; das sollte auf jeden fall noch eingefügt werden, sodass klar ist, was überhaupt zurückgenommen wird
- 

### Problem: …

- **Bereich / Ausgangssituation:** fortschrittsaktion in der homeview
- **Schritte zum Reproduzieren:**
  1. mehrere klassen mit unterschiedlichen fächern anlegen
  2. fortschrittsaktion ausführen
- **Erwartetes Verhalten:** nächste stunde wird angezeigt
- **Tatsächliches Verhalten / Fehlermeldung:** ein fach wird komplett übersprungen -> bei mir wird nur informatik angezeigt; mathematik nie
- **Wiederholbar?** jetzt funktioniert es auf einmal wieder. ich hab nichts geändert, nur noch viele male gedrückt.
- **Auswirkung:** blockiert Bedienung
- **Screenshot oder weitere Hinweise:**

## 4. Rücknahme

- [x] `previous` einmal abbrechen: Daten bleiben unverändert.
- [x] `previous` bestätigen: Letzter Eintrag wird zurückgenommen, Ansicht aktualisiert sich.
- [x] Rücknahme wird auf Home nicht angeboten.

**Beobachtungen:**

-

## 5. Zusatzunterricht

- [x] Zusatzunterricht ohne Abschluss der nächsten geplanten Stunde eintragen.
- [x] Zusatzunterricht mit Abschluss der nächsten geplanten Stunde eintragen.
- [x] Datum im Format `TT.MM.JJJJ` bearbeiten und Kommentar eintragen.
- [x] Terminart und Fortschrittswirkung im Protokoll kontrollieren.

**Beobachtungen:**

- bei klassen mit nur einem fach wird trotzdem eine fachauswahl angeboten -> sollte gleich fixiert werden
- zusatzunterricht lässt sich an tagen eintragen, an denen kein unterricht stattfindet

## 6. Sequenzbibliothek und Editor

- [x] Bibliothek öffnen; Fächer, Jahrgangsstufen und Sequenzen durchblättern.
- [x] Lange Vorschau scrollen; beim Sequenzwechsel beginnt die neue Vorschau oben.
- [x] Sequenz in nvim öffnen, bearbeiten, speichern und zur TUI zurückkehren.
- [x] Änderungen erscheinen sofort in der Vorschau; ein geänderter Sequenzentitel auch im Picker.
- [x] Nach der Editor-Rückkehr funktionieren Fokus und Tastatur weiterhin.

**Beobachtungen:**

- sequenz anzeige hat sehr viel whitespace; vielleicht ändert sich das mit einer tatsächlichen sequenz?
- Sequenzbibliothek ordnerbaum -> kann man die einrückung verringern? außerem sind nodes aufklappbar, die keine unternodes haben; das irritiert; das ist auch so wenn man eine sequenz editiert -> danach ist der pfeil nach unten, und zeigt sozusagen "aufgeklappt"

## 7. Ausfälle und Kalender

- [x] Schulweiten Ausfall anlegen und löschen.
- [x] Klassenbezogenen Ausfall anlegen und löschen.
- [x] Betroffene Termine und Stundenbilanz ändern sich passend; andere Klassen bleiben bei klassenbezogenen Ausfällen unverändert.
- [x] Ungültiges Datum bzw. unzulässigen Zeitraum eingeben: verständliche Fehlermeldung, Eingabe bleibt korrigierbar.

**Beobachtungen:**

- komplett leerer screen, wenn noch keine ausfälle existieren -> vielleicht ein hinweis einfügen?

## 8. Terminal und Darstellung

- [x] Fenster verkleinern und vergrößern.
- [x] Modals, Buttons und lange Inhalte bleiben erreichbar.
- [x] Umlaute, Statussymbole und Fortschrittsbalken werden korrekt dargestellt.
- [x] Hinweise sind lesbar und lange genug sichtbar.

**Beobachtungen:**

- das modal beim klassen-anlegen zeigt ein zu großes feld für die klassenauswahl - das ist viel zu groß für meistens nur 1 oder 2 optionen
- statussymbole können nicht getestet werden, weil gerade sonntag ist und die schule erst in einer woche beginnt


## 9. Beenden und Neustart

- [x] App insbesondere nach Benutzung der Bibliothek und des Editors beenden.
- [x] Shell erscheint ohne Hängenbleiben; Tastatur und Terminaldarstellung sind normal.
- [x] App neu starten: Gespeicherte Änderungen sind vorhanden, verworfene Änderungen nicht.

**Beobachtungen:**

-

## Fehlerbericht-Vorlage

Bei Bedarf pro Problem kopieren. Screenshots gerne ergänzen.

### Problem: …

- **Bereich / Ausgangssituation:**
- **Schritte zum Reproduzieren:**
  1.
  2.
- **Erwartetes Verhalten:**
- **Tatsächliches Verhalten / Fehlermeldung:**
- **Wiederholbar?**
- **Auswirkung:** Daten betroffen / blockiert Bedienung / störend / nur optisch
- **Screenshot oder weitere Hinweise:**

## Gesamteindruck und Wünsche für den Polish

- **Was funktioniert angenehm?**
- **Was ist unklar oder umständlich?**
- **Was sollte zuerst verbessert werden?**
- **Weitere Ideen:**

- Klassen anlegen: Wenn noch keine Klassen angelegt sind, dann sollte eine meldung erscheinen wie "Klasse anlegen". Außerdem sollte Der "Anlegen" button fokussiert sein.
- Die Klassenansicht ist noch nicht kompakt genug. Die Informatioen möchte ich nicht kürzen, aber in einem terminal auf vollem bildschirm, sollte man nicht so scrollen müssen. Das könnte auch das problem mit dem tab lösen -> man tabt nur in den content, wenn dieser auch wirklich scrollbar ist?
- in der klassenansicht muss der klassenname anders angezeigt werden. er steht gerade alleine ganz links oben. er ist zwar wichtig, aber sollte vielleicht eher beim fach stehen? dabei ist es in ordnung, wenn der klassenname mehrmals auftaucht, wenn eine klasse mehrere fächer hat.
- die hervorhebung der aktuellen sequenz in der classview ist gut so - dezent und sichtbar
- in homeview und bei stundenplanbearbeitung ist der stundenplan zu klein bzw. der bereich zu groß (vollbild terminal). hier entstehen große lücken; das sieht nicht gut aus
- beim anlegen von stundenplaneinträgen wäre es schön, wenn die eltzte klasse mit dem letzten fach und dem letzten raum für die nächste eintragung voreingestellt ist, sodass man schneller eine ganze klasse anlegen kann - oft wiederholt sich ja bspw. der raum
- 
- beim anlegen von stundenplaneinträgen wäre es schön, wenn die eltzte klasse mit dem letzten fach und dem letzten raum für die nächste eintragung voreingestellt ist, sodass man schneller eine ganze klasse anlegen kann - oft wiederholt sich ja bspw. der raum
- in homeview sollte bei nächster stunde auch der raum mit angezeigt werden.
- button-fokus ist nicht immer klar; das könnte vielleicht aber durch schöne konstante farbgebung gerichtet werden
- unterrichtsprotokoll sollte so gescrollt werden, dass der aktuellste eintrag zu sehen ist
- anordnung der verwaltungsoptionen muss noch besser gemacht werden. außerdem wäre vermutlich noch eine settings option sinnvoll oder? etwa um den editor zu ändern oder ähnliches.
- verwaltungsoptionen werden gebrochen, weil zu wenig platz in der navigationsleiste ist.

Die app funktioniert im kern, das ist gut! die darstellung in verschiedenen terminalgrößen ist noch nicht optimal. hier muss vermutlich auch die position der widgets angepasst werden. zum beispiel ist in einem terminal, das nur den halben screen einnimmt, der stundenplan nicht gant sichtbar. hier könnte man den stunden plan oben und daraunter links und rechts die nächste stunde + tagesansicht. das größte problem sind die großen whitespaces und der fokus bei der verwendung von TAB.


All meien Beobachtungen und anmerkungen sollen nicht als endgültig erfasst werden. Es ist durchaus möglich, dass sich meine meinung irgendwo noch ändern könnte; vielleicht auch durch bessere vorschläge von dir (der KI). Ich hab einfach nur meine ersten gedanken festgehalten.
