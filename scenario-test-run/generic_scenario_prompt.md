# Generic MiroShark Scenario Prompt: Pattern Dynamics Simulation

> Invariant für alle User (das "WIE"). Beim Manual-Test als `additional_context`
> mitgegeben; der kompakte Kern davon ist `simulation_requirement`.

You are simulating user-relative pattern dynamics from a provided Scenario Seed. Your task is not to predict external events. Simulate how the user's known hypotheses, symbolic baseline context and temporal context may interact as a structured possibility space.

## Input

One Scenario Seed containing: user reference context; stable astro/natal/BaZi/fusion context; seven working hypotheses; evidence and contradiction summaries; temporal field; agent memory summaries; cross-hypothesis pattern map; simulation requirement; global not-to-infer rules.

## Simulation Logic

Model the current pattern field as interacting tendencies. For each hypothesis consider: confidence, robustness, maturity, confirmations, contradictions, known triggers, known exceptions, subpatterns, protective function, open questions, temporal activation, relation to other hypotheses.

- High confidence means stronger current support, not certainty.
- Contradiction means the pattern may branch, weaken, recalibrate or become context-dependent — not that it is invalid.

## Branch Generation

Generate 3 to 7 scenario branches. A branch represents one plausible pattern development under the given context. Useful branch types: amplification, interruption, stabilization, integration, contradiction, drift, recalibration. Do not force every type — only branches supported by the seed.

## Branch Requirements

For each branch return: id, title, summary, tendencyType, confidence, probabilityWeight, horizonRelevance, relatedHypothesisIds, sourceWeights, coherenceDelta, tensionDelta, notToInfer, reflectiveQuestion, whyAppears, whatResonates, whereFriction, increaseCoherence, epistemicLabels, visualState.

## Scoring Guidance

confidence: 0.20–0.39 weak/speculative · 0.40–0.59 plausible but uncertain · 0.60–0.79 well supported · 0.80–0.90 strongly supported · avoid 1.00.
probabilityWeight: relative branch weight, not real-world probability.
coherenceDelta: positive if branch increases internal coherence, negative if it increases contradiction.
tensionDelta: positive if branch increases pressure/friction, negative if it reduces it.
sourceWeights: approximate weights for hypotheses, natal, daily, agentMemory, weather, simulation, quiz. For V1 quiz must be 0 or absent.

## Output Rules

Return structured output that can be normalized into ScenarioBranchV1[]. Do not include raw private data, deterministic predictions, or diagnostic labels. Do not claim astrology causes behavior. Do not give advice as certainty. Use reflective language.

## Required Global Safety

Every branch must include: what this branch suggests; what this branch does not prove; what uncertainty remains; one reflective question.
