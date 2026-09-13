# Gymnasium: Informatik 13 (erhöhtes Anforderungsniveau)

## Inf13 Lernbereich 1: Internet der Dinge (ca. 15 Std.)

**Kompetenzerwartungen**

Die Schüler ...

- erläutern den Begriff Internet der Dinge (IoT, Internet of Things) und beschreiben Einsatzmöglichkeiten von IoT-Systemen, z. B. Smarthome.

- entwickeln Anwendungen für eine Physical-Computing-Plattform, z. B. zur Erfassung von Messdaten mit Sensoren und zur Steuerung von Aktoren.

- entwickeln im Team eine Client-Server-Anwendung in einem lokalen Netzwerk unter Verwendung einer Physical-Computing-Plattform, um Daten zu erfassen, zu verarbeiten, darzustellen und (persistent) zu speichern, z. B. mithilfe eines Datenbankservers. Dabei verwenden sie geeignete Protokolle.

- analysieren IoT-Systeme, die auch außerhalb eines lokalen Netzwerks erreichbar sind, insbesondere im Hinblick auf mögliche Angriffsszenarien.

- erweitern ihre entwickelte Client-Server-Anwendung zu einem einfachen IoT-System, auf das auch von außerhalb des lokalen Netzwerks zugegriffen werden kann, und ergreifen dabei Sicherheitsmaßnahmen zum Schutz vor möglichen Angriffen.

- erläutern Chancen und Risiken des Internets der Dinge aus individueller und gesellschaftlicher Sicht. Dabei reflektieren sie insbesondere ihren eigenen Umgang mit IoT-Systemen.

**Inhalte zu den Kompetenzen:**

- Internet der Dinge (IoT, Internet of Things): u. a. Sensoren, Aktoren, Client, Server

- Sicherheitsmaßnahmen: organisatorisch (z. B. Richtlinien, Passwortregeln), technisch (z. B. Antivirensoftware, Firewall, Verschlüsselung, Sandbox), physisch, z. B. Zugangskontrolle

## Inf13 Lernbereich 2: Künstliche Intelligenz (ca. 34 Std.)

**Kompetenzerwartungen**

Die Schüler ...

- erstellen eine Wissensbasis zu einem abgeschlossenen System der realen Welt (z. B. Stammbaum) durch die Angabe von Fakten und Regeln. Dabei verwenden sie auch rekursive Beschreibungen.

- entwerfen Anfragen an eine Wissensbasis mithilfe eines Softwaresystems zur Lösung von Fragestellungen, z. B. Färbung von Landkarten, logische Rätsel.

- untersuchen und beschreiben an Beispielen die Strategie der automatisierten Ableitung von Aussagen durch eine Inferenzmaschine.

- erklären den prinzipiellen Aufbau eines künstlichen neuronalen Netzes, führen an einfachen Beispielen eine Forward Propagation zu gegebenen Eingabewerten durch und beschreiben die Zielsetzung der Fehlerrückführung.

- analysieren unter Verwendung einer geeigneten Software den Einfluss von Trainingsdaten und Hyperparametern, insbesondere der Anzahl von Schichten und Neuronen, auf den Lernerfolg künstlicher neuronaler Netze.

- beschreiben die Funktionsweise des k-Means-Algorithmus als Beispiel unüberwachten Lernens und implementieren diesen für ein Beispiel.

- analysieren für verschiedene Eingabedaten die Ergebnisse, die der k-Means-Algorithmus in Abhängigkeit von k liefert.

- erläutern die Grundprinzipien überwachten Lernens (supervised learning), unüberwachten Lernens (unsupervised learning) und bestärkenden Lernens (reinforcement learning).

- wenden ein maschinelles Lernverfahren auf eine Problemstellung an. Mithilfe geeigneter Softwaresysteme bereiten sie dabei je nach Verfahren Daten vor, variieren Parameter und interpretieren und bewerten ihre Ergebnisse.

- nehmen zu aktuellen Einsatzmöglichkeiten des maschinellen Lernens (z. B. Gesichtserkennung, Clustering von Kundendaten zu Marketingzwecken) Stellung, indem sie Chancen und Risiken beschreiben und diese hinsichtlich individueller und gesellschaftlicher Verantwortung bewerten.

**Inhalte zu den Kompetenzen:**

- wissensbasiertes System: Wissensbasis (Prädikat, Fakt, Regel), Inferenzmaschine

- neuronales Netz: Ein-, Ausgabeschicht, verdeckte Schicht, Gewichte; Forward Propagation und Fehlerrückführung (Backpropagation), Kostenfunktion

- Clustering, k-Means-Algorithmus

- maschinelles Lernen: überwachtes Lernen (supervised learning), unüberwachtes Lernen (unsupervised learning), bestärkendes Lernen (reinforcement learning)

- ethische Fragen bei Künstlicher Intelligenz

## Inf13 Lernbereich 3: Formale Sprachen und Automaten (ca. 24 Std.)

**Kompetenzerwartungen**

Die Schüler ...

- untersuchen formale Sprachen aus ihrem Alltag (z. B. Autokennzeichen, E-Mail-Adressen, Gleitkommazahlen) und formulieren Regeln, nach denen die Menge der Wörter der jeweiligen Sprache gebildet wird.

- definieren Grammatiken zur Erzeugung formaler Sprachen. Für geeignete Grammatiken verwenden sie zur Notation der Produktionsregeln insbesondere die Erweiterte Backus-Naur-Form (EBNF) und Syntaxdiagramme.

- entwerfen zum Erkennen regulärer Sprachen endliche Automaten.

- implementieren deterministische endliche Automaten zur automatisierten Überprüfung der Zugehörigkeit von Wörtern zu einer regulären Sprache.

- erläutern das Konzept des Nichtdeterminismus bei Automaten anhand geeigneter Beispiele.

- erläutern anhand von Beispielen wie beliebig tief geschachtelten Klammerausdrücken, dass es Sprachen gibt, die nicht regulär sind. Damit wird ihnen bewusst, dass für die automatisierte Verarbeitung von nicht regulären Sprachen, wie z. B. höheren Programmiersprachen, das Modell des endlichen Automaten nicht ausreicht.

- beschreiben das Modell der Turingmaschine und erläutern anhand von Beispielen ihre Funktionsweise bei der Erkennung von Sprachen.

- entwerfen Turingmaschinen für einfache Beispiele Turing-erkennbarer Sprachen.

**Inhalte zu den Kompetenzen:**

- formale Sprache als Menge von Wörtern über einem Alphabet: Zeichen, Alphabet (Zeichenvorrat), Wort (Zeichenkette), Syntax, Semantik

- Grammatik: Terminal, Nichtterminal, Produktionsregel, Startsymbol

- Notation formaler Sprachen: u. a. Syntaxdiagramm und Erweiterte Backus-Naur-Form (EBNF)

- Ableitung eines Wortes einer formalen Sprache als Folge von Regelanwendungen; Ableitungsbaum

- endlicher Automat: Zustandsmenge, Eingabealphabet, Zustandsübergang, Startzustand, Endzustand, Fehlerzustand (Fangzustand); reguläre Sprache

- Automat: deterministisch, nichtdeterministisch

- Turingmaschine: Zustandsmenge, Eingabealphabet, Bandalphabet, Zustandsübergang, Konfiguration; Turing-erkennbare Sprache

## Inf13 Lernbereich 4: Algorithmen, Komplexität und Berechenbarkeit (ca. 32 Std.)

**Kompetenzerwartungen**

Die Schüler ...

- erläutern den Begriff Turing-Berechenbarkeit und zeigen für einfache Funktionen (z. B. Inkrement einer Binärzahl, Summe binärer Zahlen) durch Angabe einer passenden Turingmaschine, dass diese Funktionen Turing-berechenbar sind. Sie präzisieren den Algorithmusbegriff und nennen die Äquivalenz verschiedener Berechnungsmodelle (Church-Turing-These).

- bewerten durch Zeitmessungen und Zählverfahren (z. B. Zählen der Aufrufe bei der Ausführung rekursiver Algorithmen, Zählen der zeitkritischen Anweisungen) den Laufzeitaufwand von Algorithmen.

- beschreiben das asymptotische Laufzeitverhalten von Algorithmen unter Verwendung der Landau-Notation.

- begründen, dass ein hoher Laufzeitaufwand sicherheitsrelevant sein kann, z. B. bei der Ermittlung eines Passworts mit dem Brute-Force-Verfahren.

- entwerfen Algorithmen zur Lösung von Problemen und implementieren ausgewählte Beispiele. Dazu wenden sie geeignete Strategien an, wählen passende Datenstrukturen und nutzen ggf. die Möglichkeit, ein Problem auf ein anderes zurückzuführen (z. B. das SAT-Problem auf das Cliquenproblem); sie betrachten dabei auch Algorithmen, die Näherungslösungen liefern, z. B. zur Lösung des Handlungsreisendenproblems.

- vergleichen und beurteilen Algorithmen zur Lösung eines Problems u. a. hinsichtlich des Laufzeitverhaltens und schätzen die Komplexität des betrachteten Problems ab.

- beschreiben die Definition der Komplexitätsklassen P und NP sowie die Bedeutung der Fragestellung P≟NP, insbesondere für moderne Verschlüsselungsverfahren.

- erläutern das Halteproblem als Beispiel für Probleme, die nicht berechenbar sind.

**Inhalte zu den Kompetenzen:**

- Berechenbarkeit: Turing-berechenbar, Algorithmus, Church-Turing-These

- Laufzeitaufwand von Algorithmen (linear, quadratisch als Beispiele für polynomiales Laufzeitverhalten, exponentiell, logarithmisch), Best Case, Average Case, Worst Case

- Algorithmen: u. a. die Sortieralgorithmen Bubblesort, Mergesort

- Landausche O-Notation

- Lösungsstrategien: Brute-Force, Greedy, Divide and Conquer, Zurückführen auf ein bereits gelöstes Problem

- Probleme: Sortierproblem, SAT-Problem, Handlungsreisendenproblem, Rucksackproblem, Cliquenproblem

- Komplexität von Problemen, Komplexität von Algorithmen

- Mengen P und NP

- Halteproblem
