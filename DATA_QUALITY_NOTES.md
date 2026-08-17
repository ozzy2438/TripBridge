# TripBridge Intentional Data Quality Notes

The extracts preserve unique primary keys and valid core foreign keys. The following controlled issues were added for profiling, cleansing, incremental-load and reconciliation practice.

## Deliberate source-quality issues

| Issue | Exact rows/pairs | Location | Intended exercise |
|---|---:|---|---|
| Missing optional phone | 750 rows | `customers.phone` | Null handling and completeness profiling. |
| Unknown marketing consent | 250 rows | `customers.marketing_consent` | Three-state consent treatment; blank is not consent. |
| Upper-case synthetic email | 120 rows | `customers.email` | Case normalisation and natural-key matching. |
| Duplicate-like customer natural keys | 25 pairs | Customers share name/email/phone/DOB but retain different `customer_id` values | Deduplication without breaking primary keys. |
| Travel date before booking date | 80 rows | `bookings.travel_date` | Reject/quarantine date-rule failures. The offset is only one or two days. |
| Late booking update | 600 rows | `bookings.updated_at` | Incremental watermark/backfill logic; these old bookings were updated near the extract date. |
| Inconsistent campaign channel casing | 500 rows | `campaign_events.channel` | Standardise values such as `email`, `Push` and canonical upper case. |
| Duplicate-like campaign event | 200 rows | Same business event repeated under a different `event_id` | Idempotency/business-key deduplication while preserving PK uniqueness. |
| Missing device type | 5,153 rows | `campaign_events.device_type` | Optional marketing attribute completeness. |
| Suppression anomaly | 514 event rows | Events sent to customers whose consent is false/unknown | Consent-control reconciliation; the exception rate is intentionally very small. |

## Expected optional sparsity (not necessarily a defect)

- `143,931` bookings have no `membership_id`. This includes non-members, bookings outside a usable membership period, and a small controlled source omission rate.
- `24,554` hotel/car-hire/tour bookings have a blank origin because the field is not always meaningful in the upstream product flow.
- `215,582` campaign events have no `offer_code`; many messages are informational or do not use a promotion.
- Conversion booking IDs appear on `11,201` conversion-event rows; attribution is optional.

## Operational outcomes retained for realism

- Cancelled bookings: `40,000`.
- Failed payments: `11,178`; declined payments: `9,829`; reversed payments: `10,083`.
- A cancelled booking can retain a successful payment where the amount represents a non-refundable supplier charge/cancellation fee.
- Pending/rejected refund attempts do not make a booking fully refunded. Every `FULLY_REFUNDED` booking reconciles to completed refunds; every `PARTIALLY_REFUNDED` booking has a positive completed refund below successful payments.

## Guarantees deliberately not broken

- No duplicate or null primary keys.
- No orphan customer, membership, booking, payment or refund foreign keys.
- A supplied booking membership belongs to the same customer and covers the booking date.
- Payment customer ownership matches the booking; payment amounts do not exceed booking net value.
- Refunds occur after payment and cumulative refund rows never exceed the referenced payment.
- A populated campaign conversion booking belongs to the event customer.
