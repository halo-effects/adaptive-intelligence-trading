"""Bottom to K×D cross: timing and % missed"""
from datetime import datetime

data = [
    ("ETH", "2021-06-22", 1700.48, "2021-08-01", 2555.69),
    ("ETH", "2022-02-24", 2300.00, "2022-03-27", 3295.65),
    ("ETH", "2022-06-18", 881.56, "2022-07-17", 1338.65),
    ("ETH", "2023-10-12", 1521.00, "2023-10-22", 1663.70),
    ("ETH", "2025-04-09", 1385.05, "2025-05-04", 1808.86),
    ("BTC", "2022-09-21", 18125.98, "2022-10-09", 19439.02),
    ("BTC", "2024-09-06", 52550.00, "2024-09-22", 63578.76),
    ("SOL", "2025-04-07", 95.26, "2025-04-20", 137.86),
    ("LINK", "2022-02-24", 11.40, "2022-03-27", 16.87),
    ("LINK", "2024-08-05", 8.08, "2024-08-25", 12.10),
    ("XRP", "2024-07-05", 0.38, "2024-07-14", 0.52),
    ("XRP", "2025-12-19", 1.77, "2026-01-11", 2.07),
]

print("BOTTOM to 2W K×D CROSS: Time & % Missed (K<5 threshold)")
print("=" * 70)
header = f"{'Coin':6} {'Bottom':12} {'Bot$':>10} {'KxD Date':12} {'KxD$':>10} {'Days':>5} {'%Up':>7}"
print(header)
print("-" * 70)

all_days = []
all_pcts = []
for coin, bd_s, bp, cd_s, cp in data:
    bd = datetime.strptime(bd_s, "%Y-%m-%d")
    cd = datetime.strptime(cd_s, "%Y-%m-%d")
    days = (cd - bd).days
    pct = (cp / bp - 1) * 100
    all_days.append(days)
    all_pcts.append(pct)
    print(f"{coin:6} {bd_s:12} {bp:10.2f} {cd_s:12} {cp:10.2f} {days:5d} {pct:+7.1f}%")

print("-" * 70)
avg_d = sum(all_days) / len(all_days)
avg_p = sum(all_pcts) / len(all_pcts)
med_d = sorted(all_days)[len(all_days) // 2]
med_p = sorted(all_pcts)[len(all_pcts) // 2]
print(f"Average: {avg_d:.0f} days, {avg_p:+.1f}% from bottom")
print(f"Median:  {med_d} days, {med_p:+.1f}%")
print(f"Range:   {min(all_days)}-{max(all_days)} days, {min(all_pcts):+.1f}% to {max(all_pcts):+.1f}%")

# Also note: BTC 2022 cross was at LOWER price than bottom
# (cross came during continued downtrend - false signal)
print()
print("NOTE: BTC 2022-09 cross at $19,439 vs bottom $18,126 = only +7.2%")
print("      but BTC went lower after (Nov $15,476). This was mid-bear.")
