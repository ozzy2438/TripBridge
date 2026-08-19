-- Stage: PASS / FAIL gate
-- Closes the current run. Downstream analytics should read
-- tripbridge.v_pipeline_gate.analytics_unblocked = true.

UPDATE tripbridge.pipeline_test_run r
SET finished_at = now(),
    passed_count = s.passed_count,
    failed_count = s.failed_count,
    overall_status = CASE WHEN s.failed_count = 0 THEN 'PASS' ELSE 'FAIL' END,
    notes = CASE
        WHEN s.failed_count = 0 THEN 'Source-load gate passed. Analytics may proceed.'
        ELSE format('Source-load gate failed: %s test(s) failed.', s.failed_count)
    END
FROM (
    SELECT
        COUNT(*) FILTER (WHERE passed) AS passed_count,
        COUNT(*) FILTER (WHERE NOT passed) AS failed_count
    FROM tripbridge.pipeline_test_result
    WHERE run_id = tripbridge.current_test_run_id()
) s
WHERE r.run_id = tripbridge.current_test_run_id();

SELECT
    run_id,
    overall_status,
    passed_count,
    failed_count,
    started_at,
    finished_at,
    notes
FROM tripbridge.v_pipeline_gate;

SELECT
    stage,
    test_name,
    expected_value,
    actual_value,
    detail
FROM tripbridge.pipeline_test_result
WHERE run_id = (SELECT run_id FROM tripbridge.v_pipeline_gate)
  AND NOT passed
ORDER BY stage, test_name;

DO $$
DECLARE
    v_status text;
    v_failed integer;
BEGIN
    SELECT overall_status, failed_count
    INTO v_status, v_failed
    FROM tripbridge.v_pipeline_gate;

    IF v_status IS DISTINCT FROM 'PASS' THEN
        RAISE EXCEPTION 'TripBridge source-load gate FAIL (% failed tests). Analytics is blocked.',
            v_failed;
    END IF;

    RAISE NOTICE 'TripBridge source-load gate PASS. Analytics may proceed.';
END;
$$;
