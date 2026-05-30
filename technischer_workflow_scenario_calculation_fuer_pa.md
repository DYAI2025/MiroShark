## Technischer Workflow: Scenario Calculation fuer Pattern Amp

Der Kern ist:

`Supabase-Daten
  -> Pattern State
  -> Scenario Seed
  -> Generic Simulation Prompt
  -> MiroShark Simulation
  -> Scenario Branches
  -> Pattern Amp Visualisierung`

Ziel ist **keine objektive Zukunftsvorhersage**, sondern eine Simulation von Musterdynamiken: Was verstaerkt sich, was kann kippen, wo entstehen Spannungen, wo liegen beeinflussbare Entscheidungspunkte?

---

# 1. Trigger: Wann wird ein Szenario berechnet?

Ein Scenario Run kann durch drei Ausloeser entstehen:

`manual
  User klickt im Pattern Amp auf "Run Scenario"

eve_hypotheses_change
  Eine der sieben Hypothesen wird geaendert, bestaetigt, widersprochen oder neu gewichtet

daily_06
  Automatischer Tageslauf morgens um 06:00 Uhr`

Wichtig: Jeder Trigger braucht einen `trigger_key`, damit nicht versehentlich mehrere gleiche Runs erzeugt werden.

---

# 2. Daten laden: Was kommt aus Supabase?

Bazodiac oder das Pattern-Amp-Backend laedt die relevanten Daten serverseitig.

## Pflichtdaten

`profiles
astro_profiles
natal_charts
eve_hypotheses
eve_anchors
daily_pulses
daily_interpretations`

## Empfohlene Kontextdaten

`eve_hypothesis_events
eve_sessions
agent_conversations
daily_horoscope_cache
space_weather_cache
cosmic_weather_snapshots
user_signature_state`

Diese Tabellen sind in Supabase vorhanden; `scenario_*` Persistenz-Tabellen wurden in der letzten Abfrage nicht gefunden.

Die wichtigste V1-Quelle ist `eve_hypotheses`, weil dort Muster, Confidence, Trigger, Ausnahmen, Gegenevidenz, Subpatterns und Schutzfunktion liegen.

---

# 3. Verdichtung: Aus Rohdaten wird ein Pattern State

Die Rohdaten gehen **nicht direkt** an MiroShark.

Stattdessen wird daraus ein `UserPatternStateV1` gebaut:

`UserPatternStateV1
  - User-Kontext
  - Astro-/Natal-/BaZi-/Fusion-Kontext
  - sieben aktive Hypothesen
  - Trigger Map
  - Exception Map
  - Evidence Summary
  - Contradiction Summary
  - Daily Context
  - Agent Memory Summary
  - Data Completeness
  - Warnings`

Der Pattern State beantwortet:

`Welche Muster sind beim User aktuell plausibel?
Wie gut sind sie belegt?
Was aktiviert sie?
Was unterbricht sie?
Welche aktuellen Tages-/Kontextsignale modulieren sie?`

---

# 4. Scenario Seed: MiroShark-kompatibles Input-Dokument

Aus dem Pattern State wird ein `ScenarioSeed.md` gebaut.

Das ist das eigentliche Dokument fuer MiroShark.

Es enthaelt:

`1. Purpose
2. Epistemic Rules
3. User Reference Context
4. Astro / Natal / BaZi / Fusion Context
5. Seven Working Hypotheses
6. Evidence and Contradiction Summary
7. Temporal Field
8. Agent Memory Summary
9. Cross-Hypothesis Pattern Map
10. Simulation Requirement
11. Global Not To Infer`

Der Seed sagt also: **Was wird simuliert?**

---

# 5. Generic Scenario Prompt: Die Regeln der Simulation

Der generische Prompt ist fuer alle User gleich.

Er sagt MiroShark: **Wie soll simuliert werden?**

Beispielhaft:

`Simulate user-relative pattern dynamics from the provided Scenario Seed.

Do not predict external events.
Do not diagnose the user.
Do not treat astrology as causal proof.

Generate 3 to 7 scenario branches.
Each branch must include:
- title
- summary
- tendencyType
- confidence
- relatedHypothesisIds
- sourceWeights
- coherenceDelta
- tensionDelta
- notToInfer
- reflectiveQuestion
- epistemicLabels`

Der Seed ist individuell.

Der generische Prompt ist invariant.

---

# 6. MiroShark Simulation

MiroShark bekommt:

`ScenarioSeed.md
Generic Scenario Prompt
Simulation Config`

Die Simulation soll nicht fragen:

`Was passiert dem User?`

Sondern:

`Wie koennen sich die erkannten Muster unter aktuellen Bedingungen verzweigen?`

MiroShark simuliert idealerweise:

`Pattern Amplification
Pattern Interruption
Coherence Shift
Tension Shift
Integration
Drift
Recalibration
Stabilization`

Beispiel:

`H1 Agency unter Druck
+ H3 Kontrolle durch Verstehen
+ Daily Pulse "nicht verschieben"
= Branch: Fokus steigt, Spannung steigt ebenfalls.`

Oder:

`H3 Unsicherheit
+ H7 direkte Authentizitaet
+ konkrete naechste Handlung
= Branch: Analyse wird in Handlung uebersetzt.`

---

# 7. Normalisierung: MiroShark Output wird Pattern-Amp-Format

MiroShark liefert wahrscheinlich keinen direkt renderbaren Pattern-Amp-Output. Deshalb braucht Bazodiac einen Normalizer.

Der Normalizer erzeugt:

`ScenarioBranchV1[]`

Jede Branch enthaelt:

`id
title
summary
tendencyType
confidence
probabilityWeight
horizonRelevance
relatedHypothesisIds
sourceWeights
coherenceDelta
tensionDelta
notToInfer
reflectiveQuestion
whyAppears
whatResonates
whereFriction
increaseCoherence
epistemicLabels
visualState`

Das ist der eigentliche Output, den Pattern Amp anzeigen kann.

---

# 8. Persistenz: Was gespeichert werden sollte

Fuer ein echtes Produkt braucht ihr diese Tabellen:

`scenario_pattern_states
scenario_seed_documents
scenario_runs
scenario_branches
scenario_agent_votes
scenario_run_events
scenario_trigger_events`

Nutzen:

`scenario_pattern_states
  speichert den verdichteten Musterzustand

scenario_seed_documents
  speichert den konkreten Seed, der an MiroShark ging

scenario_runs
  speichert Status, Modus, Trigger, Fehler, MiroShark IDs

scenario_branches
  speichert die normalisierten Ergebnis-Branches

scenario_run_events
  speichert Debug- und Lifecycle-Events

scenario_trigger_events
  verhindert doppelte Runs`

Aktuell fehlen diese Tabellen nach der letzten DB-Abfrage noch.

---

# 9. Frontend: Was der User sieht

Pattern Amp zeigt keine Rohdaten und keine "Schicksalsantwort".

Es zeigt:

`- aktive Musterhypothesen
- Branches / Moeglichkeitsrichtungen
- Confidence
- Source Weights
- Coherence Delta
- Tension Delta
- Related Hypotheses
- Not To Infer
- reflektive Fragen
- Datenherkunft / Provenance`

Visuell kann das als Graph, Branch-Fan oder Musterfeld erscheinen.

---

# 10. Outcome

Ein Scenario Run erzeugt:

`3 bis 7 Scenario Branches`

Beispielhafte Branches:

`1. Emergency Focus Amplification
   Druck steigt, Fokus steigt, Spannung steigt ebenfalls.

2. Concrete Step Interruption
   Ein kleiner naechster Schritt reduziert Kontrollschleifen.

3. Safe Contact Branch
   Naehe wird nicht ueber Rueckzug, sondern ueber klare Kommunikation reguliert.

4. Coherence Recalibration
   Der User unterscheidet Pause von Vermeidung.

5. Integration Branch
   Direkte Authentizitaet ersetzt indirekte Kontrolle.`

Jede Branch sagt nicht: "Das wird passieren."

Sie sagt: "Das ist eine plausible Musterrichtung unter den gegebenen Bedingungen."

---

# 11. Nutzerwert

## A. Selbstverstaendnis

Der User sieht nicht nur ein Horoskop, sondern:

`Welche Muster laufen gerade?
Warum laufen sie?
Was verstaerkt sie?
Was unterbricht sie?`

## B. Entscheidungsorientierung

Der User erkennt konkrete Hebelpunkte:

`Was ist jetzt der kleinste Schritt?
Wo wird Druck zu Fokus?
Wo wird Fokus zu Verengung?
Wo hilft Klarheit?
Wo braucht es Rueckzug?`

## C. Beeinflussbarkeit

Das Produktversprechen ist nicht:

`Wir sagen dir dein Schicksal.`

Sondern:

`Wir zeigen dir Muster, an denen dein naechster Schritt Gewicht bekommt.`

Das ist die saubere Bedeutung von **Enabling Your Destiny**:

`Nicht Zukunft festlegen.
Sondern Muster sichtbar und beeinflussbar machen.`

## D. Wiederkehrender Nutzen

Daily oder bei Hypothesen-Aenderung kann ein neuer Run entstehen:

`Heute sieht dein Musterfeld anders aus.
Nicht weil dein Schicksal anders ist,
sondern weil Kontext, Trigger und Mustergewichtung anders sind.`

Das kann Retention erzeugen, ohne in platte Wahrsagerei abzurutschen
