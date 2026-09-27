"""Synthetic HR dataset (employees, hires, exits) for the HR Analytics dashboard.

Attrition drivers are simulated on purpose (overtime, low rating, junior grade,
first-year tenure) so the dashboard has real patterns to surface.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 21
DEPTS = {"Sales": 0.26, "Operations": 0.24, "Supply Chain": 0.14, "Finance": 0.1,
         "IT": 0.14, "HR": 0.05, "Customer Service": 0.07}
GRADES = ["L1", "L2", "L3", "L4", "L5"]
LOCATIONS = ["Gurugram", "Bengaluru", "Mumbai", "Hyderabad", "Pune"]


def generate(n: int = 1800) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    hire = pd.Timestamp("2019-01-01") + pd.to_timedelta(rng.integers(0, 2550, n), unit="D")
    grade = rng.choice(GRADES, n, p=[0.34, 0.3, 0.2, 0.11, 0.05])
    df = pd.DataFrame({
        "employee_id": [f"E{i:05d}" for i in range(1, n + 1)],
        "department": rng.choice(list(DEPTS), n, p=list(DEPTS.values())),
        "grade": grade,
        "gender": rng.choice(["Female", "Male"], n, p=[0.41, 0.59]),
        "location": rng.choice(LOCATIONS, n),
        "hire_date": hire,
        "employment_type": rng.choice(["Permanent", "Contract"], n, p=[0.8, 0.2]),
        "overtime": rng.random(n) < 0.28,
        "rating": rng.choice([1, 2, 3, 4, 5], n, p=[0.05, 0.15, 0.45, 0.25, 0.1]),
    })
    # monthly exit hazard
    hazard = 0.009 * np.ones(n)
    hazard *= np.where(df["overtime"], 2.0, 1.0)
    hazard *= np.where(df["rating"] <= 2, 1.8, 1.0)
    hazard *= np.where(df["grade"] == "L1", 1.5, np.where(df["grade"].isin(["L4", "L5"]), 0.6, 1.0))
    hazard *= np.where(df["employment_type"] == "Contract", 1.4, 1.0)
    exit_dates, reasons = [], []
    end = pd.Timestamp("2025-12-31")
    for h, start, first_year in zip(hazard, df["hire_date"], rng.random(n), strict=True):
        months = int((end - start).days / 30)
        t = rng.geometric(min(h * (1.6 if first_year < 0.5 else 1.0), 0.99))
        if t <= months:
            exit_dates.append(start + pd.Timedelta(days=int(t * 30)))
            reasons.append(rng.choice(["Resigned - better offer", "Resigned - relocation",
                                       "Resigned - career change", "Terminated - performance",
                                       "Contract ended"], p=[0.45, 0.15, 0.15, 0.12, 0.13]))
        else:
            exit_dates.append(pd.NaT)
            reasons.append(None)
    df["exit_date"] = exit_dates
    df["exit_reason"] = reasons
    df["exit_type"] = np.where(df["exit_reason"].isna(), None,
                               np.where(df["exit_reason"].str.startswith("Resigned", na=False),
                                        "Voluntary", "Involuntary"))
    return df


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "hr_employees.csv"
    generate().to_csv(out, index=False)
    print(out)
