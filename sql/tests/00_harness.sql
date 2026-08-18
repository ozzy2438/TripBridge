-- Pipeline harness: result tables, helpers, and a new RUNNING test run.
-- Does not modify source extracts. Safe to re-run.

CREATE SCHEMA IF NOT EXISTS tripbridge;

CREATE TABLE IF NOT EXISTS tripbridge.pipeline_test_run (
    run_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    overall_status  text NOT NULL CHECK (overall_status IN ('RUNNING', 'PASS', 'FAIL')),
    passed_count    integer,
    failed_count    integer,
    notes           text
);

CREATE TABLE IF NOT EXISTS tripbridge.pipeline_test_result (
    run_id          uuid NOT NULL REFERENCES tripbridge.pipeline_test_run(run_id) ON DELETE CASCADE,
    stage           text NOT NULL,
    test_name       text NOT NULL,
    passed          boolean NOT NULL,
    expected_value  text,
    actual_value    text,
    detail          text,
    checked_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, stage, test_name)
);

CREATE INDEX IF NOT EXISTS pipeline_test_result_failed_idx
    ON tripbridge.pipeline_test_result (run_id)
    WHERE NOT passed;

CREATE OR REPLACE FUNCTION tripbridge.current_test_run_id()
RETURNS uuid
LANGUAGE sql
VOLATILE
AS $$
    SELECT run_id
    FROM tripbridge.pipeline_test_run
    WHERE overall_status = 'RUNNING'
    ORDER BY started_at DESC
    LIMIT 1
$$;

CREATE OR REPLACE FUNCTION tripbridge.record_test(
    p_stage text,
    p_test_name text,
    p_passed boolean,
    p_expected text DEFAULT NULL,
    p_actual text DEFAULT NULL,
    p_detail text DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO tripbridge.pipeline_test_result (
        run_id, stage, test_name, passed, expected_value, actual_value, detail
    )
    VALUES (
        tripbridge.current_test_run_id(),
        p_stage,
        p_test_name,
        p_passed,
        p_expected,
        p_actual,
        p_detail
    )
    ON CONFLICT (run_id, stage, test_name) DO UPDATE
    SET passed = EXCLUDED.passed,
        expected_value = EXCLUDED.expected_value,
        actual_value = EXCLUDED.actual_value,
        detail = EXCLUDED.detail,
        checked_at = now();
END;
$$;

CREATE OR REPLACE FUNCTION tripbridge.assert_eq(
    p_stage text,
    p_test_name text,
    p_expected bigint,
    p_actual bigint,
    p_detail text DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM tripbridge.record_test(
        p_stage,
        p_test_name,
        p_expected IS NOT DISTINCT FROM p_actual,
        p_expected::text,
        p_actual::text,
        p_detail
    );
END;
$$;

CREATE OR REPLACE FUNCTION tripbridge.assert_eq_numeric(
    p_stage text,
    p_test_name text,
    p_expected numeric,
    p_actual numeric,
    p_detail text DEFAULT NULL
) RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM tripbridge.record_test(
        p_stage,
        p_test_name,
        p_expected IS NOT DISTINCT FROM p_actual,
        p_expected::text,
        p_actual::text,
        p_detail
    );
END;
$$;

CREATE OR REPLACE VIEW tripbridge.v_pipeline_gate AS
SELECT
    r.run_id,
    r.started_at,
    r.finished_at,
    r.overall_status,
    r.passed_count,
    r.failed_count,
    r.notes,
    (r.overall_status = 'PASS') AS analytics_unblocked
FROM tripbridge.pipeline_test_run r
ORDER BY r.started_at DESC
LIMIT 1;

UPDATE tripbridge.pipeline_test_run
SET overall_status = 'FAIL',
    finished_at = COALESCE(finished_at, now()),
    notes = COALESCE(notes || ' ', '') || 'Superseded by a newer run.'
WHERE overall_status = 'RUNNING';

INSERT INTO tripbridge.pipeline_test_run (overall_status, notes)
VALUES ('RUNNING', 'Source-load gate after CSV extract load.');
