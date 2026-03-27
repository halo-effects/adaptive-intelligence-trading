# Contract Addresses & Token Decimals

**What this covers:** All BSC Mainnet contract addresses used by the SDK, and the token decimal reference for raw amount calculations.

**Related sections:** â†’ See: [09-getting-started.md](09-getting-started.md) for SDK configuration options Â· â†’ See: [04-atomic-skills.md](04-atomic-skills.md) for methods that use these addresses

---

## Contract Addresses

Default BSC Mainnet contract addresses used by the SDK:

| Contract | Address |
|----------|---------|
| Factory (ATokenFactory) | `0xd80850a3b712E6B9dB4d3e487c76b7c1F904E273` |
| Swap (SWAP) | `0xa2483dd5d22D1A8a01473878f247fEC8dC952f1e` |
| MarketTrading (PREDICTION) | `0x69e4b11346f928f29Affe6B52a8e3Ebd115DE7a6` |
| LoanHub (LOANS) | `0x504AeDa510D4cb5Fe6E29D000Dfc377f3f50cC30` |
| Vesting (VESTING) | `0x82D1a54fd9671Cd4fE8774f0f85A0CB8A96dee3b` |
| Staking (AStasisVault) | `0x8E2C5267f2BA1A142A88a333C075E21719E330aC` |
| Resolver (AMarketResolver) | `0x1AB2C2551429Bd4f9a5D8c781BEb5BC5497a42bd` |
| Private Markets | `0x4eCDD0A082b3f523c31F61eC8bEfF69A8182C0aD` |
| Market Reader | `0xC8652aF90B1C2C9012ADe56B58EfA9572122d342` |
| Leverage Simulator | `0x0030d46D3ba98287e7D62482c14E4395FbF52904` |
| Taxes (ATaxes) | `0x3CE0381C6515b7771a6E47d99abf1e42054121CD` |
| USDB | `0x217B82e4bAc4E4647B1F189F33554229Ce27c51A` |
| MAINTOKEN (STASIS/STASIS) | `0xE4b1ed74C77984EbFf1CE871E7F7c9414e5dd73b` |
| ERC-8004 Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |

All addresses are overridable via constructor options.

---

## Token Decimals

When working with raw amounts (e.g., reading from contract returns or constructing manual transactions), be aware of decimal differences:

| Token | Decimals | Example |
|-------|----------|---------|
| USDB | 18 | `5000000000000000000` = 5 USDB |
| MAINTOKEN (STASIS/STASIS) | 18 | `1000000000000000000` = 1 STASIS |
| Factory tokens | 18 | `1000000000000000000` = 1 token |

> **Note:** All tokens in the Basis ecosystem use 18 decimals, including USDB.

All SDK methods expect raw integer amounts in the token's smallest unit. Use `parseUnits` / `formatUnits` (JS: from `viem`) or simple multiplication (Python: `amount * 10**decimals`) to convert between human-readable and raw values. The only exception is `sellPercentage`, which takes a percentage (1-100) and reads the balance automatically.

**JavaScript:**

```js
import { parseUnits, formatUnits } from "viem";

const usdbRaw = parseUnits("5", 18);       // 5000000000000000000n
const tokenRaw = parseUnits("100", 18);    // 100000000000000000000n

const humanUsdb = formatUnits(5000000000000000000n, 18);  // "5"
const humanToken = formatUnits(100000000000000000000n, 18); // "100"
```

**Python:**

```python
from web3 import Web3

usdb_raw = Web3.to_wei(5, "ether")    # 5000000000000000000 (all tokens are 18 decimals)
token_raw = Web3.to_wei(100, "ether") # 100000000000000000000

# Or simply:
usdb_raw = 5 * 10**18
token_raw = 100 * 10**18

human_usdb = Web3.from_wei(5000000000000000000, "ether")    # 5
human_token = Web3.from_wei(100000000000000000000, "ether") # 100
```


---
