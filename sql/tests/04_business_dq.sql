-- Stage: Business data-quality tests
-- Hard operational rules must be 0-defect.
-- Documented source dirt must still match DATA_QUALITY_NOTES.md exactly
-- so the load did not silently clean or inflate the extract.

DO $$
DECLARE
    v_dup_customers bigint;
    v_dup_events bigint;
BEGIN
    -- Allowed domains
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_customer_status', 0,
        (SELECT COUNT(*) FROM tripbridge.customers
         WHERE customer_status NOT IN ('ACTIVE', 'INACTIVE', 'CLOSED'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_gender', 0,
        (SELECT COUNT(*) FROM tripbridge.customers
         WHERE gender NOT IN ('FEMALE', 'MALE', 'NON_BINARY', 'PREFER_NOT_TO_SAY'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_membership_type', 0,
        (SELECT COUNT(*) FROM tripbridge.memberships
         WHERE membership_type NOT IN ('STANDARD', 'PLUS', 'PREMIUM', 'CORPORATE'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_membership_status', 0,
        (SELECT COUNT(*) FROM tripbridge.memberships
         WHERE membership_status NOT IN ('ACTIVE', 'EXPIRED', 'CANCELLED', 'SUSPENDED'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_renewal_type', 0,
        (SELECT COUNT(*) FROM tripbridge.memberships
         WHERE renewal_type NOT IN ('AUTO', 'MANUAL', 'NONE'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_booking_type', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings
         WHERE booking_type NOT IN ('FLIGHT', 'HOTEL', 'PACKAGE', 'CAR_HIRE', 'TOUR'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_booking_status', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings
         WHERE booking_status NOT IN (
             'CONFIRMED', 'COMPLETED', 'CANCELLED', 'PARTIALLY_REFUNDED', 'FULLY_REFUNDED'
         ))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_booking_channel', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings
         WHERE channel NOT IN ('WEB', 'MOBILE_APP', 'CALL_CENTRE', 'AGENT'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_booking_currency', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings
         WHERE booking_currency NOT IN ('AUD', 'NZD', 'USD', 'EUR', 'GBP'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_payment_method', 0,
        (SELECT COUNT(*) FROM tripbridge.payments
         WHERE payment_method NOT IN ('VISA', 'MASTERCARD', 'AMEX', 'PAYPAL', 'APPLE_PAY', 'BANK_TRANSFER'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_payment_status', 0,
        (SELECT COUNT(*) FROM tripbridge.payments
         WHERE payment_status NOT IN ('SUCCESS', 'PENDING', 'FAILED', 'DECLINED', 'REVERSED'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_refund_reason', 0,
        (SELECT COUNT(*) FROM tripbridge.refunds
         WHERE refund_reason NOT IN (
             'CUSTOMER_CANCELLED', 'AIRLINE_CANCELLED', 'SERVICE_FAILURE',
             'DUPLICATE_PAYMENT', 'PRICE_ADJUSTMENT', 'PARTIAL_SERVICE_REFUND', 'OTHER'
         ))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_refund_status', 0,
        (SELECT COUNT(*) FROM tripbridge.refunds
         WHERE refund_status NOT IN ('COMPLETED', 'PENDING', 'REJECTED'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_campaign_type', 0,
        (SELECT COUNT(*) FROM tripbridge.campaign_events
         WHERE campaign_type NOT IN ('SEASONAL', 'TACTICAL', 'MEMBER', 'LIFECYCLE'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_campaign_name', 0,
        (SELECT COUNT(*) FROM tripbridge.campaign_events
         WHERE campaign_name NOT IN (
             'SUMMER_ESCAPE', 'EOFY_TRAVEL', 'WEEKEND_GETAWAY',
             'PREMIUM_MEMBER_OFFER', 'NEW_MEMBER_WELCOME', 'WINTER_CITY_BREAK'
         ))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_event_type', 0,
        (SELECT COUNT(*) FROM tripbridge.campaign_events
         WHERE event_type NOT IN (
             'SENT', 'DELIVERED', 'OPENED', 'CLICKED', 'BOUNCED', 'UNSUBSCRIBED', 'CONVERTED'
         ))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_canonical_campaign_channel', 0,
        (SELECT COUNT(*) FROM tripbridge.campaign_events
         WHERE upper(channel) NOT IN ('EMAIL', 'SMS', 'PUSH', 'IN_APP'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'invalid_device_type', 0,
        (SELECT COUNT(*) FROM tripbridge.campaign_events
         WHERE device_type IS NOT NULL
           AND device_type NOT IN ('MOBILE', 'DESKTOP', 'TABLET'))
    );

    -- Hard operational rules
    PERFORM tripbridge.assert_eq(
        'business_dq', 'membership_end_before_start', 0,
        (SELECT COUNT(*) FROM tripbridge.memberships
         WHERE membership_end_date < membership_start_date)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'non_positive_passenger_count', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings WHERE passenger_count <= 0)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'discount_exceeds_gross', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings
         WHERE discount_amount < 0 OR gross_booking_amount < 0
            OR discount_amount > gross_booking_amount)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'non_positive_booking_net', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings
         WHERE gross_booking_amount - discount_amount <= 0)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'booking_membership_not_usable_on_booking_date', 0,
        (SELECT COUNT(*)
         FROM tripbridge.bookings b
         JOIN tripbridge.memberships m ON m.membership_id = b.membership_id
         WHERE m.membership_status NOT IN ('ACTIVE', 'EXPIRED')
            OR b.booking_date < m.membership_start_date
            OR b.booking_date > m.membership_end_date)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'payment_before_booking', 0,
        (SELECT COUNT(*)
         FROM tripbridge.payments p
         JOIN tripbridge.bookings b ON b.booking_id = p.booking_id
         WHERE p.payment_date < b.booking_date)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'refund_not_after_payment', 0,
        (SELECT COUNT(*)
         FROM tripbridge.refunds r
         JOIN tripbridge.payments p ON p.payment_id = r.payment_id
         WHERE r.refund_date <= p.payment_date)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'refunds_on_non_refund_booking_status', 0,
        (SELECT COUNT(*)
         FROM tripbridge.refunds r
         JOIN tripbridge.bookings b ON b.booking_id = r.booking_id
         WHERE b.booking_status NOT IN ('PARTIALLY_REFUNDED', 'FULLY_REFUNDED'))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'customer_not_adult_at_signup', 0,
        (SELECT COUNT(*) FROM tripbridge.customers
         WHERE AGE(signup_date, date_of_birth) < INTERVAL '18 years')
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'updated_at_before_created_at_customers', 0,
        (SELECT COUNT(*) FROM tripbridge.customers WHERE updated_at < created_at)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'updated_at_before_created_at_bookings', 0,
        (SELECT COUNT(*) FROM tripbridge.bookings WHERE updated_at < created_at)
    );

    -- Documented source dirt: exact expected counts
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_missing_phone', 750,
        (SELECT COUNT(*) FROM tripbridge.customers WHERE phone IS NULL)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_unknown_marketing_consent', 250,
        (SELECT COUNT(*) FROM tripbridge.customers WHERE marketing_consent IS NULL)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_uppercase_email', 120,
        (SELECT COUNT(*) FROM tripbridge.customers WHERE email <> lower(email))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_travel_before_booking', 80,
        (SELECT COUNT(*) FROM tripbridge.bookings WHERE travel_date < booking_date)
    );
    PERFORM tripbridge.record_test(
        'business_dq',
        'documented_late_booking_update_present',
        (
            SELECT COUNT(*) FROM tripbridge.bookings
            WHERE booking_status = 'COMPLETED'
              AND booking_date <= DATE '2026-08-17' - 180
              AND updated_at::date >= DATE '2026-08-17' - 8
        ) >= 600,
        '>=600',
        (
            SELECT COUNT(*) FROM tripbridge.bookings
            WHERE booking_status = 'COMPLETED'
              AND booking_date <= DATE '2026-08-17' - 180
              AND updated_at::date >= DATE '2026-08-17' - 8
        )::text,
        'Old completed bookings updated near extract date; exact 600 rows are not uniquely keyed'
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_noncanonical_campaign_channel', 500,
        (SELECT COUNT(*) FROM tripbridge.campaign_events WHERE channel <> upper(channel))
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_missing_device_type', 5153,
        (SELECT COUNT(*) FROM tripbridge.campaign_events WHERE device_type IS NULL)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_suppression_anomaly', 514,
        (SELECT COUNT(*)
         FROM tripbridge.campaign_events e
         JOIN tripbridge.customers c USING (customer_id)
         WHERE c.marketing_consent IS DISTINCT FROM TRUE)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_bookings_without_membership', 143931,
        (SELECT COUNT(*) FROM tripbridge.bookings WHERE membership_id IS NULL)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_missing_origin', 24554,
        (SELECT COUNT(*) FROM tripbridge.bookings WHERE origin IS NULL)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_missing_offer_code', 215582,
        (SELECT COUNT(*) FROM tripbridge.campaign_events WHERE offer_code IS NULL)
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_conversion_booking_refs', 11201,
        (SELECT COUNT(*) FROM tripbridge.campaign_events WHERE conversion_booking_id IS NOT NULL)
    );

    SELECT COALESCE(SUM(cnt - 1), 0) INTO v_dup_customers
    FROM (
        SELECT COUNT(*) AS cnt
        FROM tripbridge.customers
        GROUP BY first_name, last_name, email, phone, date_of_birth
        HAVING COUNT(*) > 1
    ) d;
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_duplicate_like_customer_pairs', 25, v_dup_customers
    );

    SELECT COALESCE(SUM(cnt - 1), 0) INTO v_dup_events
    FROM (
        SELECT COUNT(*) AS cnt
        FROM tripbridge.campaign_events
        GROUP BY customer_id, campaign_id, campaign_name, campaign_type, channel,
                 event_type, event_timestamp, device_type, offer_code, conversion_booking_id
        HAVING COUNT(*) > 1
    ) d;
    PERFORM tripbridge.assert_eq(
        'business_dq', 'documented_duplicate_like_campaign_events', 200, v_dup_events
    );

    -- Status volumes from GENERATION_SUMMARY.md
    PERFORM tripbridge.assert_eq(
        'business_dq', 'customer_status_active', 43870,
        (SELECT COUNT(*) FROM tripbridge.customers WHERE customer_status = 'ACTIVE')
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'booking_status_completed', 291000,
        (SELECT COUNT(*) FROM tripbridge.bookings WHERE booking_status = 'COMPLETED')
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'booking_status_cancelled', 40000,
        (SELECT COUNT(*) FROM tripbridge.bookings WHERE booking_status = 'CANCELLED')
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'booking_status_fully_refunded', 10000,
        (SELECT COUNT(*) FROM tripbridge.bookings WHERE booking_status = 'FULLY_REFUNDED')
    );
    PERFORM tripbridge.assert_eq(
        'business_dq', 'booking_status_partially_refunded', 15000,
        (SELECT COUNT(*) FROM tripbridge.bookings WHERE booking_status = 'PARTIALLY_REFUNDED')
    );
END;
$$;
