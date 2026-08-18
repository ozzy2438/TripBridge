-- Stage: Row reconciliation
-- Live COUNT(*) must match the extract contract and load_audit.

DO $$
DECLARE
    rec record;
    live_count bigint;
BEGIN
    FOR rec IN
        SELECT *
        FROM (
            VALUES
                ('customers', 50000::bigint, 'data/customers.csv'),
                ('memberships', 70000, 'data/memberships.csv'),
                ('bookings', 400000, 'data/bookings.csv'),
                ('payments', 450000, 'data/payments.csv'),
                ('refunds', 30000, 'data/refunds.csv'),
                ('campaign_events', 500000, 'data/campaign_events.csv')
        ) AS x(dataset_name, expected_rows, source_file)
    LOOP
        EXECUTE format('SELECT COUNT(*) FROM tripbridge.%I', rec.dataset_name)
            INTO live_count;

        PERFORM tripbridge.assert_eq(
            'row_reconciliation',
            rec.dataset_name || '_live_vs_contract',
            rec.expected_rows,
            live_count,
            'CSV extract contract'
        );

        PERFORM tripbridge.assert_eq(
            'row_reconciliation',
            rec.dataset_name || '_live_vs_load_audit',
            (SELECT loaded_rows FROM tripbridge.load_audit WHERE dataset_name = rec.dataset_name),
            live_count,
            'load_audit.loaded_rows'
        );

        PERFORM tripbridge.assert_eq(
            'row_reconciliation',
            rec.dataset_name || '_audit_expected_eq_loaded',
            (SELECT expected_rows FROM tripbridge.load_audit WHERE dataset_name = rec.dataset_name),
            (SELECT loaded_rows FROM tripbridge.load_audit WHERE dataset_name = rec.dataset_name),
            rec.source_file
        );

        PERFORM tripbridge.record_test(
            'row_reconciliation',
            rec.dataset_name || '_load_status_pass',
            (SELECT load_status FROM tripbridge.load_audit WHERE dataset_name = rec.dataset_name) = 'PASS',
            'PASS',
            (SELECT load_status FROM tripbridge.load_audit WHERE dataset_name = rec.dataset_name),
            rec.source_file
        );

        PERFORM tripbridge.record_test(
            'row_reconciliation',
            rec.dataset_name || '_source_file_matches',
            (SELECT source_file FROM tripbridge.load_audit WHERE dataset_name = rec.dataset_name) = rec.source_file,
            rec.source_file,
            (SELECT source_file FROM tripbridge.load_audit WHERE dataset_name = rec.dataset_name),
            NULL
        );
    END LOOP;

    PERFORM tripbridge.assert_eq(
        'row_reconciliation',
        'load_audit_dataset_count',
        6,
        (SELECT COUNT(*) FROM tripbridge.load_audit),
        'one audit row per source extract'
    );

    PERFORM tripbridge.assert_eq(
        'row_reconciliation',
        'v_source_row_counts_matches_live',
        0,
        (
            SELECT COUNT(*)
            FROM tripbridge.v_source_row_counts v
            JOIN tripbridge.load_audit a USING (dataset_name)
            WHERE v.row_count IS DISTINCT FROM a.loaded_rows
        ),
        'view vs load_audit'
    );
END;
$$;
