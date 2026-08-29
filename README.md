# Ein persönliches Projekt zur Verwaltung alltäglicher schulbezogener Aufgaben.

## Zusammenfassung

Eine kleine TUI, die Stundenplan, Unterrichtssequenzen und Ausfälle verwaltet. Der Fortschritt angelegter Klassen wird verfolgt und angezeigt. **Bayerische** Feiertage und Schulferien werden berücksichtigt, um die Anzahl verbleibender Unterrichtsstunden zu berechnen.


### Geplanter Funktionsumfang für Version 1

- Styling nach dem aktuellen **Omrachy**-Theme.
- Initialisierung eines Stammordners sowie Ordner für Schuljahre und Klassen.
- Verwaltung eines Stundenplans.
- Verwaltung von globalen Unterrichtssequenzen.
- Verwaltung von lokalen Unterrichtsausfällen.
- Verwaltung von schriftlichen Leistungsnachweisen (Art und Datum).
- Anzeigen von Metainformationen auf der Startseite.
- Anzeigen klassenspezifischer Informationen auf Klassenseiten.
	- Fortschritt der einzelnen Unterrichtssequenzen.
	- Bilanz von benötigten zu zur Verfügung stehenden Stunden.

### Vereinbarungen

- Verwaltung des Stundenplans in einer .csv Datei.
- Verwaltung von Unterrichtssequenzen in .toml Dateien.
- Editieren der Datein findet in einem externen Editor statt. Entsprechende Dateien werden über die TUI für easy-access geöffnet.

### TUI-Desing

- Spalte auf der linken Seite der TUI als **PICKER**.
- Rechtes Panel als Anzeige.
- Bedienung über **VIM-MOTIONS** und Pfeiltasten.
- Design so intuitiv wie möglich.
- Je weniger Tasten gedrückt werden müssen, um an die gewünschte Ansicht zu kommen, desto besser.
- ":" startet Eingabe für **Commands**.
- "q" beendet die TUI.
- Startseite über Hotkey sofort erreichbar (Wahl steht noch aus).