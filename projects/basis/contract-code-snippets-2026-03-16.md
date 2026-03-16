# Contract Code Snippets — From Alex, 2026-03-16

_Raw contract code shared by Alex in Telegram. Preserved verbatim for reference._

## MAIN_TOKEN / STASIS — Loan Fee Parameters

```solidity
uint256 public dynamicFeePercentage = 5; // 5 = 0.005% PER DAY
uint256 public staticFeePercentage = 200; // 200 = 2.0%
```

## ATaxes — Tax Rates & Distribution

```solidity
uint256 public _taxRateXether = 50;       // STASIS: 0.50%
uint256 public _taxRateStable = 50;       // Stable+: 0.50% (+ surge)
uint256 public _taxRateDefault = 150;     // Floor+: 1.50% (+ surge)
uint256 public _taxRatePrediction = 150;  // Predict+: 1.50%
uint256 public injectRate = 16;           // 16% of fee → wSTASIS Vault
uint256 public devRate = 20;              // 20% of fee → Creator
uint256 public presaleRate = 4;           // 4% of fee → Bonding phase buyers
```

## ATaxes — getTaxRate()

```solidity
function getTaxRate(IERC20 token, address user) public view returns (uint256) {
    if (isWhitelisted[user]) {
        return 0;
    }

    if (address(token) == address(MAINTOKEN)) {
        return _taxRateXether;
    }

    address dev = token.DEV();
    if(isPrediction[dev]){
        return _taxRatePrediction;
    }

    uint256 surge = getCurrentSurgeTax(address(token));
    if (token.hybridMultiplier() == 100) {
        return _taxRateStable + surge;
    }
    return _taxRateDefault + surge;
}
```

## ATaxes — Surge Tax

```solidity
function getCurrentSurgeTax(address token) public view returns (uint256) {
    if (!isSurgeActive[token] || block.timestamp >= surgeStartTime[token] + surgeDuration[token]) {
        return 0;
    }
    uint256 elapsed = block.timestamp - surgeStartTime[token];
    uint256 totalDrop = surgeStartRate[token] - surgeEndRate[token];
    uint256 currentDrop = (elapsed * totalDrop) / surgeDuration[token];
    return surgeStartRate[token] - currentDrop;
}

function startSurgeTax(uint256 startRate, uint256 endRate, uint256 duration, address token) external {
    IERC20 TOKEN = IERC20(token);
    require(TOKEN.DEV() == msg.sender, "only dev");
    uint256 multiplier = TOKEN.hybridMultiplier();
    require(multiplier >= 1 && (multiplier <= 90 || multiplier == 100), "invalid multiplier");

    uint256 maxRate;
    if (multiplier == 100) {
        maxRate = 50;
    } else {
        uint256 decrement = (multiplier - 1) * 1400 / 89;  // Base decrement
        uint256 rawMax = 1500 - decrement;
        uint256 step = 50;

        maxRate = (rawMax / step) * step;
        maxRate = maxRate < 100 ? 100 : maxRate;
    }

    require(startRate <= maxRate && startRate >= 10, "invalid start rate");
    require(endRate <= startRate && endRate >= 0, "invalid end rate");
    require(duration >= ONE_HOUR, "duration too short");

    _pruneHistory(token);
    uint256 currentUsed = _calculateUsed(token);
    require(currentUsed + duration <= SEVEN_DAYS, "quota exceeded");
    require(!isSurgeActive[token], "surge already active");

    surgeStartTime[token] = block.timestamp;
    surgeDuration[token] = duration;
    surgeStartRate[token] = startRate;
    surgeEndRate[token] = endRate;
    isSurgeActive[token] = true;
    surgeHistory[token].push(Surge({start: block.timestamp, dur: duration}));

    emit SurgeStarted(token, startRate, endRate, duration, block.timestamp);
}
```

## SDK Status (2026-03-16)
- ✅ Complete — all views and functions tested
- ✅ Local dApp built for manual testing
- ❌ NOT yet on npm/PyPI — docs needed first
- ⚠️ Contracts need redeployment with "live" parameters (current ones are test-optimized: lower LP, sped-up prediction resolvements)
