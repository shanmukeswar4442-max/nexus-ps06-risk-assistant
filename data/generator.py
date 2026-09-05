"""
Synthetic Data Generator for Transaction Risk Investigation Assistant (NexusTiq24 PS06) — INR (Indian Rupees) Edition.
Generates multi-month transaction histories in Indian Rupees (₹) for three customer profiles:
1. Clean Customer (Routine activity in INR, 0 rules triggered)
2. Anomalous Customer (Planted anomalies in INR: large transfer, unfamiliar payee burst, odd hours)
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

    # Generate 120 days of routine activity in Indian Rupees (₹)
    for day in range(120):
        current_day = base_date + timedelta(days=day)
        
        # Monthly salary on day 1 and 15
        if current_day.day == 1 or current_day.day == 15:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-CLN-{txn_counter}",
                "customer_id": "CUST-1001",
                "timestamp": current_day.replace(hour=9, minute=15).isoformat(),
                "description": "Bi-weekly Payroll Salary Credit",
                "payee": "Infosys Ltd Payroll",
                "amount": 145000.00,
                "channel": "NEFT",
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
                "description": "Monthly House Rent Payment",
                "payee": "Sharma Realty Properties",
                "amount": 35000.00,
                "channel": "UPI",
                "category": "Housing",
                "status": "Completed"
            })

        # Daily coffee / snacks via UPI
        if current_day.weekday() < 5 and random.random() < 0.8:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-CLN-{txn_counter}",
                "customer_id": "CUST-1001",
                "timestamp": current_day.replace(hour=8, minute=20 + random.randint(0, 30)).isoformat(),
                "description": "Morning Chai & Breakfast",
                "payee": "Chai Point",
                "amount": round(random.uniform(120.00, 350.00), 2),
                "channel": "UPI",
                "category": "Dining",
                "status": "Completed"
            })

        # Groceries weekly (Saturdays)
        if current_day.weekday() == 5:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-CLN-{txn_counter}",
                "customer_id": "CUST-1001",
                "timestamp": current_day.replace(hour=11, minute=random.randint(10, 50)).isoformat(),
                "description": "Weekly Supermarket Shopping",
                "payee": "DMart Supermarket",
                "amount": round(random.uniform(2500.00, 6500.00), 2),
                "channel": "UPI",
                "category": "Groceries",
                "status": "Completed"
            })

    return {
        "customer_id": "CUST-1001",
        "customer_name": "Sarah Jenkins",
        "account_type": "Personal Salary Account",
        "currency": "INR",
        "risk_profile": "Clean / Routine",
        "total_count": len(txns),
        "transactions": sorted(txns, key=lambda x: x["timestamp"])
    }


def generate_anomalous_customer():
    base_date = datetime(2026, 5, 1, 9, 0, 0)
    txns = []
    txn_counter = 2000

    # 90 days of normal baseline activity in INR
    for day in range(90):
        current_day = base_date + timedelta(days=day)
        
        # Salary
        if current_day.day in [1, 15]:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-ANO-{txn_counter}",
                "customer_id": "CUST-1002",
                "timestamp": current_day.replace(hour=9, minute=0).isoformat(),
                "description": "Executive Salary Direct Credit",
                "payee": "Apex Global Solutions India",
                "amount": 185000.00,
                "channel": "RTGS",
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
                "description": "Apartment Maintenance & Rent",
                "payee": "Prestige Heights Housing",
                "amount": 42000.00,
                "channel": "Net Banking",
                "category": "Housing",
                "status": "Completed"
            })

        if current_day.weekday() == 2 and random.random() < 0.7:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-ANO-{txn_counter}",
                "customer_id": "CUST-1002",
                "timestamp": current_day.replace(hour=18, minute=30).isoformat(),
                "description": "Grocery Superstore",
                "payee": "Nature Basket Market",
                "amount": round(random.uniform(1800.00, 4500.00), 2),
                "channel": "UPI",
                "category": "Groceries",
                "status": "Completed"
            })

    # Planted Anomalies near the end (Day 91 & 92)
    anomaly_date = base_date + timedelta(days=91)

    # Anomaly 1: Unusually large transfer relative to history (baseline max normal spending was ₹42,000, 90th percentile ~₹15,000)
    txns.append({
        "transaction_id": "TXN-88219",
        "customer_id": "CUST-1002",
        "timestamp": anomaly_date.replace(hour=14, minute=10).isoformat(),
        "description": "High-Value Overseas Wire Transfer",
        "payee": "Apex Overseas Investment LLC",
        "amount": 950000.00,
        "channel": "Wire Transfer",
        "category": "Transfer",
        "status": "Completed"
    })

    # Anomaly 2 & 3: Payee burst to new unfamiliar payee + Odd-hours activity (03:14 AM and 03:42 AM)
    txns.append({
        "transaction_id": "TXN-88220",
        "customer_id": "CUST-1002",
        "timestamp": (anomaly_date + timedelta(days=1)).replace(hour=3, minute=14).isoformat(),
        "description": "Instant Crypto Token Purchase",
        "payee": "CryptoVault Exchange India",
        "amount": 220000.00,
        "channel": "IMPS",
        "category": "Crypto/Investments",
        "status": "Completed"
    })

    txns.append({
        "transaction_id": "TXN-88221",
        "customer_id": "CUST-1002",
        "timestamp": (anomaly_date + timedelta(days=1)).replace(hour=3, minute=42).isoformat(),
        "description": "Instant Crypto Token Purchase",
        "payee": "CryptoVault Exchange India",
        "amount": 260000.00,
        "channel": "IMPS",
        "category": "Crypto/Investments",
        "status": "Completed"
    })

    txns.append({
        "transaction_id": "TXN-88222",
        "customer_id": "CUST-1002",
        "timestamp": (anomaly_date + timedelta(days=1)).replace(hour=4, minute=5).isoformat(),
        "description": "Instant Crypto Token Purchase",
        "payee": "CryptoVault Exchange India",
        "amount": 180000.00,
        "channel": "IMPS",
        "category": "Crypto/Investments",
        "status": "Completed"
    })

    return {
        "customer_id": "CUST-1002",
        "customer_name": "Marcus Vance",
        "account_type": "Privilege Savings Account",
        "currency": "INR",
        "risk_profile": "High Risk / Multiple Anomalies",
        "total_count": len(txns),
        "transactions": sorted(txns, key=lambda x: x["timestamp"])
    }


def generate_borderline_customer():
    base_date = datetime(2026, 5, 1, 9, 0, 0)
    txns = []
    txn_counter = 3000

    # 90 days of normal activity in INR
    for day in range(90):
        current_day = base_date + timedelta(days=day)
        
        if current_day.day in [1, 15]:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-BOR-{txn_counter}",
                "customer_id": "CUST-1003",
                "timestamp": current_day.replace(hour=9, minute=30).isoformat(),
                "description": "Bi-weekly Professional Fee",
                "payee": "Global Logistics Corp India",
                "amount": 115000.00,
                "channel": "NEFT",
                "category": "Income",
                "status": "Completed"
            })

        if current_day.weekday() == 1 and random.random() < 0.6:
            txn_counter += 1
            txns.append({
                "transaction_id": f"TXN-BOR-{txn_counter}",
                "customer_id": "CUST-1003",
                "timestamp": current_day.replace(hour=19, minute=10).isoformat(),
                "description": "Apparel Shopping",
                "payee": "Urban Fashion Outlet",
                "amount": round(random.uniform(1500.00, 6500.00), 2),
                "channel": "UPI",
                "category": "Shopping",
                "status": "Completed"
            })

    # Borderline activity: Slightly elevated annual premium payment (₹45,000 vs routine ₹6,500) at 00:45 AM
    borderline_date = base_date + timedelta(days=88)
    txns.append({
        "transaction_id": "TXN-BOR-9901",
        "customer_id": "CUST-1003",
        "timestamp": borderline_date.replace(hour=0, minute=45).isoformat(),
        "description": "Annual Premium Auto Insurance Renewal",
        "payee": "ICICI Lombard Auto Insurance",
        "amount": 45000.00,
        "channel": "Debit Card",
        "category": "Insurance",
        "status": "Completed"
    })

    return {
        "customer_id": "CUST-1003",
        "customer_name": "Elena Rostova",
        "account_type": "Standard Savings Account",
        "currency": "INR",
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

    print("Synthetic INR datasets generated successfully in data/")


if __name__ == "__main__":
    main()
