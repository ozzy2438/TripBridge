# TripBridge Data Dictionary

All timestamps use ISO 8601 `YYYY-MM-DD HH:MM:SS` text in the CSV extracts and represent local operational time for this synthetic system. Monetary fields use decimal currency units with two fractional digits. Suggested PostgreSQL types are included for the later source-system exercise.

## customers.csv

| Column | Suggested PostgreSQL type | Business meaning |
|---|---|---|
| customer_id | varchar(12) | Stable synthetic customer primary key. |
| first_name | varchar(50) | Synthetic given name. |
| last_name | varchar(60) | Invented synthetic family name. |
| email | varchar(160) | Synthetic email under the reserved `.test` domain. |
| phone | varchar(30) | Synthetic contact number; optional. |
| date_of_birth | date | Synthetic birth date, constrained to adult customers at signup. |
| gender | varchar(24) | Self-described gender category. |
| city | varchar(80) | Customer home city. |
| state | varchar(80) | Australian state/territory code or overseas region. |
| postcode | varchar(12) | Postal code stored as text to preserve leading zeroes. |
| country | varchar(60) | Customer country; predominantly Australia. |
| signup_date | date | Date the customer profile was opened. |
| marketing_consent | boolean | Consent state; blank means source state unknown. |
| customer_status | varchar(12) | ACTIVE, INACTIVE or CLOSED. |
| created_at | timestamp | Operational row creation timestamp. |
| updated_at | timestamp | Most recent operational update timestamp. |

## memberships.csv

| Column | Suggested PostgreSQL type | Business meaning |
|---|---|---|
| membership_id | varchar(11) | Membership primary key. |
| customer_id | varchar(12) | Owning customer foreign key. |
| membership_type | varchar(12) | STANDARD, PLUS, PREMIUM or CORPORATE tier. |
| membership_start_date | date | Membership service-period start. |
| membership_end_date | date | Membership service-period end. |
| membership_status | varchar(12) | ACTIVE, EXPIRED, CANCELLED or SUSPENDED. |
| annual_fee | numeric(10,2) | Annualised membership fee in AUD. |
| renewal_type | varchar(8) | AUTO, MANUAL or NONE. |
| created_at | timestamp | Operational row creation timestamp. |
| updated_at | timestamp | Most recent membership update timestamp. |

## bookings.csv

| Column | Suggested PostgreSQL type | Business meaning |
|---|---|---|
| booking_id | varchar(12) | Booking primary key. |
| customer_id | varchar(12) | Booking customer foreign key. |
| membership_id | varchar(11) | Optional membership used at booking time. |
| booking_date | date | Date the booking was made. |
| travel_date | date | Planned first service/travel date. |
| booking_type | varchar(12) | FLIGHT, HOTEL, PACKAGE, CAR_HIRE or TOUR. |
| origin | varchar(100) | Origin/home market where relevant; optional for some products. |
| destination | varchar(100) | Travel destination. |
| passenger_count | smallint | Number of travellers covered by the booking. |
| booking_currency | char(3) | ISO-like transaction currency (AUD/NZD/USD/EUR/GBP). |
| gross_booking_amount | numeric(12,2) | Price before discounts in booking currency. |
| discount_amount | numeric(12,2) | Discount in booking currency. |
| booking_status | varchar(24) | CONFIRMED, COMPLETED, CANCELLED, PARTIALLY_REFUNDED or FULLY_REFUNDED. |
| channel | varchar(20) | WEB, MOBILE_APP, CALL_CENTRE or AGENT. |
| created_at | timestamp | Operational booking creation timestamp. |
| updated_at | timestamp | Most recent booking update timestamp. |

## payments.csv

| Column | Suggested PostgreSQL type | Business meaning |
|---|---|---|
| payment_id | varchar(12) | Payment-attempt primary key. |
| booking_id | varchar(12) | Related booking foreign key. |
| customer_id | varchar(12) | Paying customer; agrees with the booking owner. |
| payment_date | date | Date of the attempt/settlement. |
| payment_method | varchar(20) | VISA, MASTERCARD, AMEX, PAYPAL, APPLE_PAY or BANK_TRANSFER. |
| payment_currency | char(3) | Payment currency, aligned to the booking. |
| payment_amount | numeric(12,2) | Attempted or settled payment amount. |
| payment_status | varchar(12) | SUCCESS, PENDING, FAILED, DECLINED or REVERSED. |
| transaction_reference | varchar(32) | Synthetic processor transaction reference. |
| created_at | timestamp | Operational payment creation timestamp. |
| updated_at | timestamp | Most recent payment-state update. |

## refunds.csv

| Column | Suggested PostgreSQL type | Business meaning |
|---|---|---|
| refund_id | varchar(11) | Refund transaction primary key. |
| payment_id | varchar(12) | Refunded payment foreign key. |
| booking_id | varchar(12) | Related booking foreign key. |
| customer_id | varchar(12) | Refunded customer; agrees with payment and booking. |
| refund_date | date | Date refund processing began. |
| refund_amount | numeric(12,2) | Refund amount in the referenced payment currency. |
| refund_reason | varchar(28) | Operational reason category. |
| refund_status | varchar(12) | COMPLETED, PENDING or REJECTED. |
| created_at | timestamp | Operational refund creation timestamp. |
| updated_at | timestamp | Most recent refund-state update. |

## campaign_events.csv

| Column | Suggested PostgreSQL type | Business meaning |
|---|---|---|
| event_id | varchar(12) | Marketing event primary key. |
| customer_id | varchar(12) | Recipient customer foreign key. |
| campaign_id | varchar(40) | Marketing-platform campaign instance identifier. |
| campaign_name | varchar(40) | Stable campaign family name. |
| campaign_type | varchar(16) | SEASONAL, TACTICAL, MEMBER or LIFECYCLE. |
| channel | varchar(12) | EMAIL, SMS, PUSH or IN_APP; a documented casing issue exists. |
| event_type | varchar(16) | SENT, DELIVERED, OPENED, CLICKED, BOUNCED, UNSUBSCRIBED or CONVERTED. |
| event_timestamp | timestamp | Time the customer/campaign event occurred. |
| device_type | varchar(12) | MOBILE, DESKTOP or TABLET; optional. |
| offer_code | varchar(24) | Optional offer/promotion code. |
| conversion_booking_id | varchar(12) | Optional booking attributed to a CONVERTED event. |
| created_at | timestamp | Time the export row was recorded. |
