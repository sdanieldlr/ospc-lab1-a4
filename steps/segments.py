"""Number of orders per region, quarter and order size (segments.csv)."""

import os
import pandas as pd
import numpy as np

DATA = os.environ.get("DATA", os.path.expanduser("~/data/sales_2025.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/data/out"))
os.makedirs(OUT, exist_ok=True)

totals = None

for chunk in pd.read_csv(
    DATA,
    usecols=["order_date", "region", "quantity", "unit_price"],
    chunksize=100000
):
    quarter = pd.to_datetime(chunk["order_date"]).dt.quarter
    value = chunk["quantity"] * chunk["unit_price"]

    size = np.where(
        value >= 500, "large",
        np.where(value >= 100, "medium", "small")
    )

    chunk["segment"] = "Q" + quarter.astype(str) + " " + size

    counts = chunk.groupby(["region", "segment"]).size()

    if totals is None:
        totals = counts
    else:
        totals = totals.add(counts, fill_value=0)

if totals is None:
    raise ValueError("The input dataset is empty")

table = totals.astype(int).unstack(fill_value=0)
table.to_csv(os.path.join(OUT, "segments.csv"))

print("segments: done")
