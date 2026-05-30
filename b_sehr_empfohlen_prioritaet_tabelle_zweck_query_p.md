## B. Sehr empfohlen

PrioritaetTabelleZweckQuery pro UserBearbeitung fuer MiroShark

P1`eve_hypothesis_events`Evidenz, Widerspruch, Erweiterung`user_id = activeUserId::text`, letzte 100Je Hypothese zusammenfassen: confirmations, contradictions, recalibrations, latest evidence.

P1`eve_sessions`Eve-Sitzungskontext`user_id = activeUserId::text`, letzte 20Nur Session-Summaries, Mode, Agent Type, keine Rohdialoge.

P1`agent_conversations`Levi/Eve Agent Memory`user_id = activeUserId`, letzte 10-20Nur `summary`, `topics`, `agent_type`, `created_at`. Keine Rohgespraeche.

P1`daily_horoscope_cache`bereits berechnete Daily Payloads`user_id = activeUserId`, letzte 1-7Nur Tages-/Archetypen-Zusammenfassung, keine vollen Payloads, falls gross.

P1`space_weather_cache`globaler Space-Weather-Kontextneuester globaler EintragNur verwenden, wenn nicht stale. Sonst `status: stale`, Gewicht niedrig.

P1`cosmic_weather_snapshots`kosmisches Wetter / Transiteneuester oder ZeitraumAls externes Feld, nicht user-spezifisch. Nur komprimierte Transit-/Weather-Signale.
