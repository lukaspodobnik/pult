# PULT

PULT ist ein lokaler Unterrichtsplaner fürs Terminal: Stundenplan, Sequenzen,
Materialien, Leistungsnachweise und Fortschritt je Klasse und Fach.
Enthalten sind Vorlagen für Mathematik und Informatik am bayerischen Gymnasium.
Kein Konto nötig; nach der Einrichtung offline nutzbar.

## Installation und Update

Benötigt werden [uv](https://docs.astral.sh/uv/), ein Texteditor und ein Terminal
mit mindestens **160 Spalten × 45 Zeilen**. Ghostty und Foot unterstützen die
grafische Dokumentansicht; alternativ gibt es eine Textansicht.

```sh
uv tool install --force --python 3.11 https://github.com/lukaspodobnik/pult/releases/download/v1.4.0/pult-1.4.0-py3-none-any.whl
pult
```

Falls `pult` nicht gefunden wird: `uv tool update-shell` ausführen und das Terminal
neu öffnen.

Für Dokumentgrafik und PDF-Export **Dokumentdarstellung einrichten** wählen.
PULT lädt dafür Chromium herunter und meldet unter Linux fehlende Systempakete.

## Verwendung

Beim ersten Start Datenordner, Editor und Schuljahr wählen. Unter **Verwaltung**
Klassen anlegen und den Stundenplan eintragen. Sequenzen und Materialien stehen
unter **Unterricht**; `e` öffnet Inhalte im gewählten Editor.

Mit Fokus auf **Ansichten** gelten:

| Taste | Aktion |
| --- | --- |
| `o` | Nächste Stunde öffnen |
| `n` | Stunde abschließen |
| `c` | Termin buchen, Inhalt zur Fortsetzung offenlassen |
| `p` | In der Klassenansicht die letzte Buchung zurücknehmen |

**F1** zeigt die Tasten der aktuellen Ansicht. Stoffverteilungsplan, Stundenplan
und Aufgaben lassen sich als PDF exportieren.

Materialien liegen als Markdown und TOML im gewählten Datenordner.
Formate und Beispiele: [Materialvertrag](src/pult/defaults/vorbereitung/materialvertrag.md).

[Änderungen und Update-Hinweise](CHANGELOG.md) · [GPL-3.0-or-later](LICENSE) ·
[Quellen und Fremdbestandteile](SOURCES.md)
