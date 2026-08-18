-- Stage: Financial controls
-- Reconcile money by currency. Do not convert FX. Successful payments are
-- settlement-like; all payment attempts are not revenue.

DO $$
DECLARE
    rec record;
BEGIN
    FOR rec IN
        SELECT *
        FROM (
            VALUES
                ('AUD'::bpchar,
                 473907470.60::numeric, 18658485.40::numeric,
                 471052060.22::numeric, 434335568.50::numeric,
                 18220649.44::numeric, 18140877.41::numeric),
                ('NZD',
                 29671115.58, 1147287.74,
                 29559435.83, 27327460.13,
                 1162558.82, 1157128.32),
                ('USD',
                 25394071.69, 1013210.16,
                 25322066.50, 23344415.93,
                 986203.47, 983226.35),
                ('EUR',
                 13981160.27, 544128.66,
                 13840661.52, 12882792.77,
                 565573.07, 564155.02),
                ('GBP',
                 8116197.94, 317183.34,
                 8084907.66, 7387449.57,
                 340866.50, 340458.27)
        ) AS x(
            currency, gross_booking_value, discounts,
            all_payment_attempts, successful_payments,
            all_refund_requests, completed_refunds
        )
    LOOP
        PERFORM tripbridge.assert_eq_numeric(
            'financial', rec.currency || '_gross_booking_value',
            rec.gross_booking_value,
            (SELECT COALESCE(SUM(gross_booking_amount), 0)
             FROM tripbridge.bookings WHERE booking_currency = rec.currency)
        );
        PERFORM tripbridge.assert_eq_numeric(
            'financial', rec.currency || '_discounts',
            rec.discounts,
            (SELECT COALESCE(SUM(discount_amount), 0)
             FROM tripbridge.bookings WHERE booking_currency = rec.currency)
        );
        PERFORM tripbridge.assert_eq_numeric(
            'financial', rec.currency || '_all_payment_attempts',
            rec.all_payment_attempts,
            (SELECT COALESCE(SUM(payment_amount), 0)
             FROM tripbridge.payments WHERE payment_currency = rec.currency)
        );
        PERFORM tripbridge.assert_eq_numeric(
            'financial', rec.currency || '_successful_payments',
            rec.successful_payments,
            (SELECT COALESCE(SUM(payment_amount), 0)
             FROM tripbridge.payments
             WHERE payment_currency = rec.currency AND payment_status = 'SUCCESS')
        );
        PERFORM tripbridge.assert_eq_numeric(
            'financial', rec.currency || '_all_refund_requests',
            rec.all_refund_requests,
            (SELECT COALESCE(SUM(r.refund_amount), 0)
             FROM tripbridge.refunds r
             JOIN tripbridge.payments p ON p.payment_id = r.payment_id
             WHERE p.payment_currency = rec.currency)
        );
        PERFORM tripbridge.assert_eq_numeric(
            'financial', rec.currency || '_completed_refunds',
            rec.completed_refunds,
            (SELECT COALESCE(SUM(r.refund_amount), 0)
             FROM tripbridge.refunds r
             JOIN tripbridge.payments p ON p.payment_id = r.payment_id
             WHERE p.payment_currency = rec.currency AND r.refund_status = 'COMPLETED')
        );
        PERFORM tripbridge.assert_eq_numeric(
            'financial', rec.currency || '_net_collected',
            rec.successful_payments - rec.completed_refunds,
            (SELECT successful_payments - completed_refunds
             FROM tripbridge.v_financial_control_totals
             WHERE currency = rec.currency)
        );
    END LOOP;

    PERFORM tripbridge.assert_eq(
        'financial', 'payment_currency_matches_booking', 0,
        (SELECT COUNT(*)
         FROM tripbridge.payments p
         JOIN tripbridge.bookings b ON b.booking_id = p.booking_id
         WHERE p.payment_currency <> b.booking_currency)
    );
    PERFORM tripbridge.assert_eq(
        'financial', 'non_positive_payment_amount', 0,
        (SELECT COUNT(*) FROM tripbridge.payments WHERE payment_amount <= 0)
    );
    PERFORM tripbridge.assert_eq(
        'financial', 'payment_exceeds_booking_net', 0,
        (SELECT COUNT(*)
         FROM tripbridge.payments p
         JOIN tripbridge.bookings b ON b.booking_id = p.booking_id
         WHERE p.payment_amount > (b.gross_booking_amount - b.discount_amount))
    );
    PERFORM tripbridge.assert_eq(
        'financial', 'successful_payments_exceed_booking_net', 0,
        (SELECT COUNT(*)
         FROM (
             SELECT p.booking_id, SUM(p.payment_amount) AS settled
             FROM tripbridge.payments p
             WHERE p.payment_status = 'SUCCESS'
             GROUP BY p.booking_id
         ) s
         JOIN tripbridge.bookings b ON b.booking_id = s.booking_id
         WHERE s.settled > (b.gross_booking_amount - b.discount_amount))
    );
    PERFORM tripbridge.assert_eq(
        'financial', 'non_positive_refund_amount', 0,
        (SELECT COUNT(*) FROM tripbridge.refunds WHERE refund_amount <= 0)
    );
    PERFORM tripbridge.assert_eq(
        'financial', 'refund_exceeds_referenced_payment', 0,
        (SELECT COUNT(*)
         FROM tripbridge.refunds r
         JOIN tripbridge.payments p ON p.payment_id = r.payment_id
         WHERE r.refund_amount > p.payment_amount)
    );
    PERFORM tripbridge.assert_eq(
        'financial', 'cumulative_refunds_exceed_payment', 0,
        (SELECT COUNT(*)
         FROM (
             SELECT r.payment_id, SUM(r.refund_amount) AS refunded
             FROM tripbridge.refunds r
             GROUP BY r.payment_id
         ) s
         JOIN tripbridge.payments p ON p.payment_id = s.payment_id
         WHERE s.refunded > p.payment_amount)
    );
    PERFORM tripbridge.assert_eq(
        'financial', 'fully_refunded_not_reconciled', 0,
        (
            WITH pay AS (
                SELECT booking_id, SUM(payment_amount) AS paid
                FROM tripbridge.payments
                WHERE payment_status = 'SUCCESS'
                GROUP BY booking_id
            ),
            ref AS (
                SELECT booking_id, SUM(refund_amount) AS refunded
                FROM tripbridge.refunds
                WHERE refund_status = 'COMPLETED'
                GROUP BY booking_id
            )
            SELECT COUNT(*)
            FROM tripbridge.bookings b
            LEFT JOIN pay ON pay.booking_id = b.booking_id
            LEFT JOIN ref ON ref.booking_id = b.booking_id
            WHERE b.booking_status = 'FULLY_REFUNDED'
              AND COALESCE(ref.refunded, 0) IS DISTINCT FROM COALESCE(pay.paid, 0)
        )
    );
    PERFORM tripbridge.assert_eq(
        'financial', 'partially_refunded_not_partial', 0,
        (
            WITH pay AS (
                SELECT booking_id, SUM(payment_amount) AS paid
                FROM tripbridge.payments
                WHERE payment_status = 'SUCCESS'
                GROUP BY booking_id
            ),
            ref AS (
                SELECT booking_id, SUM(refund_amount) AS refunded
                FROM tripbridge.refunds
                WHERE refund_status = 'COMPLETED'
                GROUP BY booking_id
            )
            SELECT COUNT(*)
            FROM tripbridge.bookings b
            LEFT JOIN pay ON pay.booking_id = b.booking_id
            LEFT JOIN ref ON ref.booking_id = b.booking_id
            WHERE b.booking_status = 'PARTIALLY_REFUNDED'
              AND NOT (COALESCE(ref.refunded, 0) > 0
                       AND COALESCE(ref.refunded, 0) < COALESCE(pay.paid, 0))
        )
    );
    PERFORM tripbridge.assert_eq(
        'financial', 'membership_fee_currency_is_aud_numeric', 0,
        (SELECT COUNT(*) FROM tripbridge.memberships WHERE annual_fee < 0)
    );
END;
$$;
