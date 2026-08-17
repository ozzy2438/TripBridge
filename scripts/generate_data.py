#!/usr/bin/env python3
"""Generate the complete deterministic TripBridge operational source dataset.

The generator deliberately uses only the Python standard library so it can run
without installing packages.  It writes CSV files incrementally, retaining only
the compact relationship indexes needed to keep the six extracts coherent.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gc
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable


SEED = 20260817
AS_OF_DATE = date(2026, 8, 17)
HISTORY_START = date(2024, 8, 17)

ROW_COUNTS = {
    "customers.csv": 50_000,
    "memberships.csv": 70_000,
    "bookings.csv": 400_000,
    "payments.csv": 450_000,
    "refunds.csv": 30_000,
    "campaign_events.csv": 500_000,
}

CUSTOMER_COUNT = ROW_COUNTS["customers.csv"]
MEMBERSHIP_COUNT = ROW_COUNTS["memberships.csv"]
BOOKING_COUNT = ROW_COUNTS["bookings.csv"]
PAYMENT_COUNT = ROW_COUNTS["payments.csv"]
REFUND_COUNT = ROW_COUNTS["refunds.csv"]
CAMPAIGN_EVENT_COUNT = ROW_COUNTS["campaign_events.csv"]

CUSTOMER_HEADER = [
    "customer_id", "first_name", "last_name", "email", "phone",
    "date_of_birth", "gender", "city", "state", "postcode", "country",
    "signup_date", "marketing_consent", "customer_status", "created_at",
    "updated_at",
]
MEMBERSHIP_HEADER = [
    "membership_id", "customer_id", "membership_type",
    "membership_start_date", "membership_end_date", "membership_status",
    "annual_fee", "renewal_type", "created_at", "updated_at",
]
BOOKING_HEADER = [
    "booking_id", "customer_id", "membership_id", "booking_date",
    "travel_date", "booking_type", "origin", "destination",
    "passenger_count", "booking_currency", "gross_booking_amount",
    "discount_amount", "booking_status", "channel", "created_at",
    "updated_at",
]
PAYMENT_HEADER = [
    "payment_id", "booking_id", "customer_id", "payment_date",
    "payment_method", "payment_currency", "payment_amount", "payment_status",
    "transaction_reference", "created_at", "updated_at",
]
REFUND_HEADER = [
    "refund_id", "payment_id", "booking_id", "customer_id", "refund_date",
    "refund_amount", "refund_reason", "refund_status", "created_at",
    "updated_at",
]
CAMPAIGN_HEADER = [
    "event_id", "customer_id", "campaign_id", "campaign_name",
    "campaign_type", "channel", "event_type", "event_timestamp",
    "device_type", "offer_code", "conversion_booking_id", "created_at",
]


FIRST_NAMES = [
    "Aaliyah", "Aiden", "Amelia", "Archer", "Aria", "Asher", "Ava",
    "Benjamin", "Billie", "Charlotte", "Chloe", "Cooper", "Daisy", "Eli",
    "Ella", "Emily", "Ethan", "Eva", "Evie", "Finn", "Florence", "Grace",
    "Hamish", "Harper", "Harry", "Hazel", "Henry", "Hudson", "Hugo",
    "Isla", "Jack", "Jasmine", "Kai", "Lachlan", "Layla", "Leo", "Levi",
    "Liam", "Lily", "Lucas", "Lucy", "Mason", "Matilda", "Maya", "Mia",
    "Mila", "Muhammad", "Noah", "Oliver", "Olivia", "Oscar", "Poppy",
    "Riley", "Ruby", "Samuel", "Scarlett", "Sienna", "Sofia", "Sophie",
    "Theodore", "Thomas", "Willow", "Xavier", "Zara", "Zoe",
]

# Invented surnames avoid tying the synthetic records to identifiable people.
LAST_NAMES = [
    "Aldermere", "Bellhaven", "Brindlewick", "Cairnley", "Coralden",
    "Dunvale", "Eastmere", "Fairwind", "Fernleigh", "Glenora", "Goldmere",
    "Harbourin", "Hawkridge", "Ironbark", "Juniperon", "Kestrelby",
    "Lakeford", "Larkspur", "Marindale", "Moonridge", "Northmere",
    "Oakenton", "Oceandell", "Pinecroft", "Queensmere", "Redgumley",
    "Riverden", "Sandermere", "Silverby", "Southwick", "Starlingon",
    "Stonehaven", "Sunvale", "Tallowmere", "Tidecroft", "Valebrook",
    "Wattleford", "Westmere", "Windermere", "Yarrabyn",
]

AU_LOCATIONS = [
    ("Sydney", "NSW", "2000", 15), ("Parramatta", "NSW", "2150", 4),
    ("Newcastle", "NSW", "2300", 3), ("Wollongong", "NSW", "2500", 2),
    ("Penrith", "NSW", "2750", 2), ("Melbourne", "VIC", "3000", 15),
    ("Geelong", "VIC", "3220", 3), ("Ballarat", "VIC", "3350", 2),
    ("Bendigo", "VIC", "3550", 2), ("Dandenong", "VIC", "3175", 2),
    ("Brisbane", "QLD", "4000", 11), ("Gold Coast", "QLD", "4217", 5),
    ("Maroochydore", "QLD", "4558", 2), ("Cairns", "QLD", "4870", 2),
    ("Townsville", "QLD", "4810", 2), ("Perth", "WA", "6000", 9),
    ("Fremantle", "WA", "6160", 2), ("Joondalup", "WA", "6027", 2),
    ("Bunbury", "WA", "6230", 1), ("Adelaide", "SA", "5000", 6),
    ("Mount Gambier", "SA", "5290", 1), ("Port Augusta", "SA", "5700", 1),
    ("Hobart", "TAS", "7000", 2), ("Launceston", "TAS", "7250", 1),
    ("Canberra", "ACT", "2600", 3), ("Darwin", "NT", "0800", 1),
    ("Alice Springs", "NT", "0870", 1),
]
OVERSEAS_LOCATIONS = [
    ("Auckland", "Auckland", "1010", "New Zealand", 30),
    ("Wellington", "Wellington", "6011", "New Zealand", 15),
    ("Singapore", "Singapore", "018956", "Singapore", 18),
    ("London", "England", "SW1A 1AA", "United Kingdom", 12),
    ("San Francisco", "CA", "94105", "United States", 8),
    ("Toronto", "ON", "M5V 2T6", "Canada", 7),
    ("Tokyo", "Tokyo", "100-0001", "Japan", 6),
    ("Dublin", "Leinster", "D02", "Ireland", 4),
]
DESTINATIONS = [
    ("Sydney, AU", 11), ("Melbourne, AU", 11), ("Brisbane, AU", 8),
    ("Gold Coast, AU", 7), ("Perth, AU", 6), ("Adelaide, AU", 5),
    ("Hobart, AU", 3), ("Cairns, AU", 5), ("Darwin, AU", 2),
    ("Auckland, NZ", 5), ("Queenstown, NZ", 4), ("Bali, ID", 6),
    ("Singapore, SG", 4), ("Tokyo, JP", 3), ("London, GB", 2),
    ("Los Angeles, US", 2), ("Paris, FR", 1), ("Rome, IT", 1),
    ("Bangkok, TH", 3), ("Fiji, FJ", 3),
]

TIER_ORDER = {"STANDARD": 0, "PLUS": 1, "PREMIUM": 2, "CORPORATE": 3}
TIER_NAMES = ["STANDARD", "PLUS", "PREMIUM", "CORPORATE"]
FEE_OPTIONS = {
    "STANDARD": [8_900, 9_900, 10_900],
    "PLUS": [17_900, 19_900, 21_900],
    "PREMIUM": [32_900, 34_900, 37_900],
    "CORPORATE": [54_900, 59_900, 64_900],
}

STATUS_CODE = {
    "COMPLETED": 0,
    "CONFIRMED": 1,
    "CANCELLED": 2,
    "PARTIALLY_REFUNDED": 3,
    "FULLY_REFUNDED": 4,
}
STATUS_FROM_CODE = {value: key for key, value in STATUS_CODE.items()}


@dataclass(slots=True)
class CustomerRef:
    signup_date: date
    city: str
    country: str
    status: str
    marketing_consent: str


@dataclass(slots=True)
class MembershipRef:
    number: int
    start_date: date
    end_date: date
    membership_type: str
    status: str


@dataclass(slots=True)
class BookingRef:
    customer_number: int
    booking_date: date
    travel_date: date
    currency: str
    net_amount_cents: int
    status: str


@dataclass(slots=True)
class PaymentRef:
    number: int
    payment_date: date
    amount_cents: int
    currency: str


def customer_id(number: int) -> str:
    return f"CUST{number:08d}"


def membership_id(number: int) -> str:
    return f"MEM{number:08d}"


def booking_id(number: int) -> str:
    return f"BKG{number:09d}"


def payment_id(number: int) -> str:
    return f"PAY{number:09d}"


def refund_id(number: int) -> str:
    return f"REF{number:08d}"


def event_id(number: int) -> str:
    return f"EVT{number:09d}"


def money(cents: int) -> str:
    return f"{cents / 100:.2f}"


def iso_timestamp(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat(sep=" ")


def random_datetime(rng: random.Random, day: date, start_hour: int = 7, end_hour: int = 22) -> datetime:
    start_seconds = start_hour * 3600
    end_seconds = end_hour * 3600 + 3599
    return datetime.combine(day, time()) + timedelta(seconds=rng.randint(start_seconds, end_seconds))


def clamp_datetime(value: datetime) -> datetime:
    return min(value, datetime.combine(AS_OF_DATE, time(23, 59, 59)))


def weighted_choice(rng: random.Random, values: list, weights: list[int | float]):
    return rng.choices(values, weights=weights, k=1)[0]


def weighted_date(rng: random.Random, start: date, end: date) -> date:
    """Sample a date with Australian summer/holiday seasonality."""
    if end <= start:
        return start
    span = (end - start).days
    while True:
        candidate = start + timedelta(days=rng.randint(0, span))
        month_weight = {
            1: 1.75, 2: 1.20, 3: 1.05, 4: 1.25,
            5: 0.90, 6: 1.20, 7: 1.25, 8: 0.95,
            9: 1.18, 10: 1.05, 11: 1.32, 12: 1.85,
        }[candidate.month]
        # Fridays and weekends carry more leisure demand.
        weekday_weight = 1.12 if candidate.weekday() >= 4 else 1.0
        if rng.random() <= (month_weight * weekday_weight) / (1.85 * 1.12):
            return candidate


def choose_location(rng: random.Random):
    if rng.random() < 0.97:
        loc = weighted_choice(rng, AU_LOCATIONS, [x[3] for x in AU_LOCATIONS])
        return loc[0], loc[1], loc[2], "Australia"
    loc = weighted_choice(rng, OVERSEAS_LOCATIONS, [x[4] for x in OVERSEAS_LOCATIONS])
    return loc[0], loc[1], loc[2], loc[3]


def choose_destination(rng: random.Random, origin_city: str) -> str:
    for _ in range(5):
        candidate = weighted_choice(rng, DESTINATIONS, [x[1] for x in DESTINATIONS])[0]
        if not candidate.startswith(origin_city + ","):
            return candidate
    return "Gold Coast, AU"


def date_counter_update(bounds: dict[str, date | None], value: date) -> None:
    if bounds["min"] is None or value < bounds["min"]:
        bounds["min"] = value
    if bounds["max"] is None or value > bounds["max"]:
        bounds["max"] = value


def write_csv_header(path: Path, header: list[str]):
    handle = path.open("w", newline="", encoding="utf-8")
    writer = csv.DictWriter(handle, fieldnames=header, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    return handle, writer


def generate_customers(data_dir: Path, rng: random.Random):
    null_phone_indices = set(rng.sample(range(CUSTOMER_COUNT - 25), 750))
    null_consent_indices = set(rng.sample(
        [i for i in range(CUSTOMER_COUNT - 25) if i not in null_phone_indices], 250
    ))
    uppercase_email_indices = set(rng.sample(
        [i for i in range(50, CUSTOMER_COUNT - 25)
         if i not in null_consent_indices], 120
    ))
    duplicate_sources = list(range(25))
    duplicate_targets = list(range(CUSTOMER_COUNT - 25, CUSTOMER_COUNT))
    duplicate_map = dict(zip(duplicate_targets, duplicate_sources))

    rows: list[dict[str, str]] = []
    status_counts: Counter[str] = Counter()
    country_counts: Counter[str] = Counter()
    signup_bounds: dict[str, date | None] = {"min": None, "max": None}

    for idx in range(CUSTOMER_COUNT):
        if idx in duplicate_map:
            source = rows[duplicate_map[idx]].copy()
            source["customer_id"] = customer_id(idx + 1)
            rows.append(source)
            status_counts[source["customer_status"]] += 1
            country_counts[source["country"]] += 1
            date_counter_update(signup_bounds, date.fromisoformat(source["signup_date"]))
            continue

        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        city, state, postcode, country = choose_location(rng)
        history_days = (AS_OF_DATE - HISTORY_START).days
        signup_offset = int(rng.betavariate(1.05, 1.30) * history_days)
        signup = HISTORY_START + timedelta(days=signup_offset)
        age = int(rng.triangular(18, 82, 39))
        dob = signup - timedelta(days=int(age * 365.2425) + rng.randint(0, 364))
        gender = weighted_choice(
            rng,
            ["FEMALE", "MALE", "NON_BINARY", "PREFER_NOT_TO_SAY"],
            [49, 48, 1.5, 1.5],
        )
        consent = "" if idx in null_consent_indices else (
            "true" if rng.random() < 0.765 else "false"
        )
        status = weighted_choice(rng, ["ACTIVE", "INACTIVE", "CLOSED"], [88, 9.5, 2.5])
        email = f"{first.lower()}.{last.lower()}.{idx + 1:05d}@example.test"
        if idx in uppercase_email_indices:
            email = email.upper()
        if idx in null_phone_indices:
            phone = ""
        elif country == "Australia":
            phone = f"+61 490 {idx // 1000:03d} {idx % 1000:03d}"
        else:
            phone = f"+999 700 {idx // 1000:03d} {idx % 1000:03d}"
        created = random_datetime(rng, signup)
        available_days = max(0, (AS_OF_DATE - signup).days)
        if status == "ACTIVE":
            update_days = min(available_days, rng.randint(0, 45))
        else:
            update_days = rng.randint(0, available_days) if available_days else 0
        updated = clamp_datetime(created + timedelta(days=update_days, minutes=rng.randint(0, 600)))
        row = {
            "customer_id": customer_id(idx + 1),
            "first_name": first,
            "last_name": last,
            "email": email,
            "phone": phone,
            "date_of_birth": dob.isoformat(),
            "gender": gender,
            "city": city,
            "state": state,
            "postcode": postcode,
            "country": country,
            "signup_date": signup.isoformat(),
            "marketing_consent": consent,
            "customer_status": status,
            "created_at": iso_timestamp(created),
            "updated_at": iso_timestamp(updated),
        }
        rows.append(row)
        status_counts[status] += 1
        country_counts[country] += 1
        date_counter_update(signup_bounds, signup)

    handle, writer = write_csv_header(data_dir / "customers.csv", CUSTOMER_HEADER)
    with handle:
        writer.writerows(rows)

    refs = [
        CustomerRef(
            signup_date=date.fromisoformat(row["signup_date"]),
            city=row["city"],
            country=row["country"],
            status=row["customer_status"],
            marketing_consent=row["marketing_consent"],
        )
        for row in rows
    ]
    stats = {
        "status_counts": status_counts,
        "country_counts": country_counts,
        "signup_bounds": signup_bounds,
        "null_phone_count": sum(not row["phone"] for row in rows),
        "null_consent_count": sum(not row["marketing_consent"] for row in rows),
        "uppercase_email_count": sum(row["email"] != row["email"].lower() for row in rows),
        "natural_duplicate_pairs": len(duplicate_map),
    }
    return refs, stats


def generate_memberships(data_dir: Path, rng: random.Random, customers: list[CustomerRef]):
    sorted_customers = sorted(range(CUSTOMER_COUNT), key=lambda i: customers[i].signup_date)
    three_memberships = sorted_customers[:4_000]
    two_memberships = sorted_customers[4_000:25_000]
    one_membership = rng.sample(sorted_customers[25_000:], 16_000)
    allocation = {idx: 3 for idx in three_memberships}
    allocation.update({idx: 2 for idx in two_memberships})
    allocation.update({idx: 1 for idx in one_membership})
    assert sum(allocation.values()) == MEMBERSHIP_COUNT

    memberships_by_customer: dict[int, list[MembershipRef]] = defaultdict(list)
    highest_tier = [None] * CUSTOMER_COUNT
    status_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    date_bounds: dict[str, date | None] = {"min": None, "max": None}
    member_number = 0

    handle, writer = write_csv_header(data_dir / "memberships.csv", MEMBERSHIP_HEADER)
    with handle:
        for customer_num in sorted(allocation):
            count = allocation[customer_num]
            signup = customers[customer_num].signup_date
            start = min(AS_OF_DATE, signup + timedelta(days=rng.randint(0, 14)))
            tier_idx = weighted_choice(rng, [0, 1, 2, 3], [57, 28, 12, 3])

            for position in range(count):
                member_number += 1
                if position > 0:
                    upgrade_roll = rng.random()
                    if upgrade_roll < 0.28 and tier_idx < 3:
                        tier_idx += 1
                    elif upgrade_roll > 0.96 and tier_idx > 0:
                        tier_idx -= 1
                member_type = TIER_NAMES[tier_idx]
                if position < count - 1:
                    duration = rng.randint(125, 265) if count == 3 else rng.randint(210, 335)
                else:
                    duration = rng.choice([335, 350, 365, 365, 380])
                end = start + timedelta(days=duration)

                if position < count - 1:
                    status = weighted_choice(rng, ["EXPIRED", "CANCELLED"], [87, 13])
                elif end >= AS_OF_DATE:
                    status = weighted_choice(rng, ["ACTIVE", "CANCELLED", "SUSPENDED"], [84, 11, 5])
                else:
                    status = weighted_choice(rng, ["EXPIRED", "CANCELLED"], [83, 17])
                if status == "ACTIVE":
                    renewal_type = weighted_choice(rng, ["AUTO", "MANUAL"], [72, 28])
                elif status == "SUSPENDED":
                    renewal_type = weighted_choice(rng, ["AUTO", "MANUAL", "NONE"], [35, 35, 30])
                else:
                    renewal_type = weighted_choice(rng, ["MANUAL", "NONE"], [38, 62])
                fee_cents = rng.choice(FEE_OPTIONS[member_type])
                created = random_datetime(rng, start)
                if status == "ACTIVE":
                    updated_day = min(AS_OF_DATE, start + timedelta(days=rng.randint(0, min(90, max(0, (AS_OF_DATE - start).days)))))
                else:
                    terminal_day = min(AS_OF_DATE, end)
                    updated_day = max(start, terminal_day - timedelta(days=rng.randint(0, 10)))
                updated = clamp_datetime(random_datetime(rng, updated_day))

                writer.writerow({
                    "membership_id": membership_id(member_number),
                    "customer_id": customer_id(customer_num + 1),
                    "membership_type": member_type,
                    "membership_start_date": start.isoformat(),
                    "membership_end_date": end.isoformat(),
                    "membership_status": status,
                    "annual_fee": money(fee_cents),
                    "renewal_type": renewal_type,
                    "created_at": iso_timestamp(created),
                    "updated_at": iso_timestamp(max(created, updated)),
                })
                memberships_by_customer[customer_num].append(MembershipRef(
                    number=member_number,
                    start_date=start,
                    end_date=end,
                    membership_type=member_type,
                    status=status,
                ))
                if highest_tier[customer_num] is None or tier_idx > TIER_ORDER[highest_tier[customer_num]]:
                    highest_tier[customer_num] = member_type
                status_counts[status] += 1
                type_counts[member_type] += 1
                date_counter_update(date_bounds, start)
                date_counter_update(date_bounds, end)
                start = end + timedelta(days=rng.randint(0, 12))

    stats = {
        "status_counts": status_counts,
        "type_counts": type_counts,
        "date_bounds": date_bounds,
        "customers_with_membership": len(allocation),
        "customers_without_membership": CUSTOMER_COUNT - len(allocation),
    }
    return memberships_by_customer, highest_tier, stats


def membership_for_booking(
    rng: random.Random,
    customer_num: int,
    booking_day: date,
    memberships_by_customer: dict[int, list[MembershipRef]],
):
    eligible = [
        item for item in memberships_by_customer.get(customer_num, [])
        if item.status in {"ACTIVE", "EXPIRED"}
        and item.start_date <= booking_day <= item.end_date
    ]
    if not eligible or rng.random() < 0.085:
        return None
    return eligible[-1]


def booking_amount_cents(rng: random.Random, booking_type: str, passengers: int) -> int:
    params = {
        "FLIGHT": (math.log(520), 0.50, 0.55),
        "HOTEL": (math.log(760), 0.55, 0.24),
        "PACKAGE": (math.log(2_150), 0.52, 0.62),
        "CAR_HIRE": (math.log(470), 0.48, 0.12),
        "TOUR": (math.log(390), 0.52, 0.42),
    }
    mean_log, sigma, passenger_scale = params[booking_type]
    amount = rng.lognormvariate(mean_log, sigma) * (1 + passenger_scale * (passengers - 1))
    return max(5_000, min(2_500_000, int(round(amount * 100))))


def discount_rate(rng: random.Random, member: MembershipRef | None) -> float:
    if member is None:
        return 0.0 if rng.random() < 0.72 else rng.uniform(0.01, 0.035)
    ranges = {
        "STANDARD": (0.02, 0.055),
        "PLUS": (0.04, 0.085),
        "PREMIUM": (0.065, 0.13),
        "CORPORATE": (0.055, 0.115),
    }
    low, high = ranges[member.membership_type]
    return rng.uniform(low, high)


def generate_bookings(
    data_dir: Path,
    rng: random.Random,
    customers: list[CustomerRef],
    memberships_by_customer: dict[int, list[MembershipRef]],
    highest_tier: list[str | None],
):
    shuffled = list(range(BOOKING_COUNT))
    rng.shuffle(shuffled)
    status_codes = bytearray([STATUS_CODE["COMPLETED"]]) * BOOKING_COUNT
    full_indices = shuffled[:10_000]
    partial_indices = shuffled[10_000:25_000]
    cancelled_indices = shuffled[25_000:65_000]
    confirmed_indices = shuffled[65_000:109_000]
    for idx in full_indices:
        status_codes[idx] = STATUS_CODE["FULLY_REFUNDED"]
    for idx in partial_indices:
        status_codes[idx] = STATUS_CODE["PARTIALLY_REFUNDED"]
    for idx in cancelled_indices:
        status_codes[idx] = STATUS_CODE["CANCELLED"]
    for idx in confirmed_indices:
        status_codes[idx] = STATUS_CODE["CONFIRMED"]

    late_update_indices = set(rng.sample(
        [i for i in range(BOOKING_COUNT) if status_codes[i] == STATUS_CODE["COMPLETED"]],
        600,
    ))
    travel_anomaly_indices = set(rng.sample(
        [i for i in range(BOOKING_COUNT)
         if status_codes[i] in {STATUS_CODE["COMPLETED"], STATUS_CODE["CANCELLED"]}
         and i not in late_update_indices],
        80,
    ))

    no_booking_customers = set(rng.sample(range(CUSTOMER_COUNT), 6_000))
    booker_population = [i for i in range(CUSTOMER_COUNT) if i not in no_booking_customers]
    activity_weights = []
    for customer_num in booker_population:
        tier = highest_tier[customer_num]
        tier_multiplier = {None: 0.82, "STANDARD": 1.0, "PLUS": 1.18, "PREMIUM": 1.42, "CORPORATE": 1.35}[tier]
        status_multiplier = {"ACTIVE": 1.0, "INACTIVE": 0.48, "CLOSED": 0.15}[customers[customer_num].status]
        activity_weights.append(min(18.0, max(0.03, rng.lognormvariate(0.0, 1.05))) * tier_multiplier * status_multiplier)
    chosen_customers = rng.choices(booker_population, weights=activity_weights, k=BOOKING_COUNT)
    eligible_completed = [i for i in booker_population if customers[i].signup_date <= AS_OF_DATE - timedelta(days=2)]
    eligible_refunded = [i for i in booker_population if customers[i].signup_date <= AS_OF_DATE - timedelta(days=10)]
    eligible_anomaly = [i for i in booker_population if customers[i].signup_date <= AS_OF_DATE - timedelta(days=3)]
    eligible_late_update = [
        i for i in booker_population
        if customers[i].signup_date <= AS_OF_DATE - timedelta(days=180)
    ]

    bookings: list[BookingRef] = []
    bookings_by_customer: dict[int, list[tuple[int, date]]] = defaultdict(list)
    status_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    currency_counts: Counter[str] = Counter()
    channel_counts: Counter[str] = Counter()
    gross_by_currency: Counter[str] = Counter()
    discount_by_currency: Counter[str] = Counter()
    date_bounds: dict[str, date | None] = {"min": None, "max": None}
    missing_membership_count = 0
    missing_origin_count = 0
    booking_customer_counts: Counter[int] = Counter()

    handle, writer = write_csv_header(data_dir / "bookings.csv", BOOKING_HEADER)
    with handle:
        for idx in range(BOOKING_COUNT):
            status = STATUS_FROM_CODE[status_codes[idx]]
            customer_num = chosen_customers[idx]
            if status == "COMPLETED" and customers[customer_num].signup_date > AS_OF_DATE - timedelta(days=2):
                customer_num = rng.choice(eligible_completed)
            if status in {"PARTIALLY_REFUNDED", "FULLY_REFUNDED"} and customers[customer_num].signup_date > AS_OF_DATE - timedelta(days=10):
                customer_num = rng.choice(eligible_refunded)
            if idx in travel_anomaly_indices:
                customer_num = rng.choice(eligible_anomaly)
            if idx in late_update_indices:
                customer_num = rng.choice(eligible_late_update)

            signup = customers[customer_num].signup_date
            if idx in late_update_indices:
                booking_day = weighted_date(rng, signup, AS_OF_DATE - timedelta(days=180))
            elif status == "CONFIRMED":
                booking_day = weighted_date(rng, max(signup, AS_OF_DATE - timedelta(days=330)), AS_OF_DATE)
            elif status in {"PARTIALLY_REFUNDED", "FULLY_REFUNDED"}:
                booking_day = weighted_date(rng, signup, AS_OF_DATE - timedelta(days=8))
            elif status == "COMPLETED":
                booking_day = weighted_date(rng, signup, AS_OF_DATE - timedelta(days=1))
            else:
                booking_day = weighted_date(rng, signup, AS_OF_DATE)

            if idx in travel_anomaly_indices:
                booking_day = weighted_date(rng, signup + timedelta(days=2), AS_OF_DATE)
                travel_day = booking_day - timedelta(days=rng.choice([1, 1, 2]))
            elif status == "CONFIRMED":
                travel_day = AS_OF_DATE + timedelta(days=rng.randint(1, 300))
            elif status == "COMPLETED":
                lead_max = max(1, min(210, (AS_OF_DATE - booking_day).days))
                travel_day = booking_day + timedelta(days=rng.randint(1, lead_max))
            else:
                travel_day = booking_day + timedelta(days=rng.randint(2, 270))

            member = membership_for_booking(rng, customer_num, booking_day, memberships_by_customer)
            member_value = membership_id(member.number) if member else ""
            if not member_value:
                missing_membership_count += 1
            booking_type = weighted_choice(
                rng, ["FLIGHT", "HOTEL", "PACKAGE", "CAR_HIRE", "TOUR"],
                [34, 30, 15, 12, 9],
            )
            passengers = weighted_choice(rng, [1, 2, 3, 4, 5, 6], [38, 39, 10, 9, 2.5, 1.5])
            gross_cents = booking_amount_cents(rng, booking_type, passengers)
            discount_cents = int(round(gross_cents * discount_rate(rng, member)))
            discount_cents = min(discount_cents, gross_cents - 1)
            currency = weighted_choice(rng, ["AUD", "NZD", "USD", "EUR", "GBP"], [86, 5.5, 4.5, 2.5, 1.5])
            channel = weighted_choice(rng, ["WEB", "MOBILE_APP", "CALL_CENTRE", "AGENT"], [43, 38, 12, 7])
            origin = f"{customers[customer_num].city}, {'AU' if customers[customer_num].country == 'Australia' else customers[customer_num].country}"
            if booking_type in {"HOTEL", "CAR_HIRE", "TOUR"} and rng.random() < 0.12:
                origin = ""
                missing_origin_count += 1
            destination = choose_destination(rng, customers[customer_num].city)
            created = random_datetime(rng, booking_day)
            if idx in late_update_indices:
                updated_day = AS_OF_DATE - timedelta(days=rng.randint(0, 8))
                updated = random_datetime(rng, updated_day)
            elif status == "COMPLETED":
                updated_day = min(AS_OF_DATE, travel_day + timedelta(days=rng.randint(0, 5)))
                updated = random_datetime(rng, updated_day)
            else:
                max_age = max(0, (AS_OF_DATE - booking_day).days)
                updated = created + timedelta(days=rng.randint(0, min(45, max_age)), minutes=rng.randint(0, 800))
                updated = clamp_datetime(updated)
            updated = max(created, updated)

            number = idx + 1
            writer.writerow({
                "booking_id": booking_id(number),
                "customer_id": customer_id(customer_num + 1),
                "membership_id": member_value,
                "booking_date": booking_day.isoformat(),
                "travel_date": travel_day.isoformat(),
                "booking_type": booking_type,
                "origin": origin,
                "destination": destination,
                "passenger_count": passengers,
                "booking_currency": currency,
                "gross_booking_amount": money(gross_cents),
                "discount_amount": money(discount_cents),
                "booking_status": status,
                "channel": channel,
                "created_at": iso_timestamp(created),
                "updated_at": iso_timestamp(updated),
            })
            bookings.append(BookingRef(
                customer_number=customer_num,
                booking_date=booking_day,
                travel_date=travel_day,
                currency=currency,
                net_amount_cents=gross_cents - discount_cents,
                status=status,
            ))
            bookings_by_customer[customer_num].append((number, booking_day))
            booking_customer_counts[customer_num] += 1
            status_counts[status] += 1
            type_counts[booking_type] += 1
            currency_counts[currency] += 1
            channel_counts[channel] += 1
            gross_by_currency[currency] += gross_cents
            discount_by_currency[currency] += discount_cents
            date_counter_update(date_bounds, booking_day)
            date_counter_update(date_bounds, travel_day)

    stats = {
        "status_counts": status_counts,
        "type_counts": type_counts,
        "currency_counts": currency_counts,
        "channel_counts": channel_counts,
        "gross_by_currency": gross_by_currency,
        "discount_by_currency": discount_by_currency,
        "date_bounds": date_bounds,
        "missing_membership_count": missing_membership_count,
        "missing_origin_count": missing_origin_count,
        "travel_anomaly_count": len(travel_anomaly_indices),
        "late_update_count": len(late_update_indices),
        "customers_with_bookings": len(booking_customer_counts),
        "customers_with_one_booking": sum(value == 1 for value in booking_customer_counts.values()),
        "max_bookings_for_one_customer": max(booking_customer_counts.values()),
        "full_indices": full_indices,
        "partial_indices": partial_indices,
    }
    return bookings, bookings_by_customer, stats


def generate_payments(data_dir: Path, rng: random.Random, bookings: list[BookingRef]):
    eligible_extra = [i for i, item in enumerate(bookings) if item.status != "CANCELLED"]
    split_indices = set(rng.sample(eligible_extra, 36_000))
    remaining = [i for i in eligible_extra if i not in split_indices]
    retry_indices = set(rng.sample(remaining, 14_000))
    assert len(split_indices) + len(retry_indices) == PAYMENT_COUNT - BOOKING_COUNT

    methods = ["VISA", "MASTERCARD", "AMEX", "PAYPAL", "APPLE_PAY", "BANK_TRANSFER"]
    method_weights = [34, 29, 8, 13, 11, 5]
    status_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    amount_by_currency: Counter[str] = Counter()
    successful_by_currency: Counter[str] = Counter()
    date_bounds: dict[str, date | None] = {"min": None, "max": None}
    refund_payment_map: dict[int, list[PaymentRef]] = defaultdict(list)
    payment_number = 0

    handle, writer = write_csv_header(data_dir / "payments.csv", PAYMENT_HEADER)

    def emit_payment(booking_index: int, pay_day: date, amount_cents: int, status: str):
        nonlocal payment_number
        item = bookings[booking_index]
        payment_number += 1
        method = weighted_choice(rng, methods, method_weights)
        created = random_datetime(rng, pay_day)
        if status in {"PENDING", "SUCCESS"}:
            updated = clamp_datetime(created + timedelta(minutes=rng.randint(0, 240)))
        else:
            updated = clamp_datetime(created + timedelta(minutes=rng.randint(1, 1_440)))
        writer.writerow({
            "payment_id": payment_id(payment_number),
            "booking_id": booking_id(booking_index + 1),
            "customer_id": customer_id(item.customer_number + 1),
            "payment_date": pay_day.isoformat(),
            "payment_method": method,
            "payment_currency": item.currency,
            "payment_amount": money(amount_cents),
            "payment_status": status,
            "transaction_reference": f"TBP{pay_day:%y%m%d}{payment_number:09d}",
            "created_at": iso_timestamp(created),
            "updated_at": iso_timestamp(max(created, updated)),
        })
        status_counts[status] += 1
        method_counts[method] += 1
        amount_by_currency[item.currency] += amount_cents
        if status == "SUCCESS":
            successful_by_currency[item.currency] += amount_cents
            if item.status in {"PARTIALLY_REFUNDED", "FULLY_REFUNDED"}:
                refund_payment_map[booking_index].append(PaymentRef(
                    number=payment_number,
                    payment_date=pay_day,
                    amount_cents=amount_cents,
                    currency=item.currency,
                ))
        date_counter_update(date_bounds, pay_day)

    with handle:
        for booking_index, item in enumerate(bookings):
            net = item.net_amount_cents
            if booking_index in split_indices:
                deposit = max(1, int(round(net * rng.uniform(0.20, 0.42))))
                deposit = min(deposit, net - 1)
                emit_payment(booking_index, item.booking_date, deposit, "SUCCESS")
                latest = AS_OF_DATE - timedelta(days=2) if item.status in {"PARTIALLY_REFUNDED", "FULLY_REFUNDED"} else AS_OF_DATE
                final_day = min(latest, item.booking_date + timedelta(days=rng.randint(7, 75)))
                final_day = max(item.booking_date, final_day)
                emit_payment(booking_index, final_day, net - deposit, "SUCCESS")
            elif booking_index in retry_indices:
                failed_status = weighted_choice(rng, ["FAILED", "DECLINED"], [52, 48])
                emit_payment(booking_index, item.booking_date, net, failed_status)
                retry_day = min(AS_OF_DATE, item.booking_date + timedelta(days=rng.randint(0, 3)))
                emit_payment(booking_index, retry_day, net, "SUCCESS")
            else:
                if item.status == "CANCELLED":
                    status = weighted_choice(rng, ["SUCCESS", "REVERSED", "FAILED", "DECLINED"], [60, 25, 8, 7])
                elif item.status == "CONFIRMED":
                    status = weighted_choice(rng, ["SUCCESS", "PENDING", "FAILED", "DECLINED"], [95, 2.5, 1.5, 1])
                else:
                    status = "SUCCESS"
                pay_day = item.booking_date
                if item.status in {"PARTIALLY_REFUNDED", "FULLY_REFUNDED"}:
                    pay_day = min(pay_day, AS_OF_DATE - timedelta(days=2))
                emit_payment(booking_index, pay_day, net, status)

    assert payment_number == PAYMENT_COUNT
    stats = {
        "status_counts": status_counts,
        "method_counts": method_counts,
        "amount_by_currency": amount_by_currency,
        "successful_by_currency": successful_by_currency,
        "date_bounds": date_bounds,
        "split_booking_count": len(split_indices),
        "retry_booking_count": len(retry_indices),
    }
    return refund_payment_map, stats


def generate_refunds(
    data_dir: Path,
    rng: random.Random,
    bookings: list[BookingRef],
    refund_payment_map: dict[int, list[PaymentRef]],
    full_indices: list[int],
    partial_indices: list[int],
):
    full_set = set(full_indices)
    refundable_indices = full_indices + partial_indices
    mandatory_two = {idx for idx in full_indices if len(refund_payment_map[idx]) > 1}
    extra_needed = 5_000 - len(mandatory_two)
    if extra_needed < 0:
        raise RuntimeError("More mandatory split refunds than the 30,000-row design permits")
    optional_pool = [idx for idx in refundable_indices if idx not in mandatory_two]
    two_refund_indices = mandatory_two | set(rng.sample(optional_pool, extra_needed))
    assert len(two_refund_indices) == 5_000

    reasons = [
        "CUSTOMER_CANCELLED", "AIRLINE_CANCELLED", "SERVICE_FAILURE",
        "DUPLICATE_PAYMENT", "PRICE_ADJUSTMENT", "PARTIAL_SERVICE_REFUND", "OTHER",
    ]
    reason_weights = [41, 19, 10, 4, 7, 15, 4]
    status_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    amount_by_currency: Counter[str] = Counter()
    completed_by_currency: Counter[str] = Counter()
    date_bounds: dict[str, date | None] = {"min": None, "max": None}
    refund_number = 0

    handle, writer = write_csv_header(data_dir / "refunds.csv", REFUND_HEADER)
    with handle:
        for booking_index in refundable_indices:
            item = bookings[booking_index]
            payments = refund_payment_map[booking_index]
            if not payments:
                raise RuntimeError(f"Refundable booking {booking_index + 1} has no successful payment")
            total_paid = sum(payment.amount_cents for payment in payments)
            refund_count = 2 if booking_index in two_refund_indices else 1
            allocations: list[tuple[PaymentRef, int]]

            if booking_index in full_set:
                if len(payments) == 2:
                    allocations = [(payments[0], payments[0].amount_cents), (payments[1], payments[1].amount_cents)]
                elif refund_count == 2:
                    first_amount = max(1, int(round(total_paid * rng.uniform(0.28, 0.62))))
                    first_amount = min(first_amount, total_paid - 1)
                    allocations = [(payments[0], first_amount), (payments[0], total_paid - first_amount)]
                else:
                    allocations = [(payments[0], total_paid)]
            else:
                largest = max(payments, key=lambda payment: payment.amount_cents)
                target = int(round(total_paid * rng.uniform(0.10, 0.68)))
                target = max(1, min(target, int(largest.amount_cents * 0.80)))
                if refund_count == 2:
                    first_amount = max(1, int(round(target * rng.uniform(0.35, 0.65))))
                    first_amount = min(first_amount, target - 1)
                    allocations = [(largest, first_amount), (largest, target - first_amount)]
                else:
                    allocations = [(largest, target)]

            for allocation_index, (payment, amount_cents) in enumerate(allocations):
                refund_number += 1
                if booking_index in full_set or allocation_index == 0:
                    status = "COMPLETED"
                else:
                    status = weighted_choice(rng, ["COMPLETED", "PENDING", "REJECTED"], [86, 9, 5])
                reason = weighted_choice(rng, reasons, reason_weights)
                available_days = (AS_OF_DATE - payment.payment_date).days
                if available_days < 1:
                    raise RuntimeError("Refund payment date is too close to the as-of date")
                refund_day = payment.payment_date + timedelta(days=rng.randint(1, min(45, available_days)))
                created = random_datetime(rng, refund_day)
                updated = clamp_datetime(created + timedelta(days=rng.randint(0, min(5, (AS_OF_DATE - refund_day).days)), minutes=rng.randint(0, 300)))
                writer.writerow({
                    "refund_id": refund_id(refund_number),
                    "payment_id": payment_id(payment.number),
                    "booking_id": booking_id(booking_index + 1),
                    "customer_id": customer_id(item.customer_number + 1),
                    "refund_date": refund_day.isoformat(),
                    "refund_amount": money(amount_cents),
                    "refund_reason": reason,
                    "refund_status": status,
                    "created_at": iso_timestamp(created),
                    "updated_at": iso_timestamp(max(created, updated)),
                })
                status_counts[status] += 1
                reason_counts[reason] += 1
                amount_by_currency[payment.currency] += amount_cents
                if status == "COMPLETED":
                    completed_by_currency[payment.currency] += amount_cents
                date_counter_update(date_bounds, refund_day)

    assert refund_number == REFUND_COUNT
    stats = {
        "status_counts": status_counts,
        "reason_counts": reason_counts,
        "amount_by_currency": amount_by_currency,
        "completed_by_currency": completed_by_currency,
        "date_bounds": date_bounds,
        "bookings_with_refunds": len(refundable_indices),
        "bookings_with_multiple_refunds": len(two_refund_indices),
    }
    return stats


CAMPAIGN_TYPE = {
    "SUMMER_ESCAPE": "SEASONAL",
    "EOFY_TRAVEL": "SEASONAL",
    "WEEKEND_GETAWAY": "TACTICAL",
    "PREMIUM_MEMBER_OFFER": "MEMBER",
    "NEW_MEMBER_WELCOME": "LIFECYCLE",
    "WINTER_CITY_BREAK": "SEASONAL",
}
OFFER_CODES = {
    "SUMMER_ESCAPE": "SUMMER10",
    "EOFY_TRAVEL": "EOFY75",
    "WEEKEND_GETAWAY": "WKND50",
    "PREMIUM_MEMBER_OFFER": "PREMIUM12",
    "NEW_MEMBER_WELCOME": "WELCOME40",
    "WINTER_CITY_BREAK": "WINTER8",
}


def choose_campaign_name(
    rng: random.Random,
    event_day: date,
    signup_day: date,
    highest_tier: str | None,
) -> str:
    if 0 <= (event_day - signup_day).days <= 14 and rng.random() < 0.32:
        return "NEW_MEMBER_WELCOME"
    if highest_tier in {"PREMIUM", "CORPORATE"} and rng.random() < 0.17:
        return "PREMIUM_MEMBER_OFFER"
    if event_day.month in {11, 12, 1, 2}:
        return weighted_choice(rng, ["SUMMER_ESCAPE", "WEEKEND_GETAWAY"], [72, 28])
    if event_day.month in {5, 6}:
        return weighted_choice(rng, ["EOFY_TRAVEL", "WINTER_CITY_BREAK", "WEEKEND_GETAWAY"], [48, 34, 18])
    if event_day.month in {4, 7, 8}:
        return weighted_choice(rng, ["WINTER_CITY_BREAK", "WEEKEND_GETAWAY"], [68, 32])
    return "WEEKEND_GETAWAY"


def campaign_sequence(rng: random.Random, remaining: int) -> list[str]:
    sequences = [
        ["SENT"],
        ["SENT", "BOUNCED"],
        ["SENT", "DELIVERED"],
        ["SENT", "DELIVERED", "OPENED"],
        ["SENT", "DELIVERED", "OPENED", "CLICKED"],
        ["SENT", "DELIVERED", "OPENED", "CLICKED", "CONVERTED"],
        ["SENT", "DELIVERED", "OPENED", "UNSUBSCRIBED"],
    ]
    selected = weighted_choice(rng, sequences, [8, 4, 21, 29, 26, 8, 4])
    if len(selected) <= remaining:
        return selected
    # Every prefix is a valid partial journey and closes the exact row quota.
    return ["SENT", "DELIVERED", "OPENED", "CLICKED", "CONVERTED"][:remaining]


def campaign_device(rng: random.Random, channel: str) -> str:
    if channel == "SMS":
        return "MOBILE"
    if channel == "PUSH":
        return weighted_choice(rng, ["MOBILE", "TABLET"], [92, 8])
    if channel == "IN_APP":
        return weighted_choice(rng, ["MOBILE", "TABLET"], [88, 12])
    return weighted_choice(rng, ["MOBILE", "DESKTOP", "TABLET"], [49, 45, 6])


def generate_campaign_events(
    data_dir: Path,
    rng: random.Random,
    customers: list[CustomerRef],
    highest_tier: list[str | None],
    bookings_by_customer: dict[int, list[tuple[int, date]]],
):
    base_event_target = CAMPAIGN_EVENT_COUNT - 200
    duplicate_after_positions = set(rng.sample(range(1, base_event_target), 200))
    casing_event_numbers = set(rng.sample(range(1, CAMPAIGN_EVENT_COUNT + 1), 500))
    consented = [i for i, item in enumerate(customers) if item.marketing_consent == "true"]
    suppressed = [i for i, item in enumerate(customers) if item.marketing_consent != "true"]
    consented_converters = [i for i in consented if bookings_by_customer.get(i)]
    suppressed_converters = [i for i in suppressed if bookings_by_customer.get(i)]

    event_type_counts: Counter[str] = Counter()
    channel_counts: Counter[str] = Counter()
    campaign_counts: Counter[str] = Counter()
    date_bounds: dict[str, date | None] = {"min": None, "max": None}
    output_event_number = 0
    base_position = 0
    journey_number = 0
    nonconsented_event_count = 0
    missing_device_count = 0
    missing_offer_count = 0
    conversion_reference_count = 0
    duplicate_like_count = 0

    handle, writer = write_csv_header(data_dir / "campaign_events.csv", CAMPAIGN_HEADER)

    def emit(row: dict[str, str], customer_num: int, duplicate: bool = False):
        nonlocal output_event_number, nonconsented_event_count, missing_device_count
        nonlocal missing_offer_count, conversion_reference_count, duplicate_like_count
        output_event_number += 1
        row = row.copy()
        row["event_id"] = event_id(output_event_number)
        if output_event_number in casing_event_numbers:
            row["channel"] = row["channel"].lower() if output_event_number % 2 else row["channel"].title()
        writer.writerow(row)
        event_type_counts[row["event_type"]] += 1
        channel_counts[row["channel"]] += 1
        campaign_counts[row["campaign_name"]] += 1
        date_counter_update(date_bounds, datetime.fromisoformat(row["event_timestamp"]).date())
        if customers[customer_num].marketing_consent != "true":
            nonconsented_event_count += 1
        if not row["device_type"]:
            missing_device_count += 1
        if not row["offer_code"]:
            missing_offer_count += 1
        if row["conversion_booking_id"]:
            conversion_reference_count += 1
        if duplicate:
            duplicate_like_count += 1

    with handle:
        while base_position < base_event_target:
            remaining = base_event_target - base_position
            sequence = campaign_sequence(rng, remaining)
            journey_number += 1
            use_suppressed = journey_number % 1_000 == 0
            is_conversion = sequence[-1] == "CONVERTED"
            if is_conversion:
                pool = suppressed_converters if use_suppressed else consented_converters
            else:
                pool = suppressed if use_suppressed else consented
            customer_num = rng.choice(pool)
            customer = customers[customer_num]

            conversion_booking_number = None
            if is_conversion:
                conversion_booking_number, conversion_booking_day = rng.choice(bookings_by_customer[customer_num])
                base_day = max(customer.signup_date, conversion_booking_day - timedelta(days=rng.randint(1, 14)))
            else:
                base_day = weighted_date(rng, customer.signup_date, AS_OF_DATE)
            campaign_name = choose_campaign_name(rng, base_day, customer.signup_date, highest_tier[customer_num])
            campaign_id_value = f"CMP-{base_day:%Y%m}-{campaign_name[:8]}"
            channel = weighted_choice(rng, ["EMAIL", "SMS", "PUSH", "IN_APP"], [59, 13, 20, 8])
            device = campaign_device(rng, channel)
            offer = OFFER_CODES[campaign_name] if rng.random() < 0.57 else ""
            event_time = random_datetime(rng, base_day, 8, 17)

            for step_index, event_type in enumerate(sequence):
                if step_index:
                    if event_type in {"DELIVERED", "BOUNCED"}:
                        event_time += timedelta(minutes=rng.randint(2, 180))
                    elif event_type in {"OPENED", "UNSUBSCRIBED"}:
                        event_time += timedelta(minutes=rng.randint(5, 1_440))
                    else:
                        event_time += timedelta(minutes=rng.randint(2, 720))
                event_time = clamp_datetime(event_time)
                base_position += 1
                row_device = "" if base_position % 97 == 0 else device
                conversion_value = ""
                if event_type == "CONVERTED" and conversion_booking_number and rng.random() < 0.86:
                    conversion_value = booking_id(conversion_booking_number)
                created = clamp_datetime(event_time + timedelta(minutes=rng.randint(0, 180)))
                row = {
                    "event_id": "",  # populated by emit
                    "customer_id": customer_id(customer_num + 1),
                    "campaign_id": campaign_id_value,
                    "campaign_name": campaign_name,
                    "campaign_type": CAMPAIGN_TYPE[campaign_name],
                    "channel": channel,
                    "event_type": event_type,
                    "event_timestamp": iso_timestamp(event_time),
                    "device_type": row_device,
                    "offer_code": offer,
                    "conversion_booking_id": conversion_value,
                    "created_at": iso_timestamp(created),
                }
                emit(row, customer_num)
                if base_position in duplicate_after_positions:
                    emit(row, customer_num, duplicate=True)

    assert base_position == base_event_target
    assert output_event_number == CAMPAIGN_EVENT_COUNT
    stats = {
        "event_type_counts": event_type_counts,
        "channel_counts": channel_counts,
        "campaign_counts": campaign_counts,
        "date_bounds": date_bounds,
        "journey_count": journey_number,
        "nonconsented_event_count": nonconsented_event_count,
        "missing_device_count": missing_device_count,
        "missing_offer_count": missing_offer_count,
        "conversion_reference_count": conversion_reference_count,
        "inconsistent_channel_count": len(casing_event_numbers),
        "duplicate_like_count": duplicate_like_count,
    }
    return stats


def count_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in handle) - 1


def parse_cents(value: str) -> int:
    return int(Decimal(value) * 100)


def validate_outputs(data_dir: Path) -> list[str]:
    """Independently stream the generated CSVs and verify core migration rules."""
    checks: list[str] = []
    customers: set[str] = set()
    with (data_dir / "customers.csv").open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 1):
            expected = customer_id(number)
            if row["customer_id"] != expected:
                raise AssertionError(f"Customer PK sequence broke at row {number}")
            customers.add(row["customer_id"])
    if len(customers) != CUSTOMER_COUNT:
        raise AssertionError("Customer PK uniqueness failed")
    checks.append("50,000 sequential unique customer primary keys")

    memberships: dict[str, tuple[str, date, date, str]] = {}
    with (data_dir / "memberships.csv").open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 1):
            if row["membership_id"] != membership_id(number):
                raise AssertionError(f"Membership PK sequence broke at row {number}")
            if row["customer_id"] not in customers:
                raise AssertionError("Membership customer FK failed")
            memberships[row["membership_id"]] = (
                row["customer_id"],
                date.fromisoformat(row["membership_start_date"]),
                date.fromisoformat(row["membership_end_date"]),
                row["membership_status"],
            )
    if len(memberships) != MEMBERSHIP_COUNT:
        raise AssertionError("Membership PK uniqueness failed")
    checks.append("70,000 memberships with valid customer foreign keys")

    bookings: dict[str, tuple[str, int, str, date]] = {}
    travel_anomalies = 0
    with (data_dir / "bookings.csv").open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 1):
            if row["booking_id"] != booking_id(number):
                raise AssertionError(f"Booking PK sequence broke at row {number}")
            if row["customer_id"] not in customers:
                raise AssertionError("Booking customer FK failed")
            booking_day = date.fromisoformat(row["booking_date"])
            travel_day = date.fromisoformat(row["travel_date"])
            if travel_day < booking_day:
                travel_anomalies += 1
            member_value = row["membership_id"]
            if member_value:
                if member_value not in memberships:
                    raise AssertionError("Booking membership FK failed")
                member_customer, start, end, member_status = memberships[member_value]
                if member_customer != row["customer_id"]:
                    raise AssertionError("Booking membership belongs to another customer")
                if not (start <= booking_day <= end) or member_status not in {"ACTIVE", "EXPIRED"}:
                    raise AssertionError("Booking membership was not usable on booking date")
            net = parse_cents(row["gross_booking_amount"]) - parse_cents(row["discount_amount"])
            if net <= 0:
                raise AssertionError("Booking net amount is non-positive")
            bookings[row["booking_id"]] = (row["customer_id"], net, row["booking_status"], booking_day)
    if len(bookings) != BOOKING_COUNT:
        raise AssertionError("Booking PK uniqueness failed")
    if travel_anomalies != 80:
        raise AssertionError(f"Expected 80 controlled travel-date anomalies, found {travel_anomalies}")
    checks.append("400,000 bookings with valid customer/membership ownership and 80 documented date anomalies")

    payments: dict[str, tuple[str, str, date, int, str]] = {}
    successful_by_booking: Counter[str] = Counter()
    with (data_dir / "payments.csv").open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 1):
            if row["payment_id"] != payment_id(number):
                raise AssertionError(f"Payment PK sequence broke at row {number}")
            booking_value = bookings.get(row["booking_id"])
            if booking_value is None or booking_value[0] != row["customer_id"]:
                raise AssertionError("Payment booking/customer FK failed")
            amount = parse_cents(row["payment_amount"])
            if amount <= 0 or amount > booking_value[1]:
                raise AssertionError("Payment amount is outside the booking net amount")
            pay_day = date.fromisoformat(row["payment_date"])
            if pay_day < booking_value[3]:
                raise AssertionError("Payment predates booking")
            payments[row["payment_id"]] = (
                row["booking_id"], row["customer_id"], pay_day, amount, row["payment_status"]
            )
            if row["payment_status"] == "SUCCESS":
                successful_by_booking[row["booking_id"]] += amount
    if len(payments) != PAYMENT_COUNT:
        raise AssertionError("Payment PK uniqueness failed")
    for booking_key, settled in successful_by_booking.items():
        if settled > bookings[booking_key][1]:
            raise AssertionError("Successful payments exceed booking net amount")
    checks.append("450,000 payments with valid booking/customer ownership and bounded amounts")

    completed_refunds_by_booking: Counter[str] = Counter()
    refunds_by_payment: Counter[str] = Counter()
    with (data_dir / "refunds.csv").open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 1):
            if row["refund_id"] != refund_id(number):
                raise AssertionError(f"Refund PK sequence broke at row {number}")
            payment_value = payments.get(row["payment_id"])
            if payment_value is None:
                raise AssertionError("Refund payment FK failed")
            if payment_value[0] != row["booking_id"] or payment_value[1] != row["customer_id"]:
                raise AssertionError("Refund booking/customer lineage failed")
            amount = parse_cents(row["refund_amount"])
            refund_day = date.fromisoformat(row["refund_date"])
            if refund_day <= payment_value[2]:
                raise AssertionError("Refund does not occur after payment")
            if amount <= 0 or amount > payment_value[3]:
                raise AssertionError("Refund exceeds referenced payment")
            refunds_by_payment[row["payment_id"]] += amount
            if row["refund_status"] == "COMPLETED":
                completed_refunds_by_booking[row["booking_id"]] += amount
    for payment_key, total in refunds_by_payment.items():
        if total > payments[payment_key][3]:
            raise AssertionError("Cumulative refunds exceed referenced payment")
    for booking_key, (_, _, status, _) in bookings.items():
        if status == "FULLY_REFUNDED" and completed_refunds_by_booking[booking_key] != successful_by_booking[booking_key]:
            raise AssertionError("FULLY_REFUNDED booking does not reconcile to completed refunds")
        if status == "PARTIALLY_REFUNDED":
            refunded = completed_refunds_by_booking[booking_key]
            if not (0 < refunded < successful_by_booking[booking_key]):
                raise AssertionError("PARTIALLY_REFUNDED booking does not have a partial completed refund")
    checks.append("30,000 refunds after payment, cumulatively bounded, and reconciled to booking refund statuses")

    with (data_dir / "campaign_events.csv").open(newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), 1):
            if row["event_id"] != event_id(number):
                raise AssertionError(f"Campaign event PK sequence broke at row {number}")
            if row["customer_id"] not in customers:
                raise AssertionError("Campaign customer FK failed")
            conversion = row["conversion_booking_id"]
            if conversion:
                if conversion not in bookings or bookings[conversion][0] != row["customer_id"]:
                    raise AssertionError("Campaign conversion booking/customer FK failed")
    checks.append("500,000 campaign events with valid customers and customer-owned conversion bookings")

    for filename, expected in ROW_COUNTS.items():
        actual = count_rows(data_dir / filename)
        if actual != expected:
            raise AssertionError(f"{filename}: expected {expected}, found {actual}")
    checks.append("All six files match the requested exact row counts")
    return checks


def markdown_counter(counter: Counter[str]) -> str:
    lines = ["| Value | Rows | Share |", "|---|---:|---:|"]
    total = sum(counter.values())
    for key, value in counter.most_common():
        lines.append(f"| {key} | {value:,} | {value / total:.2%} |")
    return "\n".join(lines)


def markdown_money_by_currency(*columns: tuple[str, Counter[str]]) -> str:
    currencies = ["AUD", "NZD", "USD", "EUR", "GBP"]
    header = "| Currency | " + " | ".join(name for name, _ in columns) + " |"
    divider = "|---|" + "---:|" * len(columns)
    lines = [header, divider]
    for currency in currencies:
        values = [f"{counter[currency] / 100:,.2f}" for _, counter in columns]
        lines.append(f"| {currency} | " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_data_dictionary(root: Path) -> None:
    content = """# TripBridge Data Dictionary

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
"""
    (root / "DATA_DICTIONARY.md").write_text(content, encoding="utf-8")


def write_data_quality_notes(root: Path, stats: dict) -> None:
    customer = stats["customers"]
    booking = stats["bookings"]
    payment = stats["payments"]
    campaign = stats["campaign"]
    content = f"""# TripBridge Intentional Data Quality Notes

The extracts preserve unique primary keys and valid core foreign keys. The following controlled issues were added for profiling, cleansing, incremental-load and reconciliation practice.

## Deliberate source-quality issues

| Issue | Exact rows/pairs | Location | Intended exercise |
|---|---:|---|---|
| Missing optional phone | {customer['null_phone_count']:,} rows | `customers.phone` | Null handling and completeness profiling. |
| Unknown marketing consent | {customer['null_consent_count']:,} rows | `customers.marketing_consent` | Three-state consent treatment; blank is not consent. |
| Upper-case synthetic email | {customer['uppercase_email_count']:,} rows | `customers.email` | Case normalisation and natural-key matching. |
| Duplicate-like customer natural keys | {customer['natural_duplicate_pairs']:,} pairs | Customers share name/email/phone/DOB but retain different `customer_id` values | Deduplication without breaking primary keys. |
| Travel date before booking date | {booking['travel_anomaly_count']:,} rows | `bookings.travel_date` | Reject/quarantine date-rule failures. The offset is only one or two days. |
| Late booking update | {booking['late_update_count']:,} rows | `bookings.updated_at` | Incremental watermark/backfill logic; these old bookings were updated near the extract date. |
| Inconsistent campaign channel casing | {campaign['inconsistent_channel_count']:,} rows | `campaign_events.channel` | Standardise values such as `email`, `Push` and canonical upper case. |
| Duplicate-like campaign event | {campaign['duplicate_like_count']:,} rows | Same business event repeated under a different `event_id` | Idempotency/business-key deduplication while preserving PK uniqueness. |
| Missing device type | {campaign['missing_device_count']:,} rows | `campaign_events.device_type` | Optional marketing attribute completeness. |
| Suppression anomaly | {campaign['nonconsented_event_count']:,} event rows | Events sent to customers whose consent is false/unknown | Consent-control reconciliation; the exception rate is intentionally very small. |

## Expected optional sparsity (not necessarily a defect)

- `{booking['missing_membership_count']:,}` bookings have no `membership_id`. This includes non-members, bookings outside a usable membership period, and a small controlled source omission rate.
- `{booking['missing_origin_count']:,}` hotel/car-hire/tour bookings have a blank origin because the field is not always meaningful in the upstream product flow.
- `{campaign['missing_offer_count']:,}` campaign events have no `offer_code`; many messages are informational or do not use a promotion.
- Conversion booking IDs appear on `{campaign['conversion_reference_count']:,}` conversion-event rows; attribution is optional.

## Operational outcomes retained for realism

- Cancelled bookings: `{booking['status_counts']['CANCELLED']:,}`.
- Failed payments: `{payment['status_counts']['FAILED']:,}`; declined payments: `{payment['status_counts']['DECLINED']:,}`; reversed payments: `{payment['status_counts']['REVERSED']:,}`.
- A cancelled booking can retain a successful payment where the amount represents a non-refundable supplier charge/cancellation fee.
- Pending/rejected refund attempts do not make a booking fully refunded. Every `FULLY_REFUNDED` booking reconciles to completed refunds; every `PARTIALLY_REFUNDED` booking has a positive completed refund below successful payments.

## Guarantees deliberately not broken

- No duplicate or null primary keys.
- No orphan customer, membership, booking, payment or refund foreign keys.
- A supplied booking membership belongs to the same customer and covers the booking date.
- Payment customer ownership matches the booking; payment amounts do not exceed booking net value.
- Refunds occur after payment and cumulative refund rows never exceed the referenced payment.
- A populated campaign conversion booking belongs to the event customer.
"""
    (root / "DATA_QUALITY_NOTES.md").write_text(content, encoding="utf-8")


def write_generation_summary(root: Path, stats: dict, validation_checks: list[str]) -> None:
    booking = stats["bookings"]
    payment = stats["payments"]
    refund = stats["refunds"]
    customer = stats["customers"]
    membership = stats["memberships"]
    campaign = stats["campaign"]
    file_rows = "\n".join(f"| {name} | {count:,} |" for name, count in ROW_COUNTS.items())
    validation = "\n".join(f"- PASS — {check}." for check in validation_checks)
    content = f"""# TripBridge Generation Summary

Generated deterministically with seed `{SEED}` and an extract/as-of date of `{AS_OF_DATE.isoformat()}`. The main operational history runs from `{HISTORY_START.isoformat()}` through `{AS_OF_DATE.isoformat()}`; confirmed travel extends beyond the extract date.

## Output row counts

| File | Rows |
|---|---:|
{file_rows}

- Unique customers: **{CUSTOMER_COUNT:,}**
- Customers with at least one membership record: **{membership['customers_with_membership']:,}**
- Customers with at least one booking: **{booking['customers_with_bookings']:,}**
- Customers with exactly one booking: **{booking['customers_with_one_booking']:,}**
- Highest booking count for one frequent traveller: **{booking['max_bookings_for_one_customer']:,}**
- Generated campaign journeys: **{campaign['journey_count']:,}** (each journey produces a valid event sequence)

## Observed date ranges

| Dataset | Minimum | Maximum |
|---|---|---|
| Customer signup | {customer['signup_bounds']['min']} | {customer['signup_bounds']['max']} |
| Membership service dates | {membership['date_bounds']['min']} | {membership['date_bounds']['max']} |
| Booking/travel dates | {booking['date_bounds']['min']} | {booking['date_bounds']['max']} |
| Payment dates | {payment['date_bounds']['min']} | {payment['date_bounds']['max']} |
| Refund dates | {refund['date_bounds']['min']} | {refund['date_bounds']['max']} |
| Campaign event timestamps | {campaign['date_bounds']['min']} | {campaign['date_bounds']['max']} |

## Financial totals by currency

Amounts are **nominal in their recorded currencies** and are not converted to AUD. Gross booking value is before discounts. “All payment attempts” includes failed/declined retries and therefore is not settlement revenue.

{markdown_money_by_currency(
    ('Gross booking value', booking['gross_by_currency']),
    ('Discounts', booking['discount_by_currency']),
    ('All payment attempts', payment['amount_by_currency']),
    ('Successful payments', payment['successful_by_currency']),
    ('All refund requests', refund['amount_by_currency']),
    ('Completed refunds', refund['completed_by_currency']),
)}

## Customer status distribution

{markdown_counter(customer['status_counts'])}

## Membership status distribution

{markdown_counter(membership['status_counts'])}

## Booking status distribution

{markdown_counter(booking['status_counts'])}

## Payment status distribution

{markdown_counter(payment['status_counts'])}

## Refund status distribution

{markdown_counter(refund['status_counts'])}

## Campaign event-type distribution

{markdown_counter(campaign['event_type_counts'])}

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

{validation}
"""
    (root / "GENERATION_SUMMARY.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the TripBridge synthetic source extracts")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="TripBridge project root (default: parent of scripts/)",
    )
    args = parser.parse_args()
    root = args.output_root.resolve()
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    print("[1/9] Generating customers.csv", flush=True)
    customers, customer_stats = generate_customers(data_dir, rng)
    print("[2/9] Generating memberships.csv", flush=True)
    memberships_by_customer, highest_tier, membership_stats = generate_memberships(data_dir, rng, customers)
    print("[3/9] Generating bookings.csv", flush=True)
    bookings, bookings_by_customer, booking_stats = generate_bookings(
        data_dir, rng, customers, memberships_by_customer, highest_tier
    )
    print("[4/9] Generating payments.csv", flush=True)
    refund_payment_map, payment_stats = generate_payments(data_dir, rng, bookings)
    print("[5/9] Generating refunds.csv", flush=True)
    refund_stats = generate_refunds(
        data_dir, rng, bookings, refund_payment_map,
        booking_stats["full_indices"], booking_stats["partial_indices"],
    )
    print("[6/9] Generating campaign_events.csv", flush=True)
    campaign_stats = generate_campaign_events(
        data_dir, rng, customers, highest_tier, bookings_by_customer
    )

    # Retain only summary counters before the independent streaming validation.
    booking_stats = {key: value for key, value in booking_stats.items() if key not in {"full_indices", "partial_indices"}}
    stats = {
        "customers": customer_stats,
        "memberships": membership_stats,
        "bookings": booking_stats,
        "payments": payment_stats,
        "refunds": refund_stats,
        "campaign": campaign_stats,
    }
    del customers, memberships_by_customer, highest_tier, bookings
    del bookings_by_customer, refund_payment_map
    gc.collect()

    print("[7/9] Validating row counts, keys, relationships and financial rules", flush=True)
    validation_checks = validate_outputs(data_dir)
    print("[8/9] Writing DATA_DICTIONARY.md and DATA_QUALITY_NOTES.md", flush=True)
    write_data_dictionary(root)
    write_data_quality_notes(root, stats)
    print("[9/9] Writing GENERATION_SUMMARY.md", flush=True)
    write_generation_summary(root, stats, validation_checks)
    print("TripBridge generation and validation completed successfully.", flush=True)


if __name__ == "__main__":
    main()
