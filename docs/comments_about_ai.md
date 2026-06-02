---
title: "Comments about AI"
author: "Marco Schrank"
date: \today
geometry:
  - left=15mm
  - right=15mm
  - top=15mm
  - bottom=15mm
  - a4paper
fontsize: 12pt
header-includes:
  - \usepackage{geometry}
  - \usepackage{fontspec}
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhf{}
  - \rhead{\thepage}
toc: true
toc-depth: 3
number-sections: true
---

# Comments about AI

## Introduction
This text is a currated not comprehensible mingle-mangle of topics mainly about LLMs (Large Language Models) based on the Transformer architecture. 
There is also an overview of ML Algorithm as they are still the best option for their designated purposes. If a ML Algorithm can do the job, don't use 
a deep neural network. Not every problem is a nail! 
Actually LLMs are plain math, some linar algebra and stochastics mainly. To get a deeper inside into the details of the Transformer architecture, it is 
necessary to hit the math behind. This text tries to explain the principals without math as far as possible. If you skip the math part, it should be possible
to grab the meaning of the principals anyway. The harder (depends) part of each section is explicitly marked. As stated, at that point you should have got the 
meaning of the section. 
Some of the content is created or refined with AI!


## Getting ollama up and running
Installation process is shown for the Mac with homebrew. This should not be much more difficult on other OS.
It's assumed that you have homebrew on your Mac and you are able to install packages with it. 

### Install ollama with homebrew
```bash
brew install ollama
ollama --version
#get rid of it
brew uninstall ollama
```

### Run ollama as a service
```bash
brew services start ollama
#you can also stop it that way
brew services stop ollama
```

If you don't want to run it as a service, just start it manually 
```bash
ollama serve
#pull the model
#run the model
ollama pull mistral
```

### Pull a model for local usage (hopefully open source dude)
Out of souveranity, ecological and last but not least economical reasons, it's recommended to use a local model with at least free weights. 
Recommendation would be Mistral:latest because of the affore mentioned reasons. As ollama supports the ChatGPT API, it is easy to change to 
a larger model in the cloud. The limiting factor for local LLMs is mostly the hardware at hand. Anyway, for most agentic scenarios and for 
demonstration purposes fits Mistral quit well. Let's pull the model: 

```bash
ollama pull mistral
```

To see the list of models at hand: 

```bash
ollama list
```

## Get your dev environment (VS Code) ready
Hier ist eine detaillierte Schritt-für-Schritt-Anleitung, wie du Ollama mit Mistral in VS Code einrichtest, um Code-Generierung, Chat mit Code-Kontext und Autovervollständigung zu nutzen.
Da du bereits Ollama installiert und mistral:latest gepullt hast, gehen wir direkt zur Integration in VS Code über.

🛠️ Schritt 1: VS Code für Ollama + Mistral vorbereiten
1.1. VS Code-Erweiterungen installieren
Du brauchst zwei Erweiterungen, um Ollama mit Mistral in VS Code zu nutzen:
🔹 Erweiterung 1: Continue

Zweck: Bietet KI-Chat mit Code-Kontext (ähnlich wie Claude Code).
Installation:

Öffne VS Code.
Drücke Cmd+Shift+X (macOS) oder Ctrl+Shift+X (Windows/Linux), um den Erweiterungsmarketplace zu öffnen.
Suche nach "Continue" und installiere die Erweiterung von Continue Dev.

🔹 Erweiterung 2: Ollama (optional, für direkte Ollama-Integration)

Zweck: Ermöglicht direkte Interaktion mit Ollama (z. B. für schnelle Abfragen).
Installation:
Suche nach "Ollama" und installiere die Erweiterung von Jola Lye.

⚙️ Schritt 2: Continue für Ollama + Mistral konfigurieren
2.1. Continue öffnen und Modell auswählen

Klicke auf das Continue-Symbol in der VS Code-Seitenleiste (oder drücke Cmd+Shift+P / Ctrl+Shift+P und suche nach "Continue: Open").
Im Continue-Fenster (rechts in VS Code) klickst du auf das Zahnrad-Symbol (⚙️) → "Models".
Klicke auf "Add Model" und wähle "Ollama" aus.
Gib als Modellname mistral:latest ein (oder ein anderes lokal verfügbares Modell, z. B. llama3).

Hinweis: Falls mistral:latest nicht funktioniert, versuche mistral oder prüfe mit ollama list, welche Modelle verfügbar sind.

2.2. Ollama-Server starten (falls nicht automatisch)


Prüfe, ob Ollama läuft:
bash
Kopieren

ollama serve




Falls der Server nicht läuft, starte ihn manuell in einem Terminal.
Hinweis: Der Server läuft standardmäßig auf http://localhost:11434.


Prüfe die verfügbaren Modelle:
bash
Kopieren

ollama list




Sollte mistral:latest anzeigen.


💬 Schritt 3: KI-Chat mit Code-Kontext nutzen
3.1. Chat mit dem gesamten Projekt starten

Öffne dein Projekt in VS Code.
Klicke auf das Continue-Symbol in der Seitenleiste.
Wähle "New Chat" aus.
Stelle eine Frage wie:
text
Kopieren

Erkläre mir den Code in src/agent_smith/llm.py.



oder
text
Kopieren

Wie kann ich diese Funktion in src/agent_smith/llm.py optimieren?




Continue analysiert automatisch den Code-Kontext deines Projekts und gibt eine Antwort basierend auf Mistral.

3.2. Code direkt in der Datei generieren

Öffne eine Python-Datei (z. B. llm.py).
Setze den Cursor an die gewünschte Stelle.
Drücke Cmd+Shift+P / Ctrl+Shift+P und wähle "Continue: Generate Code".
Gib einen Prompt ein, z. B.:
text
Kopieren

Schreibe eine Unit-Test-Funktion für die Klasse LLM in dieser Datei.




Continue generiert den Code direkt in der Datei.


✨ Schritt 4: Autovervollständigung mit Mistral aktivieren
4.1. Continue für Inline-Vervollständigung einrichten

Öffne die Continue-Einstellungen:

Klicke auf das Continue-Symbol → ⚙️ (Zahnrad) → "Settings".

Aktiviere "Inline Code Completion":

Suche nach "Inline Completion" und schalte die Option ein.

Wähle als Modell für Inline-Vervollständigung mistral:latest aus.
4.2. Inline-Vervollständigung nutzen

Beginne in einer Datei zu tippen (z. B. in einer Python-Datei).
Continue zeigt automatisch Vervollständigungsvorschläge an, die auf Mistral basieren.
Drücke Tab, um den Vorschlag zu akzeptieren.

🔌 Schritt 5: Ollama-Erweiterung für direkte Abfragen (optional)
Falls du die Ollama-Erweiterung installiert hast, kannst du direkt mit Ollama interagieren:

Öffne die Befehlspalette (Cmd+Shift+P / Ctrl+Shift+P).
Suche nach "Ollama: Ask" und drücke Enter.
Gib deine Frage ein, z. B.:
text
Kopieren

Was ist der Unterschied zwischen Mistral und Llama?




Die Antwort wird direkt in VS Code angezeigt.


📌 Schritt 6: Fortgeschrittene Konfiguration
6.1. Custom Prompts für Continue
Du kannst benutzerdefinierte Prompts für Continue erstellen, um die KI-Anworten zu optimieren.

Öffne die Continue-Einstellungen (⚙️ → "Prompts").
Klicke auf "Add Prompt" und gib z. B. folgenden Prompt ein:
text
Kopieren

Du bist ein Python-Experte. Erkläre den folgenden Code zeilenweise und schlage Optimierungen vor:




Speichere den Prompt und wähle ihn im Chat aus.
6.2. Ollama-Modellparameter anpassen
Du kannst die Temperatur, Top-P, etc. für Mistral in Continue anpassen:

Öffne die Continue-Einstellungen (⚙️ → "Models").
Klicke auf das Stift-Symbol (✏️) neben mistral:latest.
Passe die Parameter an, z. B.:
json
Kopieren

{
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 2048
}

temperature: Kreativität (0.0 = deterministisch, 1.0 = zufällig).
top_p: Diversität der Antworten (0.9 = gut für Code).
max_tokens: Maximale Länge der Antwort.




$$\alpha = \frac{\mathbf{K}\;\mathbf{Q}}{\sqrt{S}}$$

This is text with math: $E=m \cdot c^2$