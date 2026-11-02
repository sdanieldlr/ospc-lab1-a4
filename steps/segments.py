"""Number of orders per region, quarter and order size."""

import os
import pandas as pd
import numpy as np

DATA = os.environ.get("DATA", os.path.expanduser("~/data/sales_2025.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/data/out"))
os.makedirs(OUT, exist_ok=True)

all_counts = []

for chunk in pd.read_csv(
    DATA,
    usecols=["order_date", "region", "quantity", "unit_price"],
    chunksize=100000
):
    quarter = pd.to_datetime(chunk["order_date"]).dt.quarter
    value = chunk["quantity"] * chunk["unit_price"]

    size = np.where(
        value >= 500, 2,
        np.where(value >= 100, 1, 0)
    )

    counts = chunk.groupby(
        ["region", quarter, size]
    ).size()

    all_counts.append(counts)

if not all_counts:
    raise ValueError("The input dataset is empty")

totals = pd.concat(all_counts).groupby(level=[0, 1, 2]).sum()

table = totals.unstack(level=[1, 2], fill_value=0)

table.columns = [
    f"Q{quarter} {['small', 'medium', 'large'][size]}"
    for quarter, size in table.columns
]

table = table.reindex(
    columns=[
        f"Q{q} {s}"
        for q in range(1, 5)
        for s in ["large", "medium", "small"]
    ],
    fill_value=0
)

table.to_csv(os.path.join(OUT, "segments.csv"))

print("segments: done")
