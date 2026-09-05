"""
Synthetic Data Generator for Transaction Risk Investigation Assistant (NexusTiq24 PS06).
Generates multi-month transaction histories for three customer profiles:
1. Clean Customer (Routine activity, 0 rules triggered)
2. Anomalous Customer (Planted anomalies: large transfer, unfamiliar payee burst, odd hours)
3. Borderline Customer (Ambiguous/weak signals demonstrating system restraint)
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path


def generate_clean_customer():
    base_date = datetime(2026, 5, 1, 9, 0, 0)
    txns = []
    txn_counter = 1000

    # Payees & category channels
    routine_activities = [
        ("Salary Direct Deposit", "Employer Direct", 3200.00, "ACH", 9, 10, "Monthly"),
        ("Monthly Rent", "Oakwood Apartments", 1250.00, "ACH", 10, 11, "Monthly"),
        ("Electric Utility", "City Power Co", 85.50, "ACH", 14, 16, "Monthly"),
        ("Internet Service", "FiberNet Broadband", 69.99, "Debit Card", 11, 13, "Monthly"),
        ("Weekly Grocery", "Fresh Foods Market", 110.00, "Debit Card", 17, 19, "Weekly"),
        ("Coffee Shop", "Daily Grind Cafe", 6.50, "Debit Card", 8, 9, "Daily"),
        ("Fuel / Gas", "QuickStop Station", 45.00, "Debit Card", 12, 18, "Biweekly"),
        ("Online Shopping", "A-Z Retail Store", 55.20, "Mobile App", 19, 21, "Biweekly"),
        ("Gym Membership", "FitPulse Club", 39.99, "Debit Card", 6, 7, "Monthly"),
    ]

    # Generate 120 days of routine activity
    for day in range(120):
        current_day = base_date + timedelta(days=day)
        
        # Monthly salary on day 1 and 30
        if current_day.day == 1 or current_day.day == 15:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-CLN-{txn_counter}",
                "customer_id": "CUST-1001",
                "timestamp": current_day.replace(hour=9, minute=15).isoformat(),
                "description": "Bi-weekly Payroll Direct Deposit",
                "payee": "TechCorp Payroll",
                "amount": 2850.00,
                "channel": "ACH",
                "category": "Income",
                "status": "Completed"
            })

        # Rent on 1st of month
        if current_day.day == 1:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-CLN-{txn_counter}",
                "customer_id": "CUST-1001",
                "timestamp": current_day.replace(hour=10, minute=30).isoformat(),
                "description": "Monthly Apartment Rent Payment",
                "payee": "Oakwood Apartments",
                "amount": 1250.00,
                "channel": "ACH",
                "category": "Housing",
                "status": "Completed"
            })

        # Coffee almost daily
        if current_day.weekday() < 5 and random.random() < 0.8:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-CLN-{txn_counter}",
                "customer_id": "CUST-1001",
                "timestamp": current_day.replace(hour=8, minute=20 + random.randint(0, 30)).isoformat(),
                "description": "Morning Coffee & Pastry",
                "payee": "Daily Grind Cafe",
                "amount": round(random.uniform(4.50, 8.75), 2),
                "channel": "Debit Card",
                "category": "Dining",
                "status": "Completed"
            })

        # Grocery weekly (Saturdays)
        if current_day.weekday() == 5:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-CLN-{txn_counter}",
                "customer_id": "CUST-1001",
                "timestamp": current_day.replace(hour=11, minute=random.randint(10, 50)).isoformat(),
                "description": "Weekly Grocery Supplies",
                "payee": "Fresh Foods Market",
                "amount": round(random.uniform(85.00, 140.00), 2),
                "channel": "Debit Card",
                "category": "Groceries",
                "status": "Completed"
            })

    return {
        "customer_id": "CUST-1001",
        "customer_name": "Sarah Jenkins",
        "account_type": "Personal Checking",
        "risk_profile": "Clean / Routine",
        "total_count": len(txns),
        "transactions": sorted(txns, key=lambda x: x["timestamp"])
    }


def generate_anomalous_customer():
    base_date = datetime(2026, 5, 1, 9, 0, 0)
    txns = []
    txn_counter = 2000

    # 90 days of normal baseline activity
    for day in range(90):
        current_day = base_date + timedelta(days=day)
        
        # Salary
        if current_day.day in [1, 15]:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-ANO-{txn_counter}",
                "customer_id": "CUST-1002",
                "timestamp": current_day.replace(hour=9, minute=0).isoformat(),
                "description": "Salary Direct Deposit",
                "payee": "Apex Solutions Inc",
                "amount": 3400.00,
                "channel": "ACH",
                "category": "Income",
                "status": "Completed"
            })

        # Routine expenses (Rent, Utilities, Groceries)
        if current_day.day == 2:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-ANO-{txn_counter}",
                "customer_id": "CUST-1002",
                "timestamp": current_day.replace(hour=10, minute=15).isoformat(),
                "description": "Residential Lease",
                "payee": "Metro Housing Corp",
                "amount": 1400.00,
                "channel": "ACH",
                "category": "Housing",
                "status": "Completed"
            })

        if current_day.weekday() == 2 and random.random() < 0.7:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-ANO-{txn_counter}",
                "customer_id": "CUST-1002",
                "timestamp": current_day.replace(hour=18, minute=30).isoformat(),
                "description": "Supermarket Purchase",
                "payee": "Whole Harvest Market",
                "amount": round(random.uniform(60.00, 130.00), 2),
                "channel": "Debit Card",
                "category": "Groceries",
                "status": "Completed"
            })

    # Planted Anomalies near the end (Day 91 & 92 - August 1, 2026)
    anomaly_date = base_date + timedelta(days=91)

    # Anomaly 1: Unusually large transfer relative to history (baseline max normal was $1400, 90th percentile ~$300)
    txns.append({
        "transaction_id": "TXN-88219",
        "customer_id": "CUST-1002",
        "timestamp": anomaly_date.replace(hour=14, minute=10).isoformat(),
        "description": "Outgoing International Wire Transfer",
        "payee": "Apex Overseas Holdings LLC",
        "amount": 9500.00,
        "channel": "Wire Transfer",
        "category": "Transfer",
        "status": "Completed"
    })

    # Anomaly 2 & 3: Payee burst to new unfamiliar payee + Odd-hours activity (03:14 AM and 03:42 AM)
    txns.append({
        "transaction_id": "TXN-88220",
        "customer_id": "CUST-1002",
        "timestamp": (anomaly_date + timedelta(days=1)).replace(hour=3, minute=14).isoformat(),
        "description": "Instant Crypto Purchase",
        "payee": "CryptoVault Exchange",
        "amount": 2200.00,
        "channel": "P2P Payment",
        "category": "Crypto/Investments",
        "status": "Completed"
    })

    txns.append({
        "transaction_id": "TXN-88221",
        "customer_id": "CUST-1002",
        "timestamp": (anomaly_date + timedelta(days=1)).replace(hour=3, minute=42).isoformat(),
        "description": "Instant Crypto Purchase",
        "payee": "CryptoVault Exchange",
        "amount": 2600.00,
        "channel": "P2P Payment",
        "category": "Crypto/Investments",
        "status": "Completed"
    })

    txns.append({
        "transaction_id": "TXN-88222",
        "customer_id": "CUST-1002",
        "timestamp": (anomaly_date + timedelta(days=1)).replace(hour=4, minute=5).isoformat(),
        "description": "Instant Crypto Purchase",
        "payee": "CryptoVault Exchange",
        "amount": 1800.00,
        "channel": "P2P Payment",
        "category": "Crypto/Investments",
        "status": "Completed"
    })

    return {
        "customer_id": "CUST-1002",
        "customer_name": "Marcus Vance",
        "account_type": "Premium Checking",
        "risk_profile": "High Risk / Multiple Anomalies",
        "total_count": len(txns),
        "transactions": sorted(txns, key=lambda x: x["timestamp"])
    }


def generate_borderline_customer():
    base_date = datetime(2026, 5, 1, 9, 0, 0)
    txns = []
    txn_counter = 3000

    # 90 days of normal activity
    for day in range(90):
        current_day = base_date + timedelta(days=day)
        
        if current_day.day in [1, 15]:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-BOR-{txn_counter}",
                "customer_id": "CUST-1003",
                "timestamp": current_day.replace(hour=9, minute=30).isoformat(),
                "description": "Bi-weekly Salary",
                "payee": "Global Logistics Corp",
                "amount": 2900.00,
                "channel": "ACH",
                "category": "Income",
                "status": "Completed"
            })

        if current_day.weekday() == 1 and random.random() < 0.6:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-BOR-{txn_counter}",
                "customer_id": "CUST-1003",
                "timestamp": current_day.replace(hour=19, minute=10).isoformat(),
                "description": "Department Store",
                "payee": "Urban Fashion Outlet",
                "amount": round(random.uniform(40.00, 180.00), 2),
                "channel": "Debit Card",
                "category": "Shopping",
                "status": "Completed"
            })

    # Borderline activity: Slightly elevated transaction ($1,450 vs regular shopping $180, but customer has paid annual insurance before)
    # Executed at 00:45 AM (borderline odd-hours: just after midnight)
    borderline_date = base_date + timedelta(days=88)
    txns.append({
        "transaction_id": "TXN-BOR-9901",
        "customer_id": "CUST-1003",
        "timestamp": borderline_date.replace(hour=0, minute=45).isoformat(),
        "description": "Annual Premium Auto Insurance Renewal",
        "payee": "Metro Auto Insurance Co",
        "amount": 1450.00,
        "channel": "Debit Card",
        "category": "Insurance",
        "status": "Completed"
    })

    return {
        "customer_id": "CUST-1003",
        "customer_name": "Elena Rostova",
        "account_type": "Standard Checking",
        "risk_profile": "Borderline / Low Confidence",
        "total_count": len(txns),
        "transactions": sorted(txns, key=lambda x: x["timestamp"])
    }


def main():
    data_dir = Path(__file__).parent
    data_dir.mkdir(exist_ok=True)

    clean = generate_clean_customer()
    anomalous = generate_anomalous_customer()
    borderline = generate_borderline_customer()

    with open(data_dir / "clean_customer.json", "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2)

    with open(data_dir / "anomalous_customer.json", "w", encoding="utf-8") as f:
        json.dump(anomalous, f, indent=2)

    with open(data_dir / "borderline_customer.json", "w", encoding="utf-8") as f:
        json.dump(borderline, f, indent=2)

    all_customers = {
        "CUST-1001": clean,
        "CUST-1002": anomalous,
        "CUST-1003": borderline
    }

    with open(data_dir / "all_customers.json", "w", encoding="utf-8") as f:
        json.dump(all_customers, f, indent=2)

    print("Synthetic datasets generated successfully in data/")
    print(f"Clean customer (CUST-1001): {len(clean['transactions'])} txns")
    print(f"Anomalous customer (CUST-1002): {len(anomalous['transactions'])} txns")
    print(f"Borderline customer (CUST-1003): {len(borderline['transactions'])} txns")


if __name__ == "__main__":
    main()
