"""
Referral Multiplier Simulation for Basis Points System
Diamond's proposal: multiplier-based referrals instead of flat % transfer

Two layers:
  L1: Per-referee quality bonus (based on referee's base points)
  L2: Per-referee's-referee bonus (smaller, based on L2 referee points)
  + Total count tier bonus (based on number of active referrals)

Formula:
  referral_mult = sum(per_referee_L1_bonuses) + sum(per_referee_L2_bonuses) + count_tier_bonus
  final_points = base_points × diversity_mult × streak_mult × (1 + referral_mult)
"""

# ============================================================
# PARAMETER CONFIGURATIONS TO TEST
# ============================================================

configs = {
    "Conservative": {
        "label": "Conservative — referrals are a nice bonus",
        # L1: Per-referee quality tiers (referee base points → referrer multiplier bonus)
        "l1_tiers": [
            (1000,   0.005),   # Egg referee
            (5000,   0.01),    # Shrimp referee
            (25000,  0.02),    # Crab+ referee
            (100000, 0.03),    # Lobster+ referee
        ],
        "l1_cap_per_referee": 0.03,  # Max bonus from any single referee
        "l1_cap_total": 0.30,        # Max total L1 bonus (caps at 10 quality referees)
        
        # L2: Per-L2-referee quality tiers (referee's referee → referrer bonus)
        "l2_tiers": [
            (1000,   0.001),
            (5000,   0.002),
            (25000,  0.005),
            (100000, 0.008),
        ],
        "l2_cap_per_referee": 0.008,
        "l2_cap_total": 0.10,        # Max total L2 bonus
        
        # Count tiers (total L1 referrals with any activity)
        "count_tiers": [
            (3,  0.05),
            (10, 0.10),
            (20, 0.15),
            (50, 0.20),
        ],
    },
    
    "Moderate": {
        "label": "Moderate — referrals are a meaningful advantage",
        "l1_tiers": [
            (1000,   0.008),
            (5000,   0.015),
            (25000,  0.03),
            (100000, 0.05),
        ],
        "l1_cap_per_referee": 0.05,
        "l1_cap_total": 0.50,
        
        "l2_tiers": [
            (1000,   0.002),
            (5000,   0.004),
            (25000,  0.008),
            (100000, 0.012),
        ],
        "l2_cap_per_referee": 0.012,
        "l2_cap_total": 0.15,
        
        "count_tiers": [
            (3,  0.08),
            (10, 0.15),
            (20, 0.25),
            (50, 0.35),
        ],
    },
    
    "Aggressive": {
        "label": "Aggressive — referrals are a core strategy",
        "l1_tiers": [
            (1000,   0.01),
            (5000,   0.025),
            (25000,  0.05),
            (100000, 0.08),
        ],
        "l1_cap_per_referee": 0.08,
        "l1_cap_total": 0.80,
        
        "l2_tiers": [
            (1000,   0.003),
            (5000,   0.006),
            (25000,  0.012),
            (100000, 0.02),
        ],
        "l2_cap_per_referee": 0.02,
        "l2_cap_total": 0.25,
        
        "count_tiers": [
            (3,  0.10),
            (10, 0.20),
            (20, 0.40),
            (50, 0.60),
        ],
    },
}

# ============================================================
# PLAYER ARCHETYPES
# ============================================================

players = {
    "Solo Grinder": {
        "desc": "Diverse, active, no referrals",
        "base_pts_daily": 800,     # Active across categories
        "diversity_mult": 16,       # CP ~12 (diverse)
        "streak_mult": 1.7,         # 7-day streak
        "l1_referees": [],
        "l2_referees": [],          # Referees of referees
    },
    "Casual + 3 Friends": {
        "desc": "Moderate activity, brought 3 friends",
        "base_pts_daily": 400,
        "diversity_mult": 8,        # CP ~7
        "streak_mult": 1.3,
        "l1_referees": [3000, 5000, 8000],  # Their friends' base points
        "l2_referees": [1000, 2000],         # Friends' friends
    },
    "Referral Builder": {
        "desc": "Active + built a referral network of 12",
        "base_pts_daily": 600,
        "diversity_mult": 12,
        "streak_mult": 1.5,
        "l1_referees": [2000, 3000, 5000, 8000, 12000, 15000, 1000, 500, 4000, 6000, 20000, 30000],
        "l2_referees": [1000, 2000, 500, 3000, 1500, 2500, 800, 4000],
    },
    "Whale Recruiter": {
        "desc": "Moderate activity, recruited 25 agents (some very active)",
        "base_pts_daily": 500,
        "diversity_mult": 8,
        "streak_mult": 1.4,
        "l1_referees": [50000, 80000, 30000, 25000, 15000, 10000, 10000, 8000, 5000, 5000,
                        3000, 3000, 3000, 2000, 2000, 2000, 1000, 1000, 1000, 1000,
                        500, 500, 500, 500, 500],
        "l2_referees": [5000, 3000, 2000, 8000, 1000, 1500, 2000, 500, 1000, 3000,
                        2000, 1000, 500, 500, 200],
    },
    "Power User + Network": {
        "desc": "Top-tier solo + 8 quality referrals",
        "base_pts_daily": 1000,
        "diversity_mult": 32,
        "streak_mult": 2.0,
        "l1_referees": [30000, 50000, 20000, 15000, 40000, 10000, 25000, 60000],
        "l2_referees": [5000, 10000, 3000, 8000, 2000, 15000],
    },
    "Referral-Only (No Activity)": {
        "desc": "Recruited 15 people but doesn't use platform",
        "base_pts_daily": 50,       # Minimal activity
        "diversity_mult": 1,        # No diversity
        "streak_mult": 1.0,         # No streak
        "l1_referees": [5000, 10000, 8000, 3000, 2000, 15000, 20000, 1000, 5000, 3000,
                        2000, 1000, 500, 8000, 12000],
        "l2_referees": [2000, 3000, 1000, 5000, 500],
    },
    "Bot Farm (100 wallets x 1 ref each)": {
        "desc": "Sybil: 100 wallets, each refers 1 other bot wallet",
        "base_pts_daily": 200,      # Single-category farming
        "diversity_mult": 1,        # No diversity (1 category)
        "streak_mult": 1.0,
        "l1_referees": [200],       # Each bot refers one other bot
        "l2_referees": [200],
    },
}

# ============================================================
# SIMULATION
# ============================================================

def get_tier_bonus(points, tiers):
    """Get the multiplier bonus for a given point threshold."""
    bonus = 0
    for threshold, mult in tiers:
        if points >= threshold:
            bonus = mult
    return bonus

def calc_referral_mult(player, config):
    """Calculate total referral multiplier for a player under a config."""
    # L1: Per-referee quality
    l1_total = 0
    active_l1_count = 0
    for referee_pts in player["l1_referees"]:
        if referee_pts > 0:
            active_l1_count += 1
        bonus = get_tier_bonus(referee_pts, config["l1_tiers"])
        bonus = min(bonus, config["l1_cap_per_referee"])
        l1_total += bonus
    l1_total = min(l1_total, config["l1_cap_total"])
    
    # L2: Per-L2-referee quality
    l2_total = 0
    for referee_pts in player["l2_referees"]:
        bonus = get_tier_bonus(referee_pts, config["l2_tiers"])
        bonus = min(bonus, config["l2_cap_per_referee"])
        l2_total += bonus
    l2_total = min(l2_total, config["l2_cap_total"])
    
    # Count tier bonus (based on L1 active referrals)
    count_bonus = 0
    for threshold, mult in config["count_tiers"]:
        if active_l1_count >= threshold:
            count_bonus = mult
    
    return l1_total, l2_total, count_bonus

def simulate():
    days = 30  # Simulate 30 days
    
    print("=" * 100)
    print("REFERRAL MULTIPLIER SIMULATION — 30-DAY PROJECTION")
    print("=" * 100)
    print()
    print("Formula: final_daily = base_pts × diversity × streak × (1 + L1_bonus + L2_bonus + count_bonus)")
    print()
    
    for config_name, config in configs.items():
        print()
        print(f"{'=' * 100}")
        print(f"CONFIG: {config['label']}")
        print(f"{'=' * 100}")
        print()
        
        # Header
        print(f"{'Player':<35} {'Base/day':>8} {'Div':>4} {'Strk':>5} "
              f"{'L1':>6} {'L2':>6} {'Count':>6} {'Ref Tot':>7} "
              f"{'Daily (no ref)':>14} {'Daily (w/ ref)':>14} {'Ref Boost':>10} "
              f"{'30d Total':>10}")
        print("-" * 145)
        
        results = []
        for name, player in players.items():
            l1, l2, count = calc_referral_mult(player, config)
            ref_total = l1 + l2 + count
            
            base = player["base_pts_daily"]
            div = player["diversity_mult"]
            streak = player["streak_mult"]
            
            daily_no_ref = base * div * streak
            daily_w_ref = base * div * streak * (1 + ref_total)
            boost_pct = ref_total * 100
            total_30d = daily_w_ref * days
            
            results.append((name, total_30d))
            
            print(f"{name:<35} {base:>8} {div:>4} {streak:>5.1f} "
                  f"{l1:>6.3f} {l2:>6.3f} {count:>6.2f} {ref_total:>7.3f} "
                  f"{daily_no_ref:>14,.0f} {daily_w_ref:>14,.0f} {boost_pct:>9.1f}% "
                  f"{total_30d:>10,.0f}")
        
        print()
        
        # Ranking
        results.sort(key=lambda x: x[1], reverse=True)
        print("  Ranking:")
        for i, (name, total) in enumerate(results, 1):
            print(f"    #{i} {name}: {total:,.0f} pts")
        print()
        
        # Key ratios
        solo = next(t for n, t in results if n == "Solo Grinder")
        referral_only = next(t for n, t in results if n == "Referral-Only (No Activity)")
        bot = next(t for n, t in results if n == "Bot Farm (100 wallets x 1 ref each)")
        power = next(t for n, t in results if n == "Power User + Network")
        whale_rec = next(t for n, t in results if n == "Whale Recruiter")
        
        print("  Key Ratios:")
        print(f"    Solo Grinder vs Referral-Only:     {solo/referral_only:.1f}x (should be >>1)")
        print(f"    Solo Grinder vs Bot Farm per-wallet: {solo/bot:.1f}x (should be >>1)")
        print(f"    Power User vs Whale Recruiter:      {power/whale_rec:.1f}x")
        print(f"    Referral-Only 30d total:            {referral_only:,.0f} (should feel small)")
        print(f"    Bot Farm per-wallet 30d:            {bot:,.0f} (should be tiny)")
    
    # ============================================================
    # COMPARE OLD vs NEW SYSTEM
    # ============================================================
    print()
    print("=" * 100)
    print("OLD SYSTEM COMPARISON (10% L1 + 3% L2 flat transfer)")
    print("=" * 100)
    print()
    
    print("Under the old system, the Whale Recruiter's referees generate points directly:")
    
    # Old system: referrer gets 10% of each L1 referee's points + 3% of L2
    for name, player in [("Whale Recruiter", players["Whale Recruiter"]),
                          ("Referral-Only (No Activity)", players["Referral-Only (No Activity)"])]:
        l1_pts_from_refs = sum(p * 0.10 for p in player["l1_referees"])
        l2_pts_from_refs = sum(p * 0.03 for p in player["l2_referees"])
        own_daily = player["base_pts_daily"] * player["diversity_mult"] * player["streak_mult"]
        ref_income = l1_pts_from_refs + l2_pts_from_refs
        
        print(f"\n  {name}:")
        print(f"    Own daily points:          {own_daily:>10,.0f}")
        print(f"    L1 referral income (10%):  {l1_pts_from_refs:>10,.0f} (one-time from ref base pts)")
        print(f"    L2 referral income (3%):   {l2_pts_from_refs:>10,.0f}")
        print(f"    Referral as % of own:      {ref_income/max(own_daily,1)*100:>10.1f}%")
    
    # Now moderate config comparison for same players
    print("\n  Under MODERATE config (new system):")
    for name in ["Whale Recruiter", "Referral-Only (No Activity)"]:
        player = players[name]
        l1, l2, count = calc_referral_mult(player, configs["Moderate"])
        ref_total = l1 + l2 + count
        own_daily = player["base_pts_daily"] * player["diversity_mult"] * player["streak_mult"]
        boosted_daily = own_daily * (1 + ref_total)
        ref_bonus_pts = boosted_daily - own_daily
        print(f"\n    {name}:")
        print(f"      Own daily:     {own_daily:>10,.0f}")
        print(f"      Boosted daily: {boosted_daily:>10,.0f} (+{ref_total*100:.1f}%)")
        print(f"      Daily bonus:   {ref_bonus_pts:>10,.0f} (from multiplier)")


if __name__ == "__main__":
    simulate()
