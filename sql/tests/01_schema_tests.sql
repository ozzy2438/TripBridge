-- Stage: Schema tests
-- Confirms tripbridge schema, source tables, views, column contract, and PK/FK constraint presence.

INSERT INTO tripbridge.pipeline_test_result (
    run_id, stage, test_name, passed, expected_value, actual_value, detail
)
SELECT
    tripbridge.current_test_run_id(),
    'schema',
    s.test_name,
    s.passed,
    s.expected_value,
    s.actual_value,
    s.detail
FROM (
    SELECT
        'schema_exists' AS test_name,
        EXISTS (
            SELECT 1 FROM information_schema.schemata WHERE schema_name = 'tripbridge'
        ) AS passed,
        'tripbridge' AS expected_value,
        'tripbridge' AS actual_value,
        NULL::text AS detail

    UNION ALL
    SELECT
        'required_tables_present',
        missing.n = 0,
        '6 source tables + load_audit',
        (7 - missing.n)::text,
        CASE WHEN missing.n = 0 THEN NULL
             ELSE 'Missing: ' || array_to_string(missing.names, ', ')
        END
    FROM (
        SELECT
            COUNT(*) FILTER (WHERE t.table_name IS NULL) AS n,
            array_agg(r.table_name ORDER BY r.table_name) FILTER (WHERE t.table_name IS NULL) AS names
        FROM (
            VALUES
                ('customers'),
                ('memberships'),
                ('bookings'),
                ('payments'),
                ('refunds'),
                ('campaign_events'),
                ('load_audit')
        ) AS r(table_name)
        LEFT JOIN information_schema.tables t
            ON t.table_schema = 'tripbridge'
           AND t.table_name = r.table_name
           AND t.table_type = 'BASE TABLE'
    ) missing

    UNION ALL
    SELECT
        'required_views_present',
        missing.n = 0,
        'v_source_row_counts, v_data_quality_profile, v_financial_control_totals',
        (3 - missing.n)::text,
        CASE WHEN missing.n = 0 THEN NULL
             ELSE 'Missing: ' || array_to_string(missing.names, ', ')
        END
    FROM (
        SELECT
            COUNT(*) FILTER (WHERE t.table_name IS NULL) AS n,
            array_agg(r.table_name ORDER BY r.table_name) FILTER (WHERE t.table_name IS NULL) AS names
        FROM (
            VALUES
                ('v_source_row_counts'),
                ('v_data_quality_profile'),
                ('v_financial_control_totals')
        ) AS r(table_name)
        LEFT JOIN information_schema.views t
            ON t.table_schema = 'tripbridge'
           AND t.table_name = r.table_name
    ) missing

    UNION ALL
    SELECT
        'column_contract_matches',
        mismatch.n = 0,
        '0 mismatched columns',
        mismatch.n::text,
        CASE WHEN mismatch.n = 0 THEN NULL
             ELSE left(array_to_string(mismatch.details, '; '), 1000)
        END
    FROM (
        SELECT
            COUNT(*) AS n,
            array_agg(msg ORDER BY msg) AS details
        FROM (
            WITH expected (
                table_name, column_name, data_type, character_maximum_length,
                numeric_precision, numeric_scale, is_nullable
            ) AS (
                VALUES
                    ('customers', 'customer_id', 'character varying', 12, NULL::int, NULL::int, 'NO'),
                    ('customers', 'first_name', 'character varying', 50, NULL, NULL, 'NO'),
                    ('customers', 'last_name', 'character varying', 60, NULL, NULL, 'NO'),
                    ('customers', 'email', 'character varying', 160, NULL, NULL, 'NO'),
                    ('customers', 'phone', 'character varying', 30, NULL, NULL, 'YES'),
                    ('customers', 'date_of_birth', 'date', NULL, NULL, NULL, 'NO'),
                    ('customers', 'gender', 'character varying', 24, NULL, NULL, 'NO'),
                    ('customers', 'city', 'character varying', 80, NULL, NULL, 'NO'),
                    ('customers', 'state', 'character varying', 80, NULL, NULL, 'NO'),
                    ('customers', 'postcode', 'character varying', 12, NULL, NULL, 'NO'),
                    ('customers', 'country', 'character varying', 60, NULL, NULL, 'NO'),
                    ('customers', 'signup_date', 'date', NULL, NULL, NULL, 'NO'),
                    ('customers', 'marketing_consent', 'boolean', NULL, NULL, NULL, 'YES'),
                    ('customers', 'customer_status', 'character varying', 12, NULL, NULL, 'NO'),
                    ('customers', 'created_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('customers', 'updated_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('memberships', 'membership_id', 'character varying', 11, NULL, NULL, 'NO'),
                    ('memberships', 'customer_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('memberships', 'membership_type', 'character varying', 12, NULL, NULL, 'NO'),
                    ('memberships', 'membership_start_date', 'date', NULL, NULL, NULL, 'NO'),
                    ('memberships', 'membership_end_date', 'date', NULL, NULL, NULL, 'NO'),
                    ('memberships', 'membership_status', 'character varying', 12, NULL, NULL, 'NO'),
                    ('memberships', 'annual_fee', 'numeric', NULL, 10, 2, 'NO'),
                    ('memberships', 'renewal_type', 'character varying', 8, NULL, NULL, 'NO'),
                    ('memberships', 'created_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('memberships', 'updated_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('bookings', 'booking_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('bookings', 'customer_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('bookings', 'membership_id', 'character varying', 11, NULL, NULL, 'YES'),
                    ('bookings', 'booking_date', 'date', NULL, NULL, NULL, 'NO'),
                    ('bookings', 'travel_date', 'date', NULL, NULL, NULL, 'NO'),
                    ('bookings', 'booking_type', 'character varying', 12, NULL, NULL, 'NO'),
                    ('bookings', 'origin', 'character varying', 100, NULL, NULL, 'YES'),
                    ('bookings', 'destination', 'character varying', 100, NULL, NULL, 'NO'),
                    ('bookings', 'passenger_count', 'smallint', NULL, 16, 0, 'NO'),
                    ('bookings', 'booking_currency', 'character', 3, NULL, NULL, 'NO'),
                    ('bookings', 'gross_booking_amount', 'numeric', NULL, 12, 2, 'NO'),
                    ('bookings', 'discount_amount', 'numeric', NULL, 12, 2, 'NO'),
                    ('bookings', 'booking_status', 'character varying', 24, NULL, NULL, 'NO'),
                    ('bookings', 'channel', 'character varying', 20, NULL, NULL, 'NO'),
                    ('bookings', 'created_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('bookings', 'updated_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('payments', 'payment_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('payments', 'booking_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('payments', 'customer_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('payments', 'payment_date', 'date', NULL, NULL, NULL, 'NO'),
                    ('payments', 'payment_method', 'character varying', 20, NULL, NULL, 'NO'),
                    ('payments', 'payment_currency', 'character', 3, NULL, NULL, 'NO'),
                    ('payments', 'payment_amount', 'numeric', NULL, 12, 2, 'NO'),
                    ('payments', 'payment_status', 'character varying', 12, NULL, NULL, 'NO'),
                    ('payments', 'transaction_reference', 'character varying', 32, NULL, NULL, 'NO'),
                    ('payments', 'created_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('payments', 'updated_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('refunds', 'refund_id', 'character varying', 11, NULL, NULL, 'NO'),
                    ('refunds', 'payment_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('refunds', 'booking_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('refunds', 'customer_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('refunds', 'refund_date', 'date', NULL, NULL, NULL, 'NO'),
                    ('refunds', 'refund_amount', 'numeric', NULL, 12, 2, 'NO'),
                    ('refunds', 'refund_reason', 'character varying', 28, NULL, NULL, 'NO'),
                    ('refunds', 'refund_status', 'character varying', 12, NULL, NULL, 'NO'),
                    ('refunds', 'created_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('refunds', 'updated_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('campaign_events', 'event_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('campaign_events', 'customer_id', 'character varying', 12, NULL, NULL, 'NO'),
                    ('campaign_events', 'campaign_id', 'character varying', 40, NULL, NULL, 'NO'),
                    ('campaign_events', 'campaign_name', 'character varying', 40, NULL, NULL, 'NO'),
                    ('campaign_events', 'campaign_type', 'character varying', 16, NULL, NULL, 'NO'),
                    ('campaign_events', 'channel', 'character varying', 12, NULL, NULL, 'NO'),
                    ('campaign_events', 'event_type', 'character varying', 16, NULL, NULL, 'NO'),
                    ('campaign_events', 'event_timestamp', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('campaign_events', 'device_type', 'character varying', 12, NULL, NULL, 'YES'),
                    ('campaign_events', 'offer_code', 'character varying', 24, NULL, NULL, 'YES'),
                    ('campaign_events', 'conversion_booking_id', 'character varying', 12, NULL, NULL, 'YES'),
                    ('campaign_events', 'created_at', 'timestamp without time zone', NULL, NULL, NULL, 'NO'),
                    ('load_audit', 'dataset_name', 'text', NULL, NULL, NULL, 'NO'),
                    ('load_audit', 'source_file', 'text', NULL, NULL, NULL, 'NO'),
                    ('load_audit', 'source_blob_sha', 'character', 40, NULL, NULL, 'NO'),
                    ('load_audit', 'expected_rows', 'bigint', NULL, 64, 0, 'NO'),
                    ('load_audit', 'loaded_rows', 'bigint', NULL, 64, 0, 'NO'),
                    ('load_audit', 'load_status', 'text', NULL, NULL, NULL, 'NO'),
                    ('load_audit', 'loaded_at', 'timestamp with time zone', NULL, NULL, NULL, 'NO')
            ),
            actual AS (
                SELECT
                    c.table_name,
                    c.column_name,
                    c.data_type,
                    c.character_maximum_length::int AS character_maximum_length,
                    c.numeric_precision::int AS numeric_precision,
                    c.numeric_scale::int AS numeric_scale,
                    c.is_nullable
                FROM information_schema.columns c
                WHERE c.table_schema = 'tripbridge'
                  AND c.table_name IN (
                      'customers', 'memberships', 'bookings', 'payments',
                      'refunds', 'campaign_events', 'load_audit'
                  )
            )
            SELECT format('%s.%s missing', e.table_name, e.column_name) AS msg
            FROM expected e
            LEFT JOIN actual a
                ON a.table_name = e.table_name AND a.column_name = e.column_name
            WHERE a.column_name IS NULL
            UNION ALL
            SELECT format('%s.%s extra', a.table_name, a.column_name)
            FROM actual a
            LEFT JOIN expected e
                ON e.table_name = a.table_name AND e.column_name = a.column_name
            WHERE e.column_name IS NULL
            UNION ALL
            SELECT format(
                '%s.%s type %s(%s,%s,%s,%s) vs %s(%s,%s,%s,%s)',
                e.table_name, e.column_name,
                e.data_type, e.character_maximum_length, e.numeric_precision, e.numeric_scale, e.is_nullable,
                a.data_type, a.character_maximum_length, a.numeric_precision, a.numeric_scale, a.is_nullable
            )
            FROM expected e
            JOIN actual a
                ON a.table_name = e.table_name AND a.column_name = e.column_name
            WHERE e.data_type IS DISTINCT FROM a.data_type
               OR e.character_maximum_length IS DISTINCT FROM a.character_maximum_length
               OR e.numeric_precision IS DISTINCT FROM a.numeric_precision
               OR e.numeric_scale IS DISTINCT FROM a.numeric_scale
               OR e.is_nullable IS DISTINCT FROM a.is_nullable
        ) diffs
    ) mismatch

    UNION ALL
    SELECT
        'pk_fk_constraints_present',
        missing.n = 0,
        '17 PK/FK constraints',
        (17 - missing.n)::text,
        CASE WHEN missing.n = 0 THEN NULL
             ELSE 'Missing: ' || array_to_string(missing.names, ', ')
        END
    FROM (
        SELECT
            COUNT(*) FILTER (WHERE c.conname IS NULL) AS n,
            array_agg(r.conname ORDER BY r.conname) FILTER (WHERE c.conname IS NULL) AS names
        FROM (
            VALUES
                ('customers_pkey'),
                ('memberships_pkey'),
                ('memberships_customer_fk'),
                ('bookings_pkey'),
                ('bookings_customer_fk'),
                ('bookings_membership_fk'),
                ('payments_pkey'),
                ('payments_booking_fk'),
                ('payments_customer_fk'),
                ('refunds_pkey'),
                ('refunds_payment_fk'),
                ('refunds_booking_fk'),
                ('refunds_customer_fk'),
                ('campaign_events_pkey'),
                ('campaign_events_customer_fk'),
                ('campaign_events_conversion_booking_fk'),
                ('load_audit_pkey')
        ) AS r(conname)
        LEFT JOIN pg_constraint c
            ON c.conname = r.conname
           AND c.connamespace = 'tripbridge'::regnamespace
           AND c.contype IN ('p', 'f')
    ) missing
) s;
