# TripBridge Generation Summary

Generated deterministically with seed `20260817` and an extract/as-of date of `2026-08-17`. The main operational history runs from `2024-08-17` through `2026-08-17`; confirmed travel extends beyond the extract date.

## Output row counts

| File | Rows |
|---|---:|
| customers.csv | 50,000 |
| memberships.csv | 70,000 |
| bookings.csv | 400,000 |
| payments.csv | 450,000 |
| refunds.csv | 30,000 |
| campaign_events.csv | 500,000 |

- Unique customers: **50,000**
- Customers with at least one membership record: **41,000**
- Customers with at least one booking: **40,299**
- Customers with exactly one booking: **4,627**
- Highest booking count for one frequent traveller: **157**
- Generated campaign journeys: **163,929** (each journey produces a valid event sequence)

## Observed date ranges

| Dataset | Minimum | Maximum |
|---|---|---|
| Customer signup | 2024-08-17 | 2026-08-16 |
| Membership service dates | 2024-08-17 | 2027-09-01 |
| Booking/travel dates | 2024-08-18 | 2027-06-13 |
| Payment dates | 2024-08-18 | 2026-08-17 |
| Refund dates | 2024-08-27 | 2026-08-17 |
| Campaign event timestamps | 2024-08-19 | 2026-08-17 |

## Financial totals by currency

Amounts are **nominal in their recorded currencies** and are not converted to AUD. Gross booking value is before discounts. “All payment attempts” includes failed/declined retries and therefore is not settlement revenue.

| Currency | Gross booking value | Discounts | All payment attempts | Successful payments | All refund requests | Completed refunds |
|---|---:|---:|---:|---:|---:|---:|
| AUD | 473,907,470.60 | 18,658,485.40 | 471,052,060.22 | 434,335,568.50 | 18,220,649.44 | 18,140,877.41 |
| NZD | 29,671,115.58 | 1,147,287.74 | 29,559,435.83 | 27,327,460.13 | 1,162,558.82 | 1,157,128.32 |
| USD | 25,394,071.69 | 1,013,210.16 | 25,322,066.50 | 23,344,415.93 | 986,203.47 | 983,226.35 |
| EUR | 13,981,160.27 | 544,128.66 | 13,840,661.52 | 12,882,792.77 | 565,573.07 | 564,155.02 |
| GBP | 8,116,197.94 | 317,183.34 | 8,084,907.66 | 7,387,449.57 | 340,866.50 | 340,458.27 |

## Customer status distribution

| Value | Rows | Share |
|---|---:|---:|
| ACTIVE | 43,870 | 87.74% |
| INACTIVE | 4,857 | 9.71% |
| CLOSED | 1,273 | 2.55% |

## Membership status distribution

| Value | Rows | Share |
|---|---:|---:|
| EXPIRED | 30,414 | 43.45% |
| ACTIVE | 29,235 | 41.76% |
| CANCELLED | 8,591 | 12.27% |
| SUSPENDED | 1,760 | 2.51% |

## Booking status distribution

| Value | Rows | Share |
|---|---:|---:|
| COMPLETED | 291,000 | 72.75% |
| CONFIRMED | 44,000 | 11.00% |
| CANCELLED | 40,000 | 10.00% |
| PARTIALLY_REFUNDED | 15,000 | 3.75% |
| FULLY_REFUNDED | 10,000 | 2.50% |

## Payment status distribution

| Value | Rows | Share |
|---|---:|---:|
| SUCCESS | 417,915 | 92.87% |
| FAILED | 11,178 | 2.48% |
| REVERSED | 10,083 | 2.24% |
| DECLINED | 9,829 | 2.18% |
| PENDING | 995 | 0.22% |

## Refund status distribution

| Value | Rows | Share |
|---|---:|---:|
| COMPLETED | 29,657 | 98.86% |
| PENDING | 223 | 0.74% |
| REJECTED | 120 | 0.40% |

## Campaign event-type distribution

| Value | Rows | Share |
|---|---:|---:|
| SENT | 163,986 | 32.80% |
| DELIVERED | 144,171 | 28.83% |
| OPENED | 109,741 | 21.95% |
| CLICKED | 55,922 | 11.18% |
| CONVERTED | 13,059 | 2.61% |
| UNSUBSCRIBED | 6,569 | 1.31% |
| BOUNCED | 6,552 | 1.31% |

## Important assumptions

- The extract is a fictional Australian travel operation; 97% of generated customer profiles are sampled from Australian locations, with a small overseas cohort.
- All names, contact data and transaction references are synthetic. Email addresses use the reserved `.test` domain.
- Membership fees are AUD even when a later travel booking uses another currency.
- Booking discounts are generally tier-driven: PREMIUM/PLUS members receive larger discounts, while non-members may receive small tactical offers.
- The 450,000 payment rows comprise one payment attempt per booking plus 36,000 deposit/final-payment pairs and 14,000 failed/declined retry attempts.
- Financial reconciliation should be performed by currency. No FX table or implicit conversion is embedded in the source extracts.
- `created_at` and `updated_at` are local synthetic operational timestamps without a timezone suffix.
- The precise intentional exceptions are catalogued in `DATA_QUALITY_NOTES.md` and should be handled explicitly rather than silently corrected at source.

## Validation result

- PASS — 50,000 sequential unique customer primary keys.
- PASS — 70,000 memberships with valid customer foreign keys.
- PASS — 400,000 bookings with valid customer/membership ownership and 80 documented date anomalies.
- PASS — 450,000 payments with valid booking/customer ownership and bounded amounts.
- PASS — 30,000 refunds after payment, cumulatively bounded, and reconciled to booking refund statuses.
- PASS — 500,000 campaign events with valid customers and customer-owned conversion bookings.
- PASS — All six files match the requested exact row counts.
