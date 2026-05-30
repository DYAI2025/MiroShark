{
  "schema": "ScenarioSeedV1",
  "sourceMode": "hypotheses_only",
  "activeUserId": "1ac41a3d-4df9-4953-9df5-b65829b25205",
  "profile": {
    "emailReference": "ben.poersch@dyai.app",
    "locale": "de",
    "timezone": "Europe/Berlin",
    "tier": "premium"
  },
  "dataCompleteness": {
    "profile": "present",
    "birthDataTable": "missing",
    "astroProfile": "present",
    "natalChart": "present",
    "manualHypotheses": "present",
    "dailyPulses": "present",
    "agentConversations": "present",
    "userSignatureState": "missing",
    "spaceWeather": "present_but_stale"
  },
  "astroContext": {
    "sunSign": "Cancer",
    "moonSign": "Scorpio",
    "ascSign": "Libra",
    "natalWeights": {
      "Sun": 0.5125,
      "Moon": 0.382,
      "Mercury": 0.34175,
      "Venus": 0.5545,
      "Mars": 0.58175,
      "Jupiter": 0.56025,
      "Saturn": 0.4205
    },
    "dissonanceSnapshot": {
      "dNatal": 0.17809585959495858,
      "intensity": 0.07123834383798343,
      "elemental": "neutral"
    },
    "natalChart": {
      "zodiac": "tropical",
      "houseSystem": "placidus",
      "engineVersion": "bafe-1.0",
      "payloadKeys": ["tst", "bazi", "fusion", "issues", "wuxing", "western"]
    },
    "baziFusionSummary": {
      "dayMaster": "Wu",
      "zodiacSign": "Monkey",
      "fusionHarmonyIndex": 0.6379,
      "westernDominantElement": "Wood",
      "easternDominantElement": "Metal"
    }
  },
  "temporalContext": {
    "latestDailyPulseMode": "trace",
    "latestHarmonyIndex": 0.6379,
    "recurringDailyThemes": [
      "fear-based postponement",
      "decision hesitation",
      "thoughts circling before action",
      "one concrete step without certainty",
      "self/other knowledge",
      "focus instead of distraction",
      "beginning without permission"
    ],
    "spaceWeather": {
      "source": "DONKI",
      "status": "stale",
      "fetchedAt": "2026-04-17T20:33:30.292+00:00"
    }
  },
  "agentMemorySummary": [
    "Day pulse and BaZi pillars: Wu Earth and Monkey mobility.",
    "Conscious Cancer-shell retreat to stop external pressure.",
    "Emotional emptiness and numbness; analysis stopped to reduce pressure.",
    "Tension between safety need and freedom need.",
    "Control in love reflected as an illusion."
  ],
  "hypotheses": [
    {
      "id": "H1",
      "axis": "Agency / Antrieb",
      "statement": "Wenn existenzieller Druck, finanzielle Unsicherheit oder die Notwendigkeit, ein Projekt funktionsfaehig zu machen, aktiv ist, tendiert der User zu hoher Tatkraft und kompromisslosem Fokus.",
      "confidence": 0.68,
      "robustness": 0.55,
      "relatedPatterns": ["notfallmodus", "agency under pressure", "project focus"]
    },
    {
      "id": "H2",
      "axis": "Bindung / Naehe / Distanz",
      "statement": "Wenn emotionale Leere, Einsamkeit oder Unsicherheit in Beziehungen spuerbar wird, tendiert der User dazu, Naehe ueber Zielklarheit, Funktionalitaet oder Rueckzug zu regulieren.",
      "confidence": 0.42,
      "robustness": 0.32,
      "relatedPatterns": ["distance regulation", "safe closeness", "emotional protection"]
    },
    {
      "id": "H3",
      "axis": "Kontrolle / Unsicherheit",
      "statement": "Wenn Unsicherheit steigt, tendiert der User zu Klarheitssuche, Austausch und Kontrolle durch Verstehen.",
      "confidence": 0.72,
      "robustness": 0.58,
      "relatedPatterns": ["analysis", "clarification", "control loop"]
    },
    {
      "id": "H4",
      "axis": "Kommunikation / Ausdruck",
      "statement": "Wenn etwas Unausgesprochenes, Unklares oder potenziell Unwahres im Raum steht, tendiert der User dazu, es direkt auszusprechen.",
      "confidence": 0.7,
      "robustness": 0.56,
      "relatedPatterns": ["directness", "truth pressure", "de-escalating clarity"]
    },
    {
      "id": "H5",
      "axis": "Kohaerenz / Selbstbild",
      "statement": "Wenn der User merkt, dass er sich ablenkt, verdraengt oder gegen seine eigene innere Wahrheit handelt, entsteht ein Gefuehl von Unstimmigkeit.",
      "confidence": 0.61,
      "robustness": 0.46,
      "relatedPatterns": ["coherence", "self-honesty", "values alignment"]
    },
    {
      "id": "H6",
      "axis": "Schutz / Rueckzug / Abwehr",
      "statement": "Wenn Langeweile, Gleichtoenigkeit oder innere Leere auftaucht, tendiert der User dazu, sich durch Aktion, Intensitaet oder Fokus zu schuetzen.",
      "confidence": 0.66,
      "robustness": 0.52,
      "relatedPatterns": ["intensity", "emptiness regulation", "impact seeking"]
    },
    {
      "id": "H7",
      "axis": "Entwicklung / Integration",
      "statement": "Wenn der User Entwicklung sucht, entsteht eine Bewegung von indirekter Steuerung, Manipulation oder strategischer Kontrolle hin zu direkter Authentizitaet.",
      "confidence": 0.64,
      "robustness": 0.5,
      "relatedPatterns": ["authenticity", "integration", "direct agency"]
    }
  ],
  "simulationRequirement": {
    "primaryQuestion": "How may the user's current pattern field branch when existential/project pressure, uncertainty, emotional emptiness and the need for authenticity are simultaneously active?",
    "requestedBranches": [
      "amplification",
      "interruption",
      "relationship_contact",
      "coherence",
      "integration",
      "risk",
      "stabilization"
    ],
    "outputCount": "3_to_7"
  },
  "globalNotToInfer": [
    "No concrete external event prediction.",
    "No financial outcome prediction.",
    "No romantic outcome prediction.",
    "No diagnosis.",
    "No deterministic future language.",
    "No astrology-as-causality claim."
  ]
}
