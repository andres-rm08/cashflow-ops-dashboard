import pandas as pd
import numpy as np

np.random.seed(42)

n_ops = 200
ops_ids = [f"OP-{i:03d}" for i in range(1, n_ops + 1)]

ops = pd.DataFrame({
    "ops_item_id": ops_ids,
    "type": np.random.choice(
        ["invoice_followup", "data_fix", "client_contact"],
        size=n_ops,
        p=[0.5, 0.3, 0.2]
    ),
    "sla_due": pd.Timestamp("2025-11-10") - pd.to_timedelta(
        np.random.randint(-5, 15, size=n_ops), unit="D"
    ),
    "owner": np.random.choice(["Ana", "Luis", "Marc", "Sofia"], size=n_ops),
    "age_days": np.random.randint(0, 11, size=n_ops),
    "status": "open",
})

n_tx = 200
missing_rate = 0.1  

p_real = (1 - missing_rate) / n_ops
probs = [p_real] * n_ops + [missing_rate]

tx_ops_choices = np.random.choice(
    ops_ids + [None],
    size=n_tx,
    p=probs
)

transactions = pd.DataFrame({
    "transaction_id": [f"T-{i:03d}" for i in range(1, n_tx + 1)],
    "ops_item_id": tx_ops_choices,
    "client_id": np.random.choice([f"C{i:03d}" for i in range(1, 11)], size=n_tx),
    "invoice_id": [f"INV-{1000+i}" for i in range(n_tx)],
    "amount": np.random.randint(500, 15000, size=n_tx),
    "due_date": pd.Timestamp("2025-11-05") - pd.to_timedelta(
        np.random.randint(0, 40, size=n_tx), unit="D"
    ),
    "status": np.random.choice(["open", "overdue"], size=n_tx, p=[0.6, 0.4]),
})


risk = pd.DataFrame({
    "ops_item_id": ops_ids,
    "missing_fields": np.random.randint(0, 4, size=n_ops),
    "dup_flag": np.random.choice([0, 1], size=n_ops, p=[0.9, 0.1]),
    "error_rate_by_client": np.random.uniform(0.0, 0.2, size=n_ops).round(2),
    "blocks_invoicing": np.random.choice([0, 1], size=n_ops, p=[0.8, 0.2]),
})


clients = pd.DataFrame({
    "client_id": [f"C{i:03d}" for i in range(1, 11)],
    "client_name": [f"Client {i}" for i in range(1, 11)],
    "tier": np.random.choice(["A", "B", "C"], size=10, p=[0.4, 0.4, 0.2]),
})


ops.to_csv("data/ops_items.csv", index=False)
transactions.to_csv("data/transactions.csv", index=False)
risk.to_csv("data/risk_data_quality.csv", index=False)
clients.to_csv("data/client_tier.csv", index=False)

print("Generated data in data/")
