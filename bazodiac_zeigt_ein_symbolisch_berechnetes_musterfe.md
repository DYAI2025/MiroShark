**Bazodiac zeigt ein symbolisch berechnetes Musterfeld. MiroShark simuliert daraus moegliche Entwicklungsrichtungen. Pattern Amp macht diese Richtungen sichtbar und bearbeitbar.**

Also nicht:

`Wir sagen dir dein Schicksal.`

Sondern:

`Wir zeigen dir, welche Muster in deinem aktuellen Feld wahrscheinlich staerker, schwaecher, widerspruechlicher oder integrierbarer werden koennten.`

"Enabling Your Destiny" kann als Brand-Satz funktionieren, aber intern muss klar sein:

`Destiny = reflektiver Moeglichkeitsraum
nicht = objektiv vorherbestimmte Zukunft`

---

# Exakte Funktionslogik im Bazodiac-Kontext

## 1. Supabase liefert die individuelle Musterbasis

Aus Supabase kommen pro User:

`profiles
astro_profiles
natal_charts
eve_hypotheses
eve_anchors
eve_hypothesis_events
eve_sessions
agent_conversations
daily_pulses
daily_interpretations
daily_horoscope_cache
space_weather_cache
cosmic_weather_snapshots`

Diese Tabellen sind als relevante Quellen vorhanden. `scenario_*` Persistenztabellen fehlen aktuell noch.

Die **wichtigste V1-Quelle** sind die sieben `eve_hypotheses`, weil sie konkrete Musterannahmen enthalten: Trigger, Ausnahmen, Confidence, Robustness, Contradictions, Subpatterns, Schutzfunktion und offene Fragen.

---

## 2. Bazodiac baut daraus keinen Rohdaten-Dump, sondern einen Scenario Seed

Bazodiac ist in dieser Architektur die **Orchestrierungsschicht**:

`Supabase
  -> Source Bundle
  -> UserPatternStateV1
  -> ScenarioSeed.md
  -> Generic Scenario Prompt
  -> MiroShark`

MiroShark bekommt also nicht:

`Alle Tabellen roh`

Sondern:

`ScenarioSeed.md + generischer Simulation Prompt + Config`

Das ist wichtig, weil sonst MiroShark aus zu vielen ungewichteten Daten irgendetwas plausibel Klingendes baut.

---

## 3. MiroShark simuliert keine Zukunft, sondern Musterentwicklung

Die Simulation fragt nicht:

`Was passiert Ben?`

Sondern:

`Wie entwickeln sich bekannte Muster unter aktuellen Bedingungen?`

MiroShark sollte also modellieren:

`Hypothese A wird durch Trigger X aktiviert.
Hypothese B widerspricht teilweise.
Daily Pulse erhoeht Spannung.
Natal-/Fusion-Kontext gibt symbolischen Strukturrahmen.
Daraus entstehen mehrere Branches.`

Beispiel:

`H1 Agency unter Druck
+ H3 Kontrolle durch Verstehen
+ Daily Pulse "trace / Entscheidung / nicht verschieben"
= Branch: Notfallmodus verstaerkt Fokus, aber Spannung steigt.`

Oder:

`H3 Unsicherheit
+ H7 direkte Authentizitaet
+ konkrete Handlung als Unterbrecher
= Branch: Analyse kippt nicht in Schleife, sondern wird in Handlung uebersetzt.`

---

# Produktformel

Die sauberste Produktformel waere:

`Chart = symbolische Basiskonfiguration
Hypothesen = erkannte User-Muster
Daily/Cosmic Field = aktuelle Modulation
MiroShark = Simulationsmaschine fuer Musterverzweigung
Pattern Amp = visuelle Bedienoberflaeche fuer Moeglichkeitsraeume`

Oder kuerzer:

`Bazodiac berechnet das Feld.
MiroShark simuliert die Dynamik.
Pattern Amp macht die Branches sichtbar.
Der User entscheidet, was er daraus macht.`

---

# "Enabling Your Destiny" sauber formuliert

## Riskant

`Wir zeigen dir dein beeinflussbares Schicksal.`

Problem: Das klingt nach objektiver Schicksalskenntnis.

## Besser

`Enable Your Destiny:
See the patterns shaping your possible paths - and where your choices can shift them.`

Deutsch:

`Erkenne die Muster, die deine moeglichen Wege praegen - und wo deine Entscheidungen sie veraendern koennen.`

Oder etwas klarer:

`Bazodiac zeigt keine festgelegte Zukunft. Es zeigt Muster, Tendenzen und Entscheidungspunkte, an denen dein naechster Schritt Gewicht bekommt.`

---

# Generischer Prompt: warum er gleich bleibt

Der generische Prompt ist gleich, weil er nicht den User beschreibt. Er beschreibt die **Regeln der Simulation**.

Er sagt MiroShark:

`Simuliere Musterentwicklung.
Nutze Hypothesen, Trigger, Ausnahmen, Confidence und Kontext.
Erzeuge 3-7 Branches.
Keine deterministische Zukunft.
Keine Diagnose.
Jede Branch braucht Confidence, Tension, Coherence, Not-to-Infer.`

Was sich pro User aendert, ist der **Scenario Seed**:

`User A hat andere Hypothesen.
User A hat andere Charts.
User A hat andere Daily Pulses.
User A hat andere Agent Summaries.`

Also:

`Generic Prompt = Wie simuliert wird.
Scenario Seed = Was simuliert wird.
Pattern Amp = Wie es sichtbar wird.`

---

# Konkreter Simulationsablauf

`1. User oder Trigger startet Scenario Run.

2. Bazodiac laedt aus Supabase:
   - Profile
   - Astro Profile
   - Natal Chart
   - 7 Eve Hypotheses
   - Eve Anchors
   - Hypothesis Events
   - Daily Pulses
   - Agent Summaries
   - Space/Cosmic Weather

3. Bazodiac baut UserPatternStateV1:
   - stabile Baseline
   - sieben Musterachsen
   - Trigger Map
   - Exception Map
   - Evidence/Contradiction Summary
   - Daily/Temporal Context
   - Data Completeness

4. Bazodiac baut ScenarioSeed.md:
   - User-Kontext
   - Chart-Kontext
   - sieben Hypothesen
   - zeitliche Modulation
   - Simulationsfrage
   - Output Contract
   - globale Nicht-Inferenzen

5. Bazodiac sendet an MiroShark:
   - ScenarioSeed.md
   - Generic Scenario Prompt
   - Simulation Config

6. MiroShark simuliert:
   - Pattern Amplification
   - Pattern Interruption
   - Integration
   - Drift
   - Stabilization
   - Contradiction/Recalibration

7. Bazodiac normalisiert MiroShark Output:
   - ScenarioBranchV1[]

8. Pattern Amp zeigt:
   - Branches
   - Confidence
   - Source Weights
   - Coherence/Tension Delta
   - Related Hypotheses
   - Not-to-Infer
   - Reflective Question`

---

# Wichtige Grenze

Ihr koennt es als **Destiny Product** framen, aber die Mechanik muss intern so bleiben:

`Destiny ist kein vorherbestimmtes Ergebnis.
Destiny ist ein Musterraum, der durch Wahrnehmung, Entscheidung und Handlung beeinflussbar wird.`
