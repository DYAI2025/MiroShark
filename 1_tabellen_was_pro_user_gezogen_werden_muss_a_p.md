# 1. Tabellen: Was pro User gezogen werden muss

## A. Pflicht fuer jedes Base Scenario

PrioritaetTabelleZweckQuery pro UserBearbeitung fuer MiroShark

P0`profiles`User-Kontext, Sprache, Zeitzone, Tier`id = activeUserId`Nur kompaktes Profil: `locale`, `timezone`, `tier`, optional `display_name`. Keine Zahlungsdaten.

P0`astro_profiles`verdichteter Astro-Kontext`user_id = activeUserId`Komprimieren auf Sun/Moon/Asc, Natal Weights, Soulprint, Dissonance Snapshot, Agent Summary.

P0`natal_charts`Natal-, BaZi-, Fusion-, Wuxing-Basis`user_id = activeUserId`, neuester ChartNicht roh dumpen. Extrahiere: `zodiac`, `house_system`, `engine_version`, BaZi pillars, Day Master, Fusion harmony, Wuxing vectors.

P0`eve_hypotheses`sieben primaere Musterhypothesen`user_id = activeUserId::text`Auswahl/Ranking: `active`, Confidence, Robustness, Updated At. Voll strukturiert in Seed aufnehmen.

P0`eve_anchors`Musterachsen/Anker`user_id = activeUserId::text`Anker mit Hypothesen verbinden. Keine losen Hypothesen ohne Achse.

P0`daily_pulses`aktuelles Tagesfeld`user_id = activeUserId`, letzte 7-14Verdichten auf Mode, Intensity, Harmony Index, wiederkehrende Slots/Themen.

P0`daily_interpretations`Textdeutung zu Daily Pulses`daily_pulse_id in latestPulseIds`Nur Summary/Themen extrahieren, nicht alle Texte roh weitergeben.
