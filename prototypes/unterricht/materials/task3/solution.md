```python
geheimzahl = 42
versuch = int(input("Dein Tipp: "))
anzahl = 1

while versuch != geheimzahl:
    if versuch < geheimzahl:
        print("Zu klein!")
    else:
        print("Zu groß!")
    versuch = int(input("Dein Tipp: "))
    anzahl += 1

print(f"Richtig! Du hast {anzahl} Versuche gebraucht.")
```

**Besprechung:** Die erste Eingabe steht vor der Schleife. So lässt sich die Bedingung schon vor dem ersten Durchlauf prüfen. Der Zähler berücksichtigt auch diesen ersten Tipp.
