-- Stage: PK/FK tests
-- Unique non-null keys, no orphans, and cross-table ownership lineage.

DO $$
DECLARE
    v_customers bigint;
    v_memberships bigint;
    v_bookings bigint;
    v_payments bigint;
    v_refunds bigint;
    v_events bigint;
BEGIN
    SELECT COUNT(*) INTO v_customers FROM tripbridge.customers;
    PERFORM tripbridge.assert_eq('pk_fk', 'customers_pk_unique', v_customers, (SELECT COUNT(DISTINCT customer_id) FROM tripbridge.customers));
    PERFORM tripbridge.assert_eq('pk_fk', 'customers_pk_not_null', 0, (SELECT COUNT(*) FROM tripbridge.customers WHERE customer_id IS NULL));

    SELECT COUNT(*) INTO v_memberships FROM tripbridge.memberships;
    PERFORM tripbridge.assert_eq('pk_fk', 'memberships_pk_unique', v_memberships, (SELECT COUNT(DISTINCT membership_id) FROM tripbridge.memberships));
    PERFORM tripbridge.assert_eq('pk_fk', 'memberships_pk_not_null', 0, (SELECT COUNT(*) FROM tripbridge.memberships WHERE membership_id IS NULL));

    SELECT COUNT(*) INTO v_bookings FROM tripbridge.bookings;
    PERFORM tripbridge.assert_eq('pk_fk', 'bookings_pk_unique', v_bookings, (SELECT COUNT(DISTINCT booking_id) FROM tripbridge.bookings));
    PERFORM tripbridge.assert_eq('pk_fk', 'bookings_pk_not_null', 0, (SELECT COUNT(*) FROM tripbridge.bookings WHERE booking_id IS NULL));

    SELECT COUNT(*) INTO v_payments FROM tripbridge.payments;
    PERFORM tripbridge.assert_eq('pk_fk', 'payments_pk_unique', v_payments, (SELECT COUNT(DISTINCT payment_id) FROM tripbridge.payments));
    PERFORM tripbridge.assert_eq('pk_fk', 'payments_pk_not_null', 0, (SELECT COUNT(*) FROM tripbridge.payments WHERE payment_id IS NULL));

    SELECT COUNT(*) INTO v_refunds FROM tripbridge.refunds;
    PERFORM tripbridge.assert_eq('pk_fk', 'refunds_pk_unique', v_refunds, (SELECT COUNT(DISTINCT refund_id) FROM tripbridge.refunds));
    PERFORM tripbridge.assert_eq('pk_fk', 'refunds_pk_not_null', 0, (SELECT COUNT(*) FROM tripbridge.refunds WHERE refund_id IS NULL));

    SELECT COUNT(*) INTO v_events FROM tripbridge.campaign_events;
    PERFORM tripbridge.assert_eq('pk_fk', 'campaign_events_pk_unique', v_events, (SELECT COUNT(DISTINCT event_id) FROM tripbridge.campaign_events));
    PERFORM tripbridge.assert_eq('pk_fk', 'campaign_events_pk_not_null', 0, (SELECT COUNT(*) FROM tripbridge.campaign_events WHERE event_id IS NULL));

    PERFORM tripbridge.assert_eq(
        'pk_fk', 'memberships_orphan_customer', 0,
        (SELECT COUNT(*) FROM tripbridge.memberships m
         WHERE NOT EXISTS (SELECT 1 FROM tripbridge.customers c WHERE c.customer_id = m.customer_id))
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'bookings_orphan_customer', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings b
         WHERE NOT EXISTS (SELECT 1 FROM tripbridge.customers c WHERE c.customer_id = b.customer_id))
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'bookings_orphan_membership', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings b
         WHERE b.membership_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM tripbridge.memberships m WHERE m.membership_id = b.membership_id))
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'payments_orphan_booking', 0,
        (SELECT COUNT(*) FROM tripbridge.payments p
         WHERE NOT EXISTS (SELECT 1 FROM tripbridge.bookings b WHERE b.booking_id = p.booking_id))
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'payments_orphan_customer', 0,
        (SELECT COUNT(*) FROM tripbridge.payments p
         WHERE NOT EXISTS (SELECT 1 FROM tripbridge.customers c WHERE c.customer_id = p.customer_id))
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'refunds_orphan_payment', 0,
        (SELECT COUNT(*) FROM tripbridge.refunds r
         WHERE NOT EXISTS (SELECT 1 FROM tripbridge.payments p WHERE p.payment_id = r.payment_id))
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'refunds_orphan_booking', 0,
        (SELECT COUNT(*) FROM tripbridge.refunds r
         WHERE NOT EXISTS (SELECT 1 FROM tripbridge.bookings b WHERE b.booking_id = r.booking_id))
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'campaign_events_orphan_customer', 0,
        (SELECT COUNT(*) FROM tripbridge.campaign_events e
         WHERE NOT EXISTS (SELECT 1 FROM tripbridge.customers c WHERE c.customer_id = e.customer_id))
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'campaign_events_orphan_conversion_booking', 0,
        (SELECT COUNT(*) FROM tripbridge.campaign_events e
         WHERE e.conversion_booking_id IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM tripbridge.bookings b WHERE b.booking_id = e.conversion_booking_id))
    );

    PERFORM tripbridge.assert_eq(
        'pk_fk', 'booking_membership_same_customer', 0,
        (SELECT COUNT(*)
         FROM tripbridge.bookings b
         JOIN tripbridge.memberships m ON m.membership_id = b.membership_id
         WHERE b.customer_id <> m.customer_id)
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'payment_same_customer_as_booking', 0,
        (SELECT COUNT(*)
         FROM tripbridge.payments p
         JOIN tripbridge.bookings b ON b.booking_id = p.booking_id
         WHERE p.customer_id <> b.customer_id)
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'refund_same_lineage_as_payment', 0,
        (SELECT COUNT(*)
         FROM tripbridge.refunds r
         JOIN tripbridge.payments p ON p.payment_id = r.payment_id
         WHERE r.booking_id <> p.booking_id OR r.customer_id <> p.customer_id)
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'conversion_booking_same_customer', 0,
        (SELECT COUNT(*)
         FROM tripbridge.campaign_events e
         JOIN tripbridge.bookings b ON b.booking_id = e.conversion_booking_id
         WHERE e.customer_id <> b.customer_id)
    );
    PERFORM tripbridge.assert_eq(
        'pk_fk', 'every_booking_has_payment', 0,
        (SELECT COUNT(*)
         FROM tripbridge.bookings b
         WHERE NOT EXISTS (SELECT 1 FROM tripbridge.payments p WHERE p.booking_id = b.booking_id))
    );
END;
$$;
