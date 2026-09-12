# PULT 1.1.1

Überarbeitete Darstellung, eine übersichtlichere Tastaturhilfe und direktes
Speichern in der Stundenplanverwaltung.

## Darstellung und Bedienung

- Eigenes dunkles Standardtheme für Systeme ohne Omarchy: Anthrazit, hellgrauer
  Text und ein gedämpfter warmer Orangeton als Akzent. Flächen, Rahmen und
  Fokusmarkierungen folgen denselben Gestaltungsregeln wie unter Omarchy.
  Dort folgt PULT weiterhin automatisch dem aktuellen Systemtheme.
- Der Footer passt die angezeigten Aktionen an die verfügbare Breite an und
  richtet sie an den Inhaltsrahmen aus. Hilfe und Beenden bleiben sichtbar;
  ausgeblendete Tastenkürzel können weiterhin verwendet werden.
- **F1** öffnet die Tastaturhilfe zur aktuellen Ansicht und zum aktuellen Fokus.
  Die Befehle sind nach Navigation, Aktionen der Ansicht und allgemeinen
  Befehlen gruppiert. Pfeiltasten und ihre **h/j/k/l**-Alternativen stehen
  gemeinsam in der Liste. Esc oder F1 schließt die Hilfe.
- Zentrierte Stundenplaneinträge auf der Übersicht. In der Stundenplanverwaltung
  sind alle Stundenzeilen gleich hoch; Tabellenlinien schließen bündig aneinander an.
- Stundenplaneinträge werden beim Speichern im Eingabedialog oder beim Löschen
  sofort gesichert. Ein zusätzlicher Speicherschritt in der Übersicht entfällt.
  **Zurück** und **Esc** verlassen die Übersicht, ohne gespeicherte Änderungen
  zu verwerfen. Nicht bestätigte Eingaben im einzelnen Dialog können weiterhin
  abgebrochen werden.
- Die Bestätigungsbuttons in den Eingabedialogen für Stundenplaneinträge,
  Klassen und Ausfälle heißen einheitlich **Speichern**.

## Fehlerbehebung

- Die Schuljahresprüfung greift beim Beenden nicht mehr auf einen bereits
  geschlossenen Bildschirm zu.

## Voraussetzungen und Daten

Python 3.11 oder neuer. Für grafische Formeln und SVG-Bilder werden zusätzlich
Node.js, `rsvg-convert` und ein Terminal mit passender Bildunterstützung benötigt.
MathJax ist enthalten; npm ist zur Nutzung nicht erforderlich. Ohne Grafikrenderer
erscheinen Formelquellen beziehungsweise Bildhinweise.

Das Datenformat bleibt gegenüber 1.1.0 unverändert. Für dieses Update ist keine
Migration erforderlich.

## Installation und Update

Nach Veröffentlichung von v1.1.1:

```sh
uv tool install --force --python 3.11 https://github.com/lukaspodobnik/pult/releases/download/v1.1.1/pult-1.1.1-py3-none-any.whl
```

Die Veröffentlichung erfolgt über GitHub. Eine AUR-Veröffentlichung ist für
dieses Release nicht vorgesehen.
