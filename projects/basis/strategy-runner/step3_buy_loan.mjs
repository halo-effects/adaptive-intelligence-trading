/**
 * Custom Stacking Strategy - Step 3
 * Buy LOBSTER → take hub loan → get USDB back
 */
import { BasisClient } from 'basis-sdk';
import { formatUnits, parseUnits } from 'viem';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const envPath = path.join(__dirname, '..', 'skill-scaffold', '.env');
const env = fs.readFileSync(envPath, 'utf-8')
  .split('\n')
  .filter(line => line.trim() && !line.startsWith('#'))
  .reduce((acc, line) => {
    const [key, ...rest] = line.split('=');
    acc[key.trim()] = rest.join('=').trim().replace(/^["']|["']$/g, '');
    return acc;
  }, {});

const client = await BasisClient.create({ privateKey: env.BASIS_PRIVATE_KEY, apiKey: env.BASIS_API_KEY });
const wallet = client.walletClient.account.address;
const USDB = client.usdbAddress;
const MAINTOKEN = client.mainTokenAddress;
const LOBSTER = '0x5d87bb54E510CBDc1266972c75A3260dfE79A8F9';
const fmt = (v) => formatUnits(v, 18);

const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
async function getBalance(addr) {
  return client.publicClient.readContract({ address: addr, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
}
function log(msg) { console.log(`[${new Date().toISOString()}] ${msg}`); }

log('========== STEP 3: Buy LOBSTER → Loan → USDB ==========\n');

const usdbBefore = await getBalance(USDB);
log(`USDB balance: ${fmt(usdbBefore)}`);

// 3a. Check pool depth / price impact before buying
const buyAmount = parseUnits("100", 18);
const preview = await client.trading.getAmountsOut(buyAmount, [USDB, MAINTOKEN, LOBSTER]);
log(`Preview: ${fmt(buyAmount)} USDB → ${preview} LOBSTER (3-hop via STASIS)`);

// Also check floor price to know what the loan will give us
const floorPrice = await client.factory.getFloorPrice(LOBSTER);
log(`LOBSTER floor price: ${fmt(BigInt(floorPrice))} USDB`);

// Buy with 3% slippage
log(`\n--- 3a: Buying LOBSTER with 100 USDB ---`);
const expectedOut = BigInt(preview);
const minOut = expectedOut * 97n / 100n;
const buyTx = await client.trading.buy(LOBSTER, buyAmount, minOut);
log(`  ✓ Bought: ${buyTx.hash || buyTx}`);

const lobsterBal = await getBalance(LOBSTER);
log(`  LOBSTER balance: ${fmt(lobsterBal)}`);

// 3b. Take hub loan — Floor+ LTV is at floor price
// takeLoan(ecosystem, collateral, amount, days)
log(`\n--- 3b: Taking hub loan against LOBSTER ---`);
const loanTx = await client.loans.takeLoan(MAINTOKEN, LOBSTER, lobsterBal, 10n);
log(`  ✓ Loan taken: ${loanTx.hash || loanTx}`);

// Find the hubId
const loanCount = await client.loans.getUserLoanCount(wallet);
log(`  Hub loan count: ${loanCount}`);
const hubId = loanCount;
const details = await client.loans.getUserLoanDetails(wallet, hubId);
log(`  Loan details:`, JSON.stringify(details, (k,v) => typeof v === 'bigint' ? v.toString() : v));

const usdbAfter = await getBalance(USDB);
log(`\n--- Step 3 Complete ---`);
log(`USDB before: ${fmt(usdbBefore)}`);
log(`USDB after:  ${fmt(usdbAfter)}`);
log(`USDB change: ${fmt(usdbAfter - usdbBefore)}`);
log(`LOBSTER in wallet: ${fmt(await getBalance(LOBSTER))}`);
log(`Hub ID: ${hubId}`);
