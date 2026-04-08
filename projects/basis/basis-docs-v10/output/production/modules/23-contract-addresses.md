# Contract Addresses & Token Decimals

**What this covers:** All BSC Mainnet contract addresses used by the SDK, and the token decimal reference for raw amount calculations.

**Related sections:** → See: [03-getting-started.md](03-getting-started.md) for SDK configuration options · → See: [10-atomic-skills.md](10-atomic-skills.md) for methods that use these addresses

---

## Contract Addresses

The canonical contract addresses are published at [`https://launchonbasis.com/contracts.json`](https://launchonbasis.com/contracts.json). The SDK fetches this on startup and warns if its hardcoded defaults are stale. All addresses are overridable via constructor options (see [03-getting-started.md](03-getting-started.md)).

Default BSC Mainnet contract addresses used by the SDK:

| Contract | Address |
|----------|---------|
| Factory (ATokenFactory) | `0xB6BA282f29A7C67059f4E9D0898eE58f5C79960D` |
| Swap (SWAP) | `0x9F9cF98F68bDbCbC5cf4c6402D53cEE1D180715f` |
| MarketTrading (PREDICTION) | `0x396216fc9d2c220afD227B59097cf97B7dEaCb57` |
| LoanHub (LOANS) | `0xFe19644d52fD0014EBa40c6A8F4Bfee4Ce3B2449` |
| Vesting (VESTING) | `0xedd987c7723B9634b0Aa6161258FED3e89F9094C` |
| Staking (AStasisVault) | `0x1FE7189270fb93c32a1fEfA71d1795c05C41cb33` |
| Resolver (AMarketResolver) | `0xB5FFCCB422531Cf462ec430170f85d8dD3dC3f57` |
| Private Markets | `0x28675A82ee3c2e6d2C85887Ea587FbDD3E3C86EE` |
| Market Reader | `0xF406cA6403c57Ad04c8E13F4ae87b3732daa087d` |
| Leverage Simulator | `0xeffb140d821c5B20EFc66346Cf414EeAC8A8FDB2` |
| Taxes (ATaxes) | `0x4501d1279273c44dA483842ED17b5451e7d3A601` |
| USDB | `0x42bcF288e51345c6070F37f30332ee5090fC36BF` |
| STASIS (MAINTOKEN) | `0x3067ce754a36d0a2A1b215C4C00315d9Da49EF15` |
| Floor | `0x359dE659F0242352dD7F021c2EcB370284D95F45` |
| ERC-8004 Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |

All addresses are overridable via constructor options.

> **Naming note:** MAINTOKEN is the contract/SDK variable name for the STASIS token. In code: `client.mainTokenAddress` (JS) / `client.main_token_address` (Python). In docs: STASIS.

---

## Token Decimals

When working with raw amounts (e.g., reading from contract returns or constructing manual transactions), be aware of decimal differences:

| Token | Decimals | Example |
|-------|----------|---------|
| USDB | 18 | `5000000000000000000` = 5 USDB |
| STASIS (MAINTOKEN) | 18 | `1000000000000000000` = 1 STASIS |
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
