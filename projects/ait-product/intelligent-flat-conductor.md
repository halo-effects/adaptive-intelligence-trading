# Intelligent ROUTER Conductor Design — V13 Always-On Architecture

**Date:** 2026-02-27  
**Author:** Subagent (Gee Gee)  
**Version:** 3.0  
**Status:** Design Complete - ROUTER Vision  
**Implementation Priority:** High (V13 Gap G3)

---

## Executive Summary

The V13 trading engine is undergoing a fundamental architectural transformation: **ROUTER evolves from a passive phase to an always-on orchestration layer** that monitors signals during every phase and triggers all transitions.

**The Paradigm Shift:**

**❌ Old design (wrong):** ROUTER is a phase you enter between transitions. Each phase has its own exit logic scattered across `_check_dca()`, `_check_markup()`, `_check_flat()`, `_check_markdown()`.

**✅ New design (correct):** ROUTER is an **always-on orchestration layer** that monitors signals during EVERY phase and triggers ALL transitions. It's not a phase — it's the brain. The phases (DCA, MARKUP, MARKDOWN) just execute their strategy. ROUTER decides when to change.

**Core architectural principle:** Brett's quote captures the vision: *"The router will have all the signals and indicators. It will constantly receive the realtime data and when conditions are met to transition, the router takes action. This would apply to all the gates. For example system in Markup and Router watches a regime change into Range, switches to DCA."*

---

## 1. Architecture Overview — ROUTER as Central Nervous System

### Always-On Orchestration Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ROUTER (Always Running)                   │
│                        Central Nervous System                      │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │ DCA Phase   │  │MARKUP Phase │  │MARKDOWN Ph. │  │ ROUTER Eval ││
│  │ Monitoring  │  │ Monitoring  │  │ Monitoring  │  │ Monitoring  ││
│  │             │  │             │  │             │  │             ││
│  │ Watch for:  │  │ Watch for:  │  │ Watch for:  │  │ Watch for:  ││
│  │• HH_HL+Fib  │  │• Top signals│  │• Bottom sig │  │• Confidence ││
│  │  →MARKUP    │  │• Ranging    │  │• Ranging    │  │  scoring    ││
│  │• LH_LL+ADX  │  │• Failure    │  │• Failure    │  │• 3-day min ││
│  │  +Fib→MARK  │  │• Tier gates │  │• Tier gates │  │• Route best ││
│  │  DOWN       │  │             │  │             │  │             ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│
│                                                                     │
│         Every gate in the system lives inside ROUTER:              │
│         • Markup entry gates (HH_HL ≥ 2 + Fib_support + CFGI > 40) │
│         • Markdown entry gates (LH_LL ≥ 2 + ADX > 20 + Fib_break)  │
│         • Top detection (2W StochRSI OB93, 1W OB85, K<50 failsafe) │
│         • Bottom detection (Weekly CFGI RSI(7) < 40 + structure)   │
│         • Failure detection (DD>25%+ADX>25 markup/markdown fails)  │
│         • Ranging detection (ADX < 20 sustained)                   │
│         • Dynamic tier gates (T2/T3 signal-based confirmation)     │
└─────────────────────────────────────────────────────────────────────┘
                           ↓ All decisions flow down ↓
         
         DCA          MARKUP         MARKDOWN      ROUTER_EVAL
    (accumulate)  (ride trend up) (ride trend down)  (path score)
```

### Key Principles

1. **One decision engine** — all transition logic centralized in ROUTER, not scattered across 4 phase handlers
2. **Always monitoring** — ROUTER evaluates signals on every tick regardless of current phase
3. **Phases just execute** — DCA accumulates, MARKUP rides the trend, MARKDOWN rides the decline. They don't decide when to exit.
4. **Signal-driven, not timer-driven** — no fixed delays, no arbitrary timeouts
5. **Universal** — same logic for all coins, no coin-specific hacks

### Implementation Architecture

```python
def _router_evaluate(self, date, price):
    """ROUTER always-on evaluation - called every daily tick regardless of phase."""
    
    # Universal signal stack computed once
    signals = self._compute_router_signals(date, price)
    
    if self.phase == Phase.DCA:
        self._router_check_dca_exits(date, price, signals)
    elif self.phase == Phase.MARKUP:
        self._router_check_markup_exits(date, price, signals)
        self._router_check_tier_adds(date, price, signals)
    elif self.phase == Phase.MARKDOWN:
        self._router_check_markdown_exits(date, price, signals)
        self._router_check_short_tiers(date, price, signals)
    elif self.phase == Phase.ROUTER:
        self._router_score_paths(date, price, signals)
```

This replaces the current scattered approach:
- ❌ `_check_dca()` with embedded exit logic
- ❌ `_check_markup()` with embedded exit logic  
- ❌ `_check_flat()` with embedded routing logic
- ❌ `_check_markdown()` with embedded exit logic

---

## 2. Signal Evaluation Framework — Universal Signal Stack

### Comprehensive Signal Monitoring

ROUTER monitors all signals used across the entire system on every daily tick:

```python
def _compute_router_signals(self, date, price):
    """Compute comprehensive signal stack for ROUTER decisions."""
    
    return {
        # Structure signals (trend direction)
        'hh_hl_count': self._hh_hl_streak(date, lookback=7),
        'lh_ll_count': self._lh_ll_streak(date, lookback=7),
        'hh_hl_strength': self._hh_hl_strength_delta(date),  # Strengthening vs weakening
        'lh_ll_strength': self._lh_ll_strength_delta(date),
        
        # Momentum signals (trend strength)
        'adx': self._adx(date),
        'adx_below_20_days': self._adx_below_threshold_days(date, 20),
        'adx_trend': self._adx_trend_direction(date, lookback=5),
        
        # Sentiment signals (market psychology)
        'cfgi': self._cfgi(date),
        'cfgi_momentum_5d': self._cfgi_momentum(date, lookback=5),
        'weekly_cfgi_rsi7': self._weekly_cfgi_rsi7(date),  # Bottom detection key signal
        
        # Technical structure (support/resistance)
        'fib_levels': self._fib_levels(date),
        'fib_support': self._price_above_fib_support(price, self._fib_levels(date)),
        'fib_breakdown': self._price_broke_fib_support(price, self._fib_levels(date)),
        'fib_proximity': self._price_fib_proximity(price, self._fib_levels(date)),
        
        # Moving average context
        'price_vs_sma50': self._price_vs_sma50_percent(date, price),
        'price_vs_sma200': self._price_vs_sma200_percent(date, price),
        'sma_alignment': self._sma_alignment_score(date),  # 50>200 bullish, 200>50 bearish
        
        # Top/Bottom detection signals
        'stoch_2w_k': self.pack.stoch_2w.get_k_at(date),
        'stoch_1w_k': self.pack.stoch_1w.get_k_at(date),
        'ob_2w_93': self._signal_near(date, self.ob_exits_2w),
        'ob_1w_85': self._signal_near(date, self.ob85_1w),
        'k_below_50_1w': self._signal_near(date, self.failsafe_1w),
        
        # Regime detection
        'ranging_confirmed': self.adx_below_20_streak >= 21,  # ADX<20 for 21 days
        'trend_momentum': 'strong' if signals.get('adx', 0) > 25 else 'weak' if signals.get('adx', 0) > 20 else 'ranging',
        
        # Meta
        'price': price,
        'date': date,
        'phase': self.phase,
        'days_in_phase': (date - self.phase_start_date).days if self.phase_start_date else 0
    }
```

### Signal Caching & Performance

```python
class RouterSignalCache:
    """Performance optimization: cache expensive signal calculations."""
    
    def __init__(self):
        self._cache = {}
        self._cache_date = None
    
    def get_signals(self, date, price, engine):
        """Get cached signals for date or compute fresh."""
        if self._cache_date != date:
            self._cache = engine._compute_router_signals(date, price)
            self._cache_date = date
        return self._cache
```

This ensures expensive calculations like weekly CFGI RSI(7), Fibonacci levels, and ADX streaks are computed once per day and reused across all ROUTER evaluations.

---

## 3. Phase-Specific Monitoring — What ROUTER Watches During Each Phase

### During DCA Phase: Entry Signal Monitoring

```python
def _router_check_dca_exits(self, date, price, signals):
    """ROUTER monitoring during DCA phase - watch for directional signals."""
    
    # Continue DCA mechanics
    self._dca_tick(date, price)
    
    # DCA → MARKUP: HH_HL + Fib_support + sentiment confirmation
    if self._evaluate_markup_entry(signals):
        # Graceful DCA handling (let positions ride)
        self._router_transition(date, Phase.MARKUP, "DCA→MARKUP: HH_HL+Fib_support", signals)
        self._buy(date, self.cfg.TIER1_PCT, 1)
        return
    
    # DCA → MARKDOWN: LH_LL + ADX>20 + Fib_break  
    if self._evaluate_markdown_entry(signals):
        # Hard exit DCA (incompatible with shorts)
        if self.dca_coins > 0:
            self._dca_close(date, 'ROUTER_EXIT_MARKDOWN')
        self._router_transition(date, Phase.MARKDOWN, "DCA→MARKDOWN: LH_LL+ADX+Fib_break", signals)
        return

def _evaluate_markup_entry(self, signals):
    """ROUTER evaluation of DCA→MARKUP transition."""
    structure_ok = signals['hh_hl_count'] >= 2
    support_ok = signals['fib_support']
    sentiment_ok = signals['cfgi'] > 40 or signals['weekly_cfgi_rsi7'] < 40  # Include bear-OFF
    
    confidence = 0
    if structure_ok: confidence += 40
    if support_ok: confidence += 30  
    if sentiment_ok: confidence += 25
    
    return confidence >= 75  # High confidence required for DCA exit

def _evaluate_markdown_entry(self, signals):
    """ROUTER evaluation of DCA→MARKDOWN transition."""
    structure_ok = signals['lh_ll_count'] >= 2
    momentum_ok = signals['adx'] > 20
    breakdown_ok = signals['fib_breakdown']
    
    confidence = 0
    if structure_ok: confidence += 40
    if momentum_ok: confidence += 30
    if breakdown_ok: confidence += 25
    
    return confidence >= 75  # High confidence required for DCA exit
```

### During MARKUP Phase: Exit Signal & Tier Monitoring

```python
def _router_check_markup_exits(self, date, price, signals):
    """ROUTER monitoring during MARKUP phase - watch for exit signals."""
    
    # Let DCA positions ride (graceful coexistence)
    if self.dca_coins > 0:
        self._dca_tick(date, price)
    
    # Update peak tracking for top detection
    if not np.isnan(signals['stoch_2w_k']) and signals['stoch_2w_k'] > self.peak_2w_k:
        self.peak_2w_k = signals['stoch_2w_k']
    
    # Primary exit: Top detection (2W OB93)
    if signals['ob_2w_93']:
        pnl = self._sell_all(date, 'ROUTER_TOP_2W_OB93')
        if self.dca_coins > 0:
            self._dca_close(date, 'TOP_EXIT')
        self._router_transition(date, Phase.ROUTER, f'MARKUP→ROUTER: 2W OB93 top, pnl={pnl:+.1f}%', signals)
        self._reset_top_state()
        return
    
    # Fallback exit: 1W OB85 when 2W never reached OB
    if self.peak_2w_k < 93 and signals['ob_1w_85'] and self.early_warning_date:
        pnl = self._sell_all(date, f'ROUTER_TOP_1W_OB85_FALLBACK (2W_peak={self.peak_2w_k:.0f})')
        if self.dca_coins > 0:
            self._dca_close(date, 'TOP_EXIT')
        self._router_transition(date, Phase.ROUTER, 
            f'MARKUP→ROUTER: 1W OB85 fallback (2W peak={self.peak_2w_k:.0f}), pnl={pnl:+.1f}%', signals)
        self._reset_top_state()
        return
    
    # Failsafe exit: 1W K<50 after armed
    if self.failsafe_armed and signals['k_below_50_1w']:
        pnl = self._sell_all(date, 'ROUTER_FAILSAFE_1W_K50')
        if self.dca_coins > 0:
            self._dca_close(date, 'TOP_EXIT')
        self._router_transition(date, Phase.ROUTER, f'MARKUP→ROUTER: Failsafe 1W K<50, pnl={pnl:+.1f}%', signals)
        self._reset_top_state()
        return
    
    # Ranging exit: Trend exhaustion (ADX<20 sustained)
    if signals['days_in_phase'] >= 14 and signals['ranging_confirmed']:
        pnl = self._sell_all(date, f'ROUTER_RANGING (ADX<20 for {signals["adx_below_20_days"]}d)')
        if self.dca_coins > 0:
            self._dca_close(date, 'RANGING_EXIT')
        self._router_transition(date, Phase.ROUTER,
            f'MARKUP→ROUTER: Ranging confirmed, ADX<20 for {signals["adx_below_20_days"]}d, pnl={pnl:+.1f}%', signals)
        self._reset_top_state()
        return
    
    # Failure exit: Drawdown + confirmed downtrend
    if self.entry_price > 0:
        dd_from_entry = (price - self.entry_price) / self.entry_price
        if dd_from_entry < -0.25 and signals['adx'] > 25:  # 25% DD + strong downtrend
            pnl = self._sell_all(date, f'ROUTER_MARKUP_FAIL (dd={dd_from_entry*100:.0f}%, ADX={signals["adx"]:.0f})')
            if self.dca_coins > 0:
                self._dca_close(date, 'MARKUP_FAIL')
            self._router_transition(date, Phase.ROUTER,
                f'MARKUP→ROUTER: Failure {dd_from_entry*100:.0f}% below entry, ADX={signals["adx"]:.0f}', signals)
            self._reset_top_state()
            return

def _router_check_tier_adds(self, date, price, signals):
    """ROUTER dynamic tier confirmation during MARKUP phase."""
    
    if self.tier >= 3:
        return
    
    days_in_phase = signals['days_in_phase']
    
    # T2 Confirmation: Structure + sentiment + minimum time (signal-driven vs 7-day fixed)
    if self.tier == 1 and days_in_phase >= 3:
        structure_ok = signals['hh_hl_count'] >= 1
        sentiment_ok = signals['cfgi'] > 40 or signals['weekly_cfgi_rsi7'] < 40  # Include bear-OFF
        price_ok = price >= self.entry_price
        
        if structure_ok and sentiment_ok and price_ok:
            self._buy(date, self.cfg.TIER2_PCT, 2)
            self._log_tier_confirmation(date, 2, "ROUTER T2: Structure+Sentiment", signals)
    
    # T3 Momentum: Strong signals + sustained structure + minimum time (signal-driven vs 14-day fixed)
    elif self.tier == 2 and days_in_phase >= 7:
        strong_structure = signals['hh_hl_count'] >= 2
        momentum_ok = signals['adx'] > 25  # Strong momentum required
        support_ok = signals['fib_support']
        
        confirmation_count = sum([strong_structure, momentum_ok, support_ok])
        
        if confirmation_count >= 2:  # 2 of 3 required
            self._buy(date, self.cfg.TIER3_PCT, 3)
            self._log_tier_confirmation(date, 3, "ROUTER T3: Strong momentum", signals)
```

### During MARKDOWN Phase: Bottom Signal & Tier Monitoring

```python
def _router_check_markdown_exits(self, date, price, signals):
    """ROUTER monitoring during MARKDOWN phase - watch for bottom/ranging/failure signals."""
    
    days_in_phase = signals['days_in_phase']
    
    # Bottom detection: Weekly CFGI RSI(7) < 40 + structure confirmation
    if self._evaluate_bottom_detection(signals):
        self._router_transition(date, Phase.ROUTER, 
            f'MARKDOWN→ROUTER: Bottom detected (Weekly CFGI RSI(7)={signals["weekly_cfgi_rsi7"]:.1f})', signals)
        return
    
    # Ranging exit: Downtrend exhaustion (ADX<20 sustained, minimum 14 days)
    if days_in_phase >= 14 and signals['ranging_confirmed']:
        self._router_transition(date, Phase.ROUTER,
            f'MARKDOWN→ROUTER: Ranging confirmed, ADX<20 for {signals["adx_below_20_days"]}d after {days_in_phase}d markdown', signals)
        return
    
    # Failure exit: Rise above short entry + confirmed uptrend
    if self.short_entry > 0 and self.short_coins > 0:
        rise_from_entry = (price - self.short_entry) / self.short_entry
        if rise_from_entry > 0.25 and signals['adx'] > 25:  # Mirror markup failure logic
            self._router_transition(date, Phase.ROUTER,
                f'MARKDOWN→ROUTER: Failure +{rise_from_entry*100:.0f}% above short entry, ADX={signals["adx"]:.0f}', signals)
            return

def _evaluate_bottom_detection(self, signals):
    """ROUTER bottom detection logic."""
    # Primary: Weekly CFGI RSI(7) bear-OFF signal
    bear_off = signals['weekly_cfgi_rsi7'] < 40 if not np.isnan(signals['weekly_cfgi_rsi7']) else False
    
    # Structure: HH_HL recovery beginning
    recovery_structure = signals['hh_hl_count'] >= 1
    
    # Technical: Price above key support
    support_ok = signals['fib_support']
    
    return bear_off and recovery_structure and support_ok

def _router_check_short_tiers(self, date, price, signals):
    """ROUTER dynamic short tier confirmation during MARKDOWN phase."""
    
    if self.short_tier >= 3:
        return
    
    days_in_phase = signals['days_in_phase']
    
    # Short T2: Structure + sentiment + minimum time (signal-driven vs 7-day fixed)
    if self.short_tier == 1 and days_in_phase >= 3:
        structure_ok = signals['lh_ll_count'] >= 1  
        sentiment_ok = signals['cfgi'] < 40
        price_ok = price <= self.short_entry if self.short_entry > 0 else True
        
        if structure_ok and sentiment_ok and price_ok and self.shorts_enabled and self.capital > 0:
            self._open_short(date, self.cfg.SHORT_TIER2_PCT, 2)
            self._log_tier_confirmation(date, 2, "ROUTER Short T2: Structure+Sentiment", signals)
    
    # Short T3: Strong signals + sustained structure + minimum time (signal-driven vs 14-day fixed)
    elif self.short_tier == 2 and days_in_phase >= 7:
        strong_structure = signals['lh_ll_count'] >= 2
        momentum_ok = signals['adx'] > 25
        breakdown_ok = signals['fib_breakdown']
        price_ok = price <= self.short_entry if self.short_entry > 0 else True
        
        confirmation_count = sum([strong_structure, momentum_ok, breakdown_ok])
        
        if (confirmation_count >= 2 and price_ok and 
            self.shorts_enabled and self.capital > 0):
            self._open_short(date, self.cfg.SHORT_TIER3_PCT, 3)
            self._log_tier_confirmation(date, 3, "ROUTER Short T3: Strong signals", signals)
```

### During ROUTER_EVAL Phase: Path Confidence Scoring

```python
def _router_score_paths(self, date, price, signals):
    """ROUTER evaluation phase - score all paths and route to highest confidence."""
    
    days_in_router = signals['days_in_phase']
    
    # Minimum evaluation period (prevent whipsaw)
    if days_in_router < 3:
        return  # Hold for minimum 3 days
    
    # Check bottom detection override first
    if self._evaluate_bottom_detection(signals):
        self._router_transition(date, Phase.MARKUP, "ROUTER→MARKUP: Bottom override", signals)
        self._buy(date, self.cfg.TIER1_PCT, 1)
        return
    
    # Score all paths simultaneously
    confidence_scores = {
        'MARKUP': self._score_markup_confidence(signals),
        'MARKDOWN': self._score_markdown_confidence(signals),
        'DCA': self._score_dca_confidence(signals)
    }
    
    # Find highest confidence path
    best_path = max(confidence_scores, key=confidence_scores.get)
    best_score = confidence_scores[best_path]
    
    # Route if confidence exceeds threshold
    if best_score >= 60.0:  # ROUTER_EXIT_THRESHOLD
        if best_path == "MARKUP":
            self._router_transition(date, Phase.MARKUP, f"ROUTER→MARKUP: Confidence {best_score:.1f}", signals)
            self._buy(date, self.cfg.TIER1_PCT, 1)
        elif best_path == "MARKDOWN":
            self._router_transition(date, Phase.MARKDOWN, f"ROUTER→MARKDOWN: Confidence {best_score:.1f}", signals)
        elif best_path == "DCA":
            self._router_transition(date, Phase.DCA, f"ROUTER→DCA: Confidence {best_score:.1f}", signals)
    
    # Continue evaluation if no clear winner (no arbitrary timeout)
    self._log_path_evaluation(date, confidence_scores, signals)
```

---

## 4. Dynamic Tier Gates — Signal-Based Confirmation

### Replacing Fixed Time Delays

The new ROUTER architecture eliminates fixed 7-day/14-day tier delays in favor of signal-based confirmation:

**Old (V8) Fixed Timing:**
- T2: Always 7 days after T1
- T3: Always 14 days after T1

**New (ROUTER) Dynamic Timing:**
- T2: 3+ days minimum, triggered by structure + sentiment confirmation
- T3: 7+ days minimum, triggered by strong momentum + 2 of 3 signal confirmations

### Speed Comparison & Benefits

| Tier | V8 Fixed | ROUTER Dynamic | Typical Speed Improvement |
|------|----------|----------------|---------------------------|
| **T2** | 7 days fixed | 3-21 days signal-driven | 2-4 days faster on strong trends |
| **T3** | 14 days fixed | 7-42 days signal-driven | 3-7 days faster on momentum trends |

**Benefits:**
- **Faster entries** when signals confirm quickly (strong trends catch more upside)
- **Delayed entries** when signals are weak (prevents adding to failing positions)  
- **Consistent logic** with ROUTER exit evaluation (same universal signal stack)

### Tier Gate Implementation

```python
def _evaluate_tier2_markup(self, signals, price):
    """ROUTER evaluation of T2 markup confirmation."""
    days_in_phase = signals['days_in_phase']
    
    if days_in_phase < 3:
        return False, "Minimum 3 days not met"
    
    structure_ok = signals['hh_hl_count'] >= 1
    sentiment_ok = signals['cfgi'] > 40 or signals['weekly_cfgi_rsi7'] < 40
    price_ok = price >= self.entry_price if self.entry_price > 0 else True
    
    confidence = 0
    reasons = []
    
    if structure_ok:
        confidence += 40
        reasons.append(f"HH_HL={signals['hh_hl_count']}")
    
    if sentiment_ok:
        confidence += 35
        if signals['weekly_cfgi_rsi7'] < 40:
            reasons.append(f"Bear-OFF (Weekly CFGI RSI={signals['weekly_cfgi_rsi7']:.1f})")
        else:
            reasons.append(f"CFGI={signals['cfgi']:.0f}")
    
    if price_ok:
        confidence += 25
        reasons.append("Price > entry")
    
    confirmed = confidence >= 75
    reason = f"T2 confidence {confidence:.0f}: {', '.join(reasons)}"
    
    return confirmed, reason

def _evaluate_tier3_markup(self, signals, price):
    """ROUTER evaluation of T3 markup confirmation."""
    days_in_phase = signals['days_in_phase']
    
    if days_in_phase < 7:
        return False, "Minimum 7 days not met"
    
    strong_structure = signals['hh_hl_count'] >= 2
    momentum_ok = signals['adx'] > 25
    support_ok = signals['fib_support']
    price_ok = price >= self.entry_price if self.entry_price > 0 else True
    
    confirmations = []
    if strong_structure: confirmations.append("Strong HH_HL")
    if momentum_ok: confirmations.append(f"ADX={signals['adx']:.0f}")
    if support_ok: confirmations.append("Fib support")
    
    confirmed = len(confirmations) >= 2 and price_ok
    reason = f"T3: {len(confirmations)}/3 confirmations ({', '.join(confirmations)})"
    
    return confirmed, reason
```

---

## 5. Transition Matrix — Complete Gate System

### Every Possible Transition

| From | To | Gate Conditions | Min Hold | ROUTER Logic |
|------|----|-----------------|---------|--------------| 
| **DCA** | MARKUP | HH_HL≥2 + Fib_support + CFGI>40/Bear-OFF | 3 days | `_router_check_dca_exits()` |
| **DCA** | MARKDOWN | LH_LL≥2 + ADX>20 + Fib_break | 3 days | `_router_check_dca_exits()` |
| **MARKUP** | ROUTER | 2W OB93 / 1W OB85 fallback / 1W K<50 failsafe | None | `_router_check_markup_exits()` |
| **MARKUP** | ROUTER | Ranging: ADX<20 for 21d (min 14d in phase) | 14 days | `_router_check_markup_exits()` |
| **MARKUP** | ROUTER | Failure: DD>25% + ADX>25 | None | `_router_check_markup_exits()` |
| **MARKDOWN** | ROUTER | Bottom: Weekly CFGI RSI(7)<40 + HH_HL≥1 + Fib_support | 3 days | `_router_check_markdown_exits()` |
| **MARKDOWN** | ROUTER | Ranging: ADX<20 for 21d (min 14d in phase) | 14 days | `_router_check_markdown_exits()` |
| **MARKDOWN** | ROUTER | Failure: Rise>25% + ADX>25 | None | `_router_check_markdown_exits()` |
| **ROUTER** | MARKUP | Confidence score ≥60 or bottom override | 3 days | `_router_score_paths()` |
| **ROUTER** | MARKDOWN | Confidence score ≥60 | 3 days | `_router_score_paths()` |
| **ROUTER** | DCA | Confidence score ≥60 | 3 days | `_router_score_paths()` |

### Gate Priorities & Conflict Resolution

**Priority order** (highest to lowest):
1. **Failure signals** — safety first (DD>25%+ADX>25, Rise>25%+ADX>25)
2. **Top/Bottom detection** — regime change signals (2W OB93, Weekly CFGI RSI(7)<40)
3. **Ranging confirmation** — trend exhaustion (ADX<20 sustained 21d)
4. **Directional entries** — structure + momentum signals

**Conflict resolution:**
- If multiple gates trigger simultaneously, highest priority wins
- Bottom detection override beats normal confidence scoring in ROUTER phase
- Failure detection always overrides tier additions
- Minimum hold times are enforced before any transition

---

## 6. Implementation Plan — Refactoring Roadmap

### Phase 1: Core Architecture Refactor (2-3 days)

**Critical changes:**

1. **Replace scattered check methods** with centralized ROUTER evaluation:
   ```python
   # OLD scattered approach (remove):
   def _check_dca(self, date, price)      # DCA-specific exit logic
   def _check_markup(self, date, price)   # MARKUP-specific exit logic  
   def _check_flat(self, date, price)     # FLAT-specific routing logic
   def _check_markdown(self, date, price) # MARKDOWN-specific exit logic
   
   # NEW centralized approach (implement):
   def _router_evaluate(self, date, price)             # Always-on orchestration
   def _router_check_dca_exits(self, date, price, signals)
   def _router_check_markup_exits(self, date, price, signals)  
   def _router_check_markdown_exits(self, date, price, signals)
   def _router_score_paths(self, date, price, signals)
   ```

2. **Main loop simplification:**
   ```python
   # OLD approach:
   if self.phase == Phase.DCA:
       self._check_dca(date, price)
   elif self.phase == Phase.MARKUP:
       self._check_markup(date, price)
   elif self.phase == Phase.FLAT:
       self._check_flat(date, price)
   elif self.phase == Phase.MARKDOWN:
       self._check_markdown(date, price)
   
   # NEW approach:
   # ROUTER always runs regardless of phase
   self._router_evaluate(date, price)
   ```

3. **Universal signal computation:**
   ```python
   def _compute_router_signals(self, date, price):
       """Single signal stack computed once per tick."""
       # All HH_HL, LH_LL, ADX, CFGI, Fib, StochRSI calculations
       # Cached for performance across all ROUTER methods
   ```

### Phase 2: Signal Infrastructure (1 day)

**New signal methods:**

```python
def _weekly_cfgi_rsi7(self, date):
    """Weekly CFGI RSI(7) for bottom detection."""
    
def _adx_below_threshold_days(self, date, threshold=20):
    """Count consecutive days ADX below threshold."""
    
def _hh_hl_strength_delta(self, date):
    """Recent HH_HL strength vs previous period."""
    
def _price_fib_proximity(self, price, fib_levels):
    """Proximity score to key Fibonacci levels."""
    
def _sma_alignment_score(self, date):
    """SMA 50/200 alignment scoring (bull/bear bias)."""
```

### Phase 3: Confidence Scoring Engine (2 days)

**Path evaluation methods:**

```python
def _score_markup_confidence(self, signals):
    """ROUTER→MARKUP path confidence (0-100)."""
    # Structure (40pts) + Support (30pts) + Sentiment (25pts) + Momentum (15pts) + MA (10pts)
    
def _score_markdown_confidence(self, signals):  
    """ROUTER→MARKDOWN path confidence (0-100)."""
    # Structure (40pts) + Breakdown (30pts) + ADX (25pts) + Sentiment (15pts) + MA (10pts)
    
def _score_dca_confidence(self, signals):
    """ROUTER→DCA path confidence (0-100)."""
    # Ranging (50pts) + No structure (20pts) + CFGI neutral (15pts) + Consolidation (10pts) + Low volatility (5pts)
```

### Phase 4: Enhanced Logging & Diagnostics (1 day)

**Comprehensive logging for debugging:**

```python
def _log_router_evaluation(self, date, phase, signals, transitions_checked):
    """Log ROUTER evaluation details."""
    
def _log_path_evaluation(self, date, confidence_scores, signals):
    """Log path confidence scoring details."""
    
def _log_tier_confirmation(self, date, tier, reason, signals):
    """Log dynamic tier confirmation with signal details."""
    
def _log_bottom_detection(self, date, detected, reason, signals):
    """Log bottom detection evaluation."""

def _router_transition(self, date, new_phase, reason, signals):
    """Centralized phase transition with ROUTER context."""
```

### Phase 5: Testing & Validation (2-3 days)

**Critical validation scenarios:**

1. **Behavior preservation** — ROUTER produces identical results to current V8 logic for baseline validation
2. **Signal monitoring** — Verify all signals are evaluated on every tick regardless of phase  
3. **Transition timing** — Compare transition speed vs current implementation
4. **Bottom detection** — Validate Weekly CFGI RSI(7) < 40 catches historical bottoms
5. **Tier confirmation** — Verify dynamic timing produces better tier entries vs fixed delays
6. **Universal compatibility** — Test across all qualified coins

### Migration Strategy

**Phase 1: Refactor (preserve behavior)**
- Same logic, new architecture
- All tests pass with identical results

**Phase 2: Enhanced routing**  
- Add ROUTER→MARKUP direct path (no longer DCA-only routing)
- Enable bottom detection override

**Phase 3: Dynamic optimization**
- Replace fixed tier timing with signal-based
- Remove arbitrary timeouts

**Phase 4: Performance tuning**
- Optimize signal caching
- Measure speed improvements

---

## 7. Testing Strategy — Validation Framework

### Success Metrics

| Metric | V8 Baseline | ROUTER Target | Success Criteria |
|--------|-------------|---------------|------------------|
| **Phase transition speed** | Mixed (some fast, some timeout) | Signal-driven routing | 30%+ faster avg recognition |
| **Bottom detection accuracy** | N/A (no bottom path) | >80% major bottoms caught | Historical validation |
| **Tier confirmation speed** | 7/14 days fixed | 3-7 days avg | 40%+ faster tier adds |
| **False positive rate** | Variable by phase | <15% across all gates | Improved signal quality |
| **Code complexity** | Scattered across 4 methods | Centralized in ROUTER | Cleaner architecture |

### Test Scenarios

**Baseline preservation (Phase 1):**
1. **ETH/BTC/SOL full backtest** — ROUTER architecture produces identical results to V8
2. **All transition types** — DCA→MARKUP, MARKUP→FLAT, etc. work identically
3. **Tier timing** — T2/T3 adds happen at same times initially

**Enhanced capability (Phase 2-3):**
1. **Bottom detection validation** — Test against known major bottoms (Oct 2023, Jan 2024, etc.)
2. **ROUTER→MARKUP path** — New direct routing without DCA detour
3. **Dynamic tier performance** — Faster adds on strong signals, delayed on weak signals
4. **Signal-driven routing** — No more arbitrary 42-day timeouts

**Stress testing:**
1. **Signal conflicts** — Multiple gates triggering simultaneously
2. **Rapid regime changes** — Market transitioning quickly between phases
3. **Extended ranging periods** — Long periods without clear directional signals  
4. **False signal filtering** — Noise vs genuine regime changes

### Risk Mitigation

**Risk: New architecture introduces bugs**
- **Mitigation:** Preserve V8 implementation as `v13_phase_backtest_v8.py` for comparison and rollback
- **Validation:** Phase 1 must produce identical results before proceeding

**Risk: Always-on ROUTER creates performance overhead**
- **Mitigation:** Signal caching ensures expensive calculations done once per day
- **Monitoring:** Measure execution time vs current scattered approach

**Risk: Centralized logic becomes too complex**
- **Mitigation:** Clear separation of concerns — ROUTER orchestrates, phases execute
- **Documentation:** Comprehensive logging for debugging and understanding

**Risk: Dynamic timing creates instability**
- **Mitigation:** Minimum hold times prevent whipsaw, confidence thresholds prevent false entries
- **Testing:** Extensive backtesting before deploying dynamic features

---

## 8. Code Structure — ROUTER Implementation

### Main ROUTER Loop

```python
def _router_evaluate(self, date, price):
    """ROUTER always-on evaluation - the central nervous system."""
    
    # Compute universal signal stack once per tick
    signals = self._compute_router_signals(date, price)
    
    # Log evaluation context
    self._log_router_evaluation(date, self.phase, signals)
    
    # Phase-specific monitoring (ROUTER watches everything)
    if self.phase == Phase.DCA:
        self._router_check_dca_exits(date, price, signals)
        
    elif self.phase == Phase.MARKUP:
        self._router_check_markup_exits(date, price, signals)
        self._router_check_tier_adds(date, price, signals)
        
    elif self.phase == Phase.MARKDOWN:
        self._router_check_markdown_exits(date, price, signals)
        self._router_check_short_tiers(date, price, signals)
        
    elif self.phase == Phase.ROUTER:
        self._router_score_paths(date, price, signals)
    
    # Update ROUTER state (tracking, caching, etc.)
    self._update_router_state(date, signals)

def _update_router_state(self, date, signals):
    """Update ROUTER tracking variables."""
    
    # ADX streak tracking
    if signals['adx'] < 20:
        self.adx_below_20_streak += 1
    else:
        self.adx_below_20_streak = 0
    
    # Peak tracking for top detection
    if not np.isnan(signals['stoch_2w_k']) and signals['stoch_2w_k'] > self.peak_2w_k:
        self.peak_2w_k = signals['stoch_2w_k']
    
    # Early warning state machine
    if self._signal_near(date, self.early_warnings_1w) and self.early_warning_date is None:
        self.early_warning_date = date
        self._log_router_event(date, f'EARLY_WARNING_1W_97 (2W_peak={self.peak_2w_k:.0f})')
    
    # Failsafe arming
    if (self.early_warning_date and not self.failsafe_armed and 
        (date - self.early_warning_date).days >= self.cfg.FAILSAFE_WINDOW_WEEKS * 7):
        self.failsafe_armed = True
        self._log_router_event(date, 'FAILSAFE_ARMED')
```

### Centralized Transition Handler

```python
def _router_transition(self, date, new_phase, reason, signals):
    """Centralized phase transition with ROUTER context."""
    
    old_phase = self.phase
    
    # Pre-transition cleanup based on current phase
    if old_phase == Phase.MARKUP:
        # Markup positions handled by specific exit logic (sell_all already called)
        pass
        
    elif old_phase == Phase.MARKDOWN:
        # Auto-close shorts when leaving MARKDOWN
        if self.short_coins > 0:
            self._close_short(date, f'ROUTER_TRANSITION_{old_phase}_TO_{new_phase}')
            
    elif old_phase == Phase.ROUTER:
        # ROUTER phase has no positions to close
        pass
        
    elif old_phase == Phase.DCA:
        # DCA handling depends on destination
        if new_phase == Phase.MARKDOWN:
            # Hard exit DCA (incompatible with shorts)
            if self.dca_coins > 0:
                self._dca_close(date, f'ROUTER_TRANSITION_DCA_TO_MARKDOWN')
        # else: Let DCA ride for MARKUP transitions (graceful coexistence)
    
    # Execute phase change
    self._change_phase(date, new_phase, f'ROUTER: {reason}')
    
    # Log transition with signal context
    self._log_router_transition(date, old_phase, new_phase, reason, signals)

def _log_router_transition(self, date, old_phase, new_phase, reason, signals):
    """Log ROUTER transition with full signal context."""
    
    signal_summary = {
        'hh_hl': signals['hh_hl_count'],
        'lh_ll': signals['lh_ll_count'], 
        'adx': signals['adx'],
        'cfgi': signals['cfgi'],
        'weekly_cfgi_rsi7': signals['weekly_cfgi_rsi7'],
        'fib_support': signals['fib_support'],
        'ranging_days': signals['adx_below_20_days'],
        'days_in_phase': signals['days_in_phase']
    }
    
    self.router_log.append({
        'date': date,
        'transition': f'{old_phase} → {new_phase}',
        'reason': reason,
        'signals': signal_summary,
        'price': signals['price']
    })
    
    # Also log to main trade log for continuity
    self.trades.append({
        'date': date,
        'action': f'ROUTER_TRANSITION: {old_phase} → {new_phase}',
        'price': signals['price'],
        'amount': 0,
        'coins': 0,
        'phase': new_phase,
        'reason': reason,
        'router_signals': signal_summary
    })
```

### Performance Optimization

```python
class RouterEngine:
    """ROUTER engine with signal caching and performance optimization."""
    
    def __init__(self, config):
        self.cfg = config
        self.signal_cache = {}
        self.cache_date = None
        
    def _compute_router_signals(self, date, price):
        """Cached signal computation - expensive calculations done once per day."""
        
        # Return cached signals if same date
        if self.cache_date == date:
            return self.signal_cache
        
        # Compute fresh signals
        signals = {
            # Structure (moderate cost)
            'hh_hl_count': self._hh_hl_streak(date, lookback=7),
            'lh_ll_count': self._lh_ll_streak(date, lookback=7),
            
            # Momentum (low cost)  
            'adx': self._adx(date),
            'adx_below_20_days': self._adx_below_threshold_days(date, 20),
            
            # Sentiment (moderate cost)
            'cfgi': self._cfgi(date),
            'cfgi_momentum_5d': self._cfgi_momentum(date, lookback=5),
            
            # Bottom detection (high cost - weekly resampling)
            'weekly_cfgi_rsi7': self._weekly_cfgi_rsi7(date),
            
            # Technical structure (high cost - Fibonacci calculation)
            'fib_levels': self._fib_levels(date),
            'fib_support': None,  # Computed from fib_levels
            'fib_breakdown': None,  # Computed from fib_levels
            
            # Moving averages (low cost)
            'price_vs_sma50': self._price_vs_sma50_percent(date, price),
            'price_vs_sma200': self._price_vs_sma200_percent(date, price),
            
            # StochRSI (low cost - already cached in pack)
            'stoch_2w_k': self.pack.stoch_2w.get_k_at(date),
            'stoch_1w_k': self.pack.stoch_1w.get_k_at(date),
            
            # Meta
            'price': price,
            'date': date,
            'phase': self.phase,
            'days_in_phase': (date - self.phase_start_date).days if self.phase_start_date else 0
        }
        
        # Derive Fibonacci-based signals (reuse fib_levels calculation)
        if signals['fib_levels']:
            signals['fib_support'] = price_near_fib_support(price, signals['fib_levels'])
            signals['fib_breakdown'] = price_broke_fib_support(price, signals['fib_levels'])
        else:
            signals['fib_support'] = False
            signals['fib_breakdown'] = False
        
        # Cache for subsequent calls on same date
        self.signal_cache = signals
        self.cache_date = date
        
        return signals
```

---

## Conclusion

The ROUTER transformation represents a fundamental architectural evolution in the V13 trading engine. By consolidating all transition logic into an always-on orchestration layer, the system gains:

### Architectural Advantages

1. **Unified decision making** — One brain (ROUTER) makes all transition decisions based on comprehensive signal evaluation
2. **Always monitoring** — No more blind spots where signals are ignored between phases
3. **Signal consistency** — Same signal stack used for all decisions, eliminating scattered logic inconsistencies
4. **Cleaner code** — Centralized intelligence replaces scattered exit logic across 4 different methods

### Operational Improvements  

1. **Faster transitions** — Signal-driven routing vs arbitrary timeouts (30%+ speed improvement expected)
2. **Bottom detection** — New ROUTER→MARKUP path captures recovery signals missed by current DCA-only routing
3. **Dynamic tier gates** — Signal-based T2/T3 confirmation saves 3-7 days vs fixed timing
4. **Enhanced reliability** — Multiple signal confirmation reduces false positives

### Implementation Feasibility

- **5-7 day development cycle** with comprehensive testing framework
- **Phase 1 behavioral preservation** ensures zero regression risk 
- **Backward compatibility** maintained with V8 preserved for rollback
- **Performance optimized** through signal caching and centralized computation

**Brett's vision realized:** *"The router will have all the signals and indicators. It will constantly receive the realtime data and when conditions are met to transition, the router takes action."*

The ROUTER design establishes the foundation for V13's gate optimization roadmap by creating a unified, signal-driven architecture that can be enhanced with additional indicators and refined through systematic testing across an expanded coin universe.

This transformation addresses V13 Gap #3 (FLAT optimization) while enabling the broader gate optimization roadmap through a centralized, always-on intelligence layer that truly orchestrates the entire trading engine.

---

## 9. Strategy Plugin Architecture

### The Vision

ROUTER currently hardcodes 3 phases (DCA, MARKUP, MARKDOWN). But the architecture should support a **strategy library** where adding new strategies (ICT trader, scaling engine, mean reversion, breakout catcher) is just registering a new plugin. ROUTER doesn't change — it just has more options to evaluate and deploy.

### Strategy Interface

Every strategy implements a standard interface:

```python
class TradingStrategy:
    name: str                    # e.g., "markup_rider", "ict_trader"
    category: str                # "trend", "range", "momentum", "reversal"
    
    def evaluate_fit(self, signals: SignalPack) -> float:
        """Score 0-100 how well current conditions fit this strategy."""
        
    def enter(self, date, price, capital) -> List[Action]:
        """Open positions according to strategy logic."""
        
    def manage(self, date, price, signals) -> List[Action]:
        """Manage open positions (tier adds, trailing stops, etc.)."""
        
    def exit(self, date, price, reason) -> List[Action]:
        """Close all positions, return capital."""
        
    def get_state(self) -> dict:
        """Serialize strategy state for persistence."""
        
    def restore_state(self, state: dict):
        """Restore strategy state from persistence."""
```

### Architecture Flow

```
Signals → ROUTER → Strategy Selection → Execution
                ↑                            |
                └── Performance Feedback ─────┘
```

1. **Signal Layer**: Collects and normalizes all market signals (existing V13SignalPack + extensions)
2. **ROUTER Layer**: Evaluates signal conditions, scores strategy fitness, selects best strategy
3. **Strategy Layer**: Executes selected strategy (enter/manage/exit)
4. **Feedback Layer**: Tracks strategy performance per market condition, feeds back to ROUTER for learning

### Strategy Registry

```python
class StrategyRegistry:
    strategies: Dict[str, TradingStrategy]
    
    def register(self, strategy: TradingStrategy)
    def evaluate_all(self, signals) -> List[Tuple[str, float]]  # ranked by fit score
    def get_best(self, signals, min_score=60) -> Optional[TradingStrategy]
```

### Current Strategies (Layer 1)

Map existing phases to strategy plugins:

- **MarkupRider** — trend following with tiered entries (T1/T2/T3), top detection exit
- **MarkdownShorter** — bearish trend riding with tiered shorts, bottom detection exit  
- **DCAGrinder** — accumulation zone scalping, long-only, safety order grid

### Future Strategy Candidates (Layer 5+)

- **ScalingEngine** — momentum-based position building with volatility-adjusted sizing
- **ICTTrader** — order block detection, fair value gap entries, liquidity sweep plays
- **MeanReversion** — Bollinger/RSI fade for choppy/ranging markets
- **BreakoutCatcher** — volume-confirmed range break entries
- **CarryTrader** — funding rate arbitrage on perps

### ROUTER Selection Logic

On every evaluation tick:

1. Compute all signals (signal pack)
2. Ask each registered strategy for its `evaluate_fit()` score
3. If currently in a strategy: check if current strategy's fit has degraded below threshold OR another strategy scores significantly higher
4. If switching: call current strategy's `exit()`, then new strategy's `enter()`
5. If staying: call current strategy's `manage()`
6. Log decision reasoning (strategy scores, chosen strategy, confidence)

### Strategy Switching Rules

- **Minimum hold time**: 3 days in any strategy before switching allowed
- **Hysteresis**: Current strategy gets a +15 point bonus to prevent flip-flopping
- **Graceful handoff**: Current strategy's exit() can return "needs_time" to delay switch (e.g., waiting for TP)
- **Emergency override**: Failure detection bypasses hysteresis (e.g., 25% drawdown)

### Performance Tracking

```python
class StrategyPerformance:
    strategy_name: str
    entries: int
    exits: int
    win_rate: float
    avg_pnl_pct: float
    avg_duration_days: float
    conditions_at_entry: dict  # signal snapshot for learning
```

Over time, ROUTER can weight strategy selection by historical performance in similar conditions. This is the foundation for machine learning integration later.

### Migration Path

- **Layer 1 (now)**: Refactor DCA/MARKUP/MARKDOWN into strategy plugins with standard interface. ROUTER selects between them. Identical behavior to current engine.
- **Layer 2**: Add dynamic tier gates and ROUTER→MARKUP path within existing strategies.
- **Layer 3**: Add performance tracking and strategy scoring.
- **Layer 4**: Add new strategies (scaling engine, mean reversion).
- **Layer 5**: ML-assisted strategy selection based on historical performance data.

### Why This Matters Now

We're not building ICT or scaling strategies today. But designing the interface NOW means:

1. Adding new strategies later is just implementing the interface — no ROUTER changes needed
2. The refactoring work (Layer 1) naturally creates the strategy abstraction
3. Performance tracking from day one gives us data for future optimization
4. The strategy interface forces clean separation between signal evaluation and execution

### Key Design Constraint

The strategy plugin architecture must NOT slow down Layer 1 implementation. The current DCA/MARKUP/MARKDOWN logic maps cleanly to the strategy interface. We implement the interface, wrap existing logic in strategy classes, and ROUTER calls them through the standard interface. Zero behavior change, clean architecture.