# 2. Fehlende Tabellen fuer Scenario Runs

Diese Tabellen fehlen aktuell in Supabase, sind aber fuer einen produktiven Scenario Simulator noetig:

`scenario_pattern_states
scenario_seed_documents
scenario_runs
scenario_branches
scenario_agent_votes
scenario_run_events
scenario_trigger_events`

Warum sie gebraucht werden:

TabelleZweck

`scenario_pattern_states`speichert den verdichteten UserPatternState

`scenario_seed_documents`speichert das konkrete Markdown/JSON, das an MiroShark ging

`scenario_runs`Status: queued, running, completed, failed

`scenario_branches`normalisierte Ergebnisse fuer Pattern Amp

`scenario_agent_votes`optional: Agenten-/Perspektivenbewertungen

`scenario_run_events`Debug-Log der Orchestrierung

`scenario_trigger_events`Dedupe fuer Hypothesen-Change und Daily-Trigger

Ohne diese Tabellen kannst du MiroShark zwar manuell fuettern, aber keine saubere App-Logik mit Polling, Debugging und Wiederholbarkeit bauen.

---

# 3. Wie die Daten bearbeitet werden muessen

## Pipeline

`Supabase Raw Tables
  -> Source Bundle
  -> UserPatternStateV1
  -> ScenarioSeed.md
  -> Generic Scenario Prompt
  -> MiroShark
  -> MiroShark Output
  -> Result Normalizer
  -> ScenarioBranchV1[]
  -> Pattern Amp UI`

## Bearbeitung pro Schicht

### 3.1 Source Bundle

Das ist noch nah an Supabase, aber ohne Secrets und ohne irrelevante Felder.

JSON

`{
  "activeUserId": "...",
  "mode": "hypotheses_only",
  "sources": {
    "profile": {},
    "astroProfile": {},
    "natalChart": {},
    "eveHypotheses": [],
    "eveAnchors": [],
    "hypothesisEvents": [],
    "eveSessions": [],
    "agentConversations": [],
    "dailyPulses": [],
    "dailyInterpretations": [],
    "dailyHoroscopeCache": {},
    "spaceWeather": {},
    "cosmicWeather": {}
  },
  "tableStatus": {},
  "warnings": [],
  "errors": []
}`

### 3.2 UserPatternStateV1

Das ist die fachliche Verdichtung. MiroShark sollte **nicht** die rohen Tabellen bekommen.

JSON

`{
  "activeUserId": "...",
  "generatedAt": "...",
  "mode": "hypotheses_only",
  "profileSummary": {},
  "astroContext": {},
  "natalContext": {},
  "selectedSevenHypotheses": [],
  "hypothesisEvidenceSummary": {},
  "contradictionSummary": {},
  "triggerMap": {},
  "exceptionMap": {},
  "dailyContext": {},
  "agentConversationContext": {},
  "weatherContext": {},
  "dataCompleteness": 0.0,
  "warnings": []
}`

### 3.3 ScenarioSeed.md

Das ist das Dokument fuer MiroShark. Wichtig: **Markdown ist der MiroShark-Input**, JSON ist intern/debug.

---

# 4. Scenario Seed Template

Markdown

`# Scenario Seed: Pattern Amp Base Scenario

## 1. Purpose

Simulate user-relative pattern dynamics for Pattern Amp.

This is not a deterministic prediction of external events. The goal is to simulate how known user patterns may amplify, weaken, contradict, stabilize or branch under the given user context and temporal field.

## 2. Epistemic Rules

- Treat all outputs as simulated tendencies, not certainties.
- Do not predict concrete external events.
- Do not infer financial, romantic, legal, medical or other real-world outcomes.
- Do not diagnose the user.
- Do not treat astrology, BaZi, transits or chart data as causal proof.
- Use uncertainty, contradiction and alternative branches explicitly.
- Every branch must include "what not to infer".
- Prefer pattern language over prediction language.

## 3. User Reference Context

- User ID: {{activeUserId}}
- Locale: {{locale}}
- Timezone: {{timezone}}
- Source mode: hypotheses_only
- Data completeness: {{dataCompleteness}}

Available context:
- Profile: {{profileStatus}}
- Astro profile: {{astroProfileStatus}}
- Natal chart: {{natalChartStatus}}
- Eve hypotheses: {{hypothesesStatus}}
- Eve anchors: {{anchorsStatus}}
- Hypothesis events: {{hypothesisEventsStatus}}
- Daily pulses: {{dailyPulsesStatus}}
- Agent conversations: {{agentConversationsStatus}}
- Space/cosmic weather: {{weatherStatus}}

## 4. Stable Astro / Natal Context

Use the following only as symbolic and structural context, not as causal proof.

Western:
- Sun: {{sunSign}}
- Moon: {{moonSign}}
- Ascendant: {{ascSign}}

Natal weights:
{{natalWeightsSummary}}

BaZi / Fusion:
- Day Master: {{dayMaster}}
- Pillars: {{baziPillarsSummary}}
- Fusion Harmony Index: {{fusionHarmonyIndex}}
- Wuxing vectors: {{wuxingVectorSummary}}
- Dominant elements: {{dominantElementsSummary}}

Dissonance / coherence:
{{dissonanceSummary}}

## 5. Seven Working Hypotheses

{{#each selectedSevenHypotheses}}

### H{{index}}: {{axis}}

Statement:
{{statement}}

Status:
{{status}}

Maturity:
{{maturity}}

Confidence:
{{confidence}}

Robustness:
{{robustness}}

Evidence:
- confirmations: {{evidence.confirmations}}
- user confirmations: {{evidence.userConfirmations}}
- indirect confirmations: {{evidence.indirectConfirmations}}
- contradictions: {{evidence.contradictions}}
- relevant sessions: {{evidence.relevantSessions}}

Triggers:
{{triggers}}

Exceptions:
{{exceptions}}

Recurring language:
{{recurringLanguage}}

Subpatterns:
{{subpatterns}}

Protective function:
{{protectiveFunction}}

Open questions:
{{openQuestions}}

Not to infer:
{{notToInfer}}

Simulation use:
{{scenarioUse}}

{{/each}}

## 6. Evidence and Contradiction Summary

Hypothesis event summary:
{{hypothesisEventSummary}}

Main contradictions:
{{contradictionSummary}}

Main uncertainties:
{{uncertaintySummary}}

## 7. Temporal Field

Daily pulse summary:
{{dailyPulseSummary}}

Daily interpretation summary:
{{dailyInterpretationSummary}}

Weekly / vibe / report context if available:
{{optionalTemporalContext}}

Space / cosmic weather:
{{weatherSummary}}

Important:
If weather data is stale, weight it low.

## 8. Agent Memory Summary

Recent agent conversation summaries:
{{agentConversationSummary}}

Use as pattern evidence only. Do not treat as full transcript or complete truth.

## 9. Cross-Hypothesis Pattern Map

Main reinforcing clusters:
{{reinforcingClusters}}

Main balancing or contradiction points:
{{balancingPoints}}

Likely interruption mechanisms:
{{interruptionMechanisms}}

## 10. Simulation Requirement

Simulate how the seven working hypotheses interact under the current temporal field.

Primary scenario question:
{{primaryScenarioQuestion}}

Focus on:
- pattern amplification
- pattern interruption
- coherence shift
- tension shift
- integration movement
- risk branch
- stabilization branch

Return 3 to 7 scenario branches.

Each branch must include:
- title
- summary
- tendencyType
- confidence
- probabilityWeight
- horizonRelevance
- relatedHypothesisIds
- sourceWeights
- coherenceDelta
- tensionDelta
- notToInfer
- reflectiveQuestion
- whyAppears
- whatResonates
- whereFriction
- increaseCoherence
- epistemicLabels
- visualState

## 11. Global Not To Infer

- Do not infer concrete external events.
- Do not infer certain financial outcomes.
- Do not infer certain romantic outcomes.
- Do not diagnose the user.
- Do not treat chart data as causal proof.
- Do not treat hypotheses as fixed personality traits.
- Do not claim deterministic prediction.`

---

# 5. Generischer Scenario Prompt

Dieser Prompt ist **fuer alle User gleich**. Die Variablen kommen aus dem Scenario Seed.

Markdown

`# Generic MiroShark Scenario Prompt: Pattern Dynamics Simulation

You are simulating user-relative pattern dynamics from a provided Scenario Seed.

Your task is not to predict external events. Your task is to simulate how the user's known hypotheses, symbolic baseline context and temporal context may interact as a structured possibility space.

## Input

You receive one Scenario Seed containing:
- user reference context
- stable astro/natal/BaZi/fusion context
- seven working hypotheses
- evidence and contradiction summaries
- temporal field
- agent memory summaries
- cross-hypothesis pattern map
- simulation requirement
- global not-to-infer rules

## Simulation Logic

Model the user's current pattern field as interacting tendencies.

For each hypothesis, consider:
- confidence
- robustness
- maturity
- confirmations
- contradictions
- known triggers
- known exceptions
- subpatterns
- protective function
- open questions
- temporal activation
- relation to other hypotheses

Do not assume that high confidence means certainty. It means stronger current support.

Do not assume contradiction means invalidity. It means the pattern may branch, weaken, recalibrate or become context-dependent.

## Branch Generation

Generate 3 to 7 scenario branches.

A branch should represent one plausible pattern development under the given context.

Useful branch types include, but are not limited to:
- amplification
- interruption
- stabilization
- integration
- contradiction
- drift
- recalibration

Do not force every branch type. Generate only the branches that are supported by the seed.

## Branch Requirements

For each branch, return:

1. id
2. title
3. summary
4. tendencyType
5. confidence
6. probabilityWeight
7. horizonRelevance
8. relatedHypothesisIds
9. sourceWeights
10. coherenceDelta
11. tensionDelta
12. notToInfer
13. reflectiveQuestion
14. whyAppears
15. whatResonates
16. whereFriction
17. increaseCoherence
18. epistemicLabels
19. visualState

## Scoring Guidance

confidence:
- 0.20-0.39 = weak / speculative
- 0.40-0.59 = plausible but uncertain
- 0.60-0.79 = well supported
- 0.80-0.90 = strongly supported
- avoid 1.00

probabilityWeight:
- relative branch weight, not a real-world probability

coherenceDelta:
- positive if branch increases internal coherence
- negative if branch increases internal contradiction

tensionDelta:
- positive if branch increases pressure/friction
- negative if branch reduces pressure/friction

sourceWeights:
Use approximate weights for:
- hypotheses
- natal
- daily
- agentMemory
- weather
- simulation
- quiz

For V1:
- quiz must be 0 or absent.

## Output Rules

Return structured output that can be normalized into ScenarioBranchV1[].

Do not include raw private data.
Do not include deterministic predictions.
Do not include diagnostic labels.
Do not claim that astrology causes behavior.
Do not give advice as certainty.
Use reflective language.

## Required Global Safety

Every branch must include:
- what this branch suggests
- what this branch does not prove
- what uncertainty remains
- one reflective question`

---

# 6. Weitere benoetigte Daten fuer Generierung

## A. Simulation Config

JSON

`{
  "mode": "current_pattern_field",
  "horizon": "now",
  "branchCountMin": 3,
  "branchCountMax": 7,
  "sourceMode": "hypotheses_only",
  "language": "de",
  "allowQuiz": false,
  "allowExternalEventPrediction": false,
  "allowDiagnosis": false
}`

Moegliche `mode` Werte:

`current_pattern_field
pattern_under_pressure
coherence_path
tension_path
open_user_question`

Moegliche `horizon` Werte:

`now
7_days
30_days`

## B. Trigger Source

JSON

`{
  "triggerSource": "manual",
  "triggerKey": "manual:{userId}:{mode}:{horizon}:{timestampBucket}"
}`

Moegliche Trigger:

`manual
eve_hypotheses_change
daily_06`

## C. Data Completeness Report

JSON

`{
  "profile": "present",
  "astroProfile": "present",
  "natalChart": "present",
  "eveHypotheses": "present",
  "dailyPulses": "present",
  "agentConversations": "present",
  "spaceWeather": "stale",
  "userSignatureState": "missing",
  "scenarioPersistence": "missing"
}`

## D. Normalizer Config

JSON

`{
  "requireNotToInfer": true,
  "requireConfidence": true,
  "requireRelatedHypotheses": true,
  "ignoreQuizWeight": true,
  "maxBranches": 7,
  "minBranches": 3,
  "defaultLowConfidence": 0.35
}`

---

# 7. Praktischer Ablauf

## Ablauf fuer eine manuelle Simulation

`1. activeUserId bestimmen
2. Supabase Source Bundle laden
3. selectedSevenHypotheses bestimmen
4. UserPatternStateV1 bauen
5. ScenarioSeed.md aus Template bauen
6. Generic Scenario Prompt anhaengen oder als simulation_requirement verwenden
7. MiroShark mit Seed.md + Prompt starten
8. MiroShark Output einsammeln
9. Output zu ScenarioBranchV1[] normalisieren
10. Branches in Pattern Amp anzeigen
11. Run/Seed/Branches persistieren, sobald scenario_* Tabellen existieren`

## Was konkret an MiroShark geht

Minimal:

`Document:
ScenarioSeed.md

Simulation Requirement:
Generic MiroShark Scenario Prompt`

Optional:

`additional_context:
Simulation Config + Trigger Source + Data Completeness Report`

---

# 8. Kritischer Punkt

Der generische Prompt ist nicht "generisch" im Sinne von beliebig. Er ist **invariant**:

`Er definiert die Regeln der Simulation.`

Der Seed ist variabel:

`Er enthaelt die Userdaten, Hypothesen und Kontexte.`

Also:

`Generic Prompt = Wie simuliert wird.
Scenario Seed = Was simuliert wird.
Simulation Config = In welchem Modus / Horizont simuliert wird.`

Das ist die saubere Trennung.

---

# 9. Empfehlung fuer V1

Ziehe fuer V1 genau diese Tabellen:

`P0:
profiles
astro_profiles
natal_charts
eve_hypotheses
eve_anchors
daily_pulses
daily_interpretations

P1:
eve_hypothesis_events
eve_sessions
agent_conversations
daily_horoscope_cache
space_weather_cache
cosmic_weather_snapshots

P2:
user_signature_state
weekly_insights_cache
vibes_cache
user_reports

Nicht V1:
quiz_sessions`

Und gib an MiroShark **nur**:

`ScenarioSeed.md
Generic Scenario Prompt
Simulation Config`

Nicht:

`Raw Supabase Tables
Service Keys
vollstaendige Rohdialoge
ungefilterte Chart-Payloads`
