-- Compatibility migration for source_health schema evolution.
-- Older local deployments used last_success_at / last_failure_at while the
-- current runtime persists observed_at / recorded_at. Keep old columns intact
-- for backward compatibility and add the canonical columns deterministically.

ALTER TABLE source_health
    ADD COLUMN IF NOT EXISTS observed_at TIMESTAMPTZ;

ALTER TABLE source_health
    ADD COLUMN IF NOT EXISTS recorded_at TIMESTAMPTZ;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'source_health'
          AND column_name = 'last_success_at'
    ) THEN
        UPDATE source_health
        SET observed_at = COALESCE(
                observed_at,
                last_success_at,
                last_failure_at,
                NOW()
            ),
            recorded_at = COALESCE(
                recorded_at,
                last_success_at,
                last_failure_at,
                NOW()
            )
        WHERE observed_at IS NULL
           OR recorded_at IS NULL;
    ELSE
        UPDATE source_health
        SET observed_at = COALESCE(observed_at, NOW()),
            recorded_at = COALESCE(recorded_at, NOW())
        WHERE observed_at IS NULL
           OR recorded_at IS NULL;
    END IF;
END
$$;

ALTER TABLE source_health
    ALTER COLUMN observed_at SET DEFAULT NOW();

ALTER TABLE source_health
    ALTER COLUMN recorded_at SET DEFAULT NOW();

ALTER TABLE source_health
    ALTER COLUMN observed_at SET NOT NULL;

ALTER TABLE source_health
    ALTER COLUMN recorded_at SET NOT NULL;
