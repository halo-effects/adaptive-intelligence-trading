/**
 * Strategy 2: "The Yield Maximizer" — 3 stacks, all yielding positions
 * 
 * Path A: Buy STASIS → wrap wSTASIS → lock → borrow USDB
 * Path C: Buy FEDCUT (Predict+) → borrow USDB against it
 * Path B: Buy LVTHN (Floor+) → borrow USDB against it
 * 
 * Following: Module 02, 04, 05, 06, 12, 18
 */

import { BasisClient } from 'basis-sdk';
import { parseUnits, formatUnits } from 'viem';
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
const FEDCUT = '0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06';
const LVTHN = '0xFf84209eBCCAc7328070E0011e973451c4a045F9';

const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];

async function getBalance(tokenAddr) {
  const bal = await client.publicClient.readContract({ address: tokenAddr, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
  return bal;
}

function fmt(wei) { return formatUnits(wei, 18); }
function log(msg) { console.log(`[${new Date().toISOString()}] ${msg}`); }

// ============================================================
// PRE-FLIGHT: Check current state
// ============================================================
log('========== STRATEGY 2: THE YIELD MAXIMIZER ==========');
log('');

log('--- Pre-flight checks ---');
const usdbBalance = await getBalance(USDB);
log(`USDB balance: ${fmt(usdbBalance)}`);

const stasisBalance = await getBalance(MAINTOKEN);
log(`STASIS balance: ${fmt(stasisBalance)}`);

// Check existing staking position (Module 06: getUserStakeDetails)
const stakeDetails = await client.staking.getUserStakeDetails(wallet);
const liquidShares = stakeDetails[0];
const lockedShares = stakeDetails[1];
const totalShares = stakeDetails[2];
const totalAssetValue = stakeDetails[3];
log(`wSTASIS liquid: ${fmt(liquidShares)}, locked: ${fmt(lockedShares)}, total: ${fmt(totalShares)}`);
log(`wSTASIS total STASIS value: ${fmt(totalAssetValue)}`);

// Check available borrow capacity (Module 06: getAvailableStasis)
const availableStasis = await client.staking.getAvailableStasis(wallet);
log(`Available STASIS for new borrowing: ${fmt(availableStasis)}`);

// Decide allocation: use ~200 USDB per stack (conservative with 650 total)
// Keep ~50 USDB reserve for loan extensions
const STACK_AMOUNT = parseUnits('200', 18);
const MIN_RESERVE = parseUnits('50', 18);

if (usdbBalance < STACK_AMOUNT + MIN_RESERVE) {
  log(`ERROR: Need at least ${fmt(STACK_AMOUNT + MIN_RESERVE)} USDB, have ${fmt(usdbBalance)}`);
  process.exit(1);
}

log(`\nAllocation: ${fmt(STACK_AMOUNT)} USDB per stack, ${fmt(MIN_RESERVE)} reserve`);

// ============================================================
// PATH A: Buy STASIS → wrap wSTASIS → lock → borrow USDB
// ============================================================
log('\n========== PATH A: STASIS → wSTASIS → Lock → Borrow ==========');

// Step A1: Preview buy STASIS (Module 04: getAmountsOut)
log('A1: Previewing STASIS buy...');
const expectedStasis = await client.trading.getAmountsOut(STACK_AMOUNT, [USDB, MAINTOKEN]);
const stasisMinOut = expectedStasis * 95n / 100n; // 5% slippage tolerance
log(`  Expected STASIS out: ${fmt(expectedStasis)}, minOut (5%): ${fmt(stasisMinOut)}`);

// Step A2: Buy STASIS (Module 04: buy)
log('A2: Buying STASIS...');
const buyStasisTx = await client.trading.buy(MAINTOKEN, STACK_AMOUNT, stasisMinOut);
log(`  ✓ Buy tx: ${buyStasisTx.hash || buyStasisTx}`);

// Check STASIS balance after buy
const stasisAfterBuy = await getBalance(MAINTOKEN);
log(`  STASIS balance after buy: ${fmt(stasisAfterBuy)}`);

// Step A3: Wrap STASIS → wSTASIS (Module 06: staking.buy)
log('A3: Wrapping STASIS → wSTASIS...');
const wrapTx = await client.staking.buy(stasisAfterBuy);
log(`  ✓ Wrap tx: ${wrapTx.hash || wrapTx}`);

// Step A4: Lock wSTASIS as collateral (Module 06: lock)
// CRITICAL: lock() takes wSTASIS shares, use convertToShares()
log('A4: Locking wSTASIS as collateral...');
const newShares = await client.staking.convertToShares(stasisAfterBuy);
log(`  Shares to lock: ${fmt(newShares)}`);
const lockTx = await client.staking.lock(newShares);
log(`  ✓ Lock tx: ${lockTx.hash || lockTx}`);

// Step A5: Borrow USDB against locked wSTASIS (Module 06: borrow / addToLoan)
// Check if there's already an active vault loan (one loan per wallet rule)
log('A5: Borrowing USDB against wSTASIS...');
const updatedStakeDetails = await client.staking.getUserStakeDetails(wallet);
const updatedAvailable = await client.staking.getAvailableStasis(wallet);
log(`  Available to borrow (STASIS): ${fmt(updatedAvailable)}`);

// Per Module 06: one loan per wallet. Try borrow first, if it reverts with
// "Position active. Use increaseLoan" then use addToLoan instead.
let borrowTx;
try {
  borrowTx = await client.staking.borrow(updatedAvailable, 10n);
  log(`  ✓ New vault loan: ${borrowTx.hash || borrowTx}`);
} catch (e) {
  if (e.message?.includes('Position active') || e.message?.includes('increaseLoan')) {
    log('  Active vault loan exists, using addToLoan...');
    borrowTx = await client.staking.addToLoan(updatedAvailable);
    log(`  ✓ Added to existing loan: ${borrowTx.hash || borrowTx}`);
  } else {
    throw e;
  }
}

const usdbAfterPathA = await getBalance(USDB);
log(`  USDB after Path A: ${fmt(usdbAfterPathA)}`);

// ============================================================
// PATH C: Buy FEDCUT (Predict+) → borrow USDB against it
// ============================================================
log('\n========== PATH C: FEDCUT (Predict+) → Borrow ==========');

// Use ~200 USDB for this stack too (or whatever we got back)
const pathCAmount = usdbAfterPathA > STACK_AMOUNT ? STACK_AMOUNT : usdbAfterPathA - MIN_RESERVE;
if (pathCAmount <= 0n) {
  log('ERROR: Not enough USDB for Path C');
  process.exit(1);
}

// Step C1: Preview buy FEDCUT (Module 04: getAmountsOut — 3-hop path)
log('C1: Previewing FEDCUT buy...');
const expectedFedcut = await client.trading.getAmountsOut(pathCAmount, [USDB, MAINTOKEN, FEDCUT]);
const fedcutMinOut = expectedFedcut * 95n / 100n;
log(`  Input: ${fmt(pathCAmount)} USDB`);
log(`  Expected FEDCUT out: ${fmt(expectedFedcut)}, minOut (5%): ${fmt(fedcutMinOut)}`);

// Step C2: Buy FEDCUT (Module 04: buy)
log('C2: Buying FEDCUT...');
const buyFedcutTx = await client.trading.buy(FEDCUT, pathCAmount, fedcutMinOut);
log(`  ✓ Buy tx: ${buyFedcutTx.hash || buyFedcutTx}`);

// Check FEDCUT balance
const fedcutBalance = await getBalance(FEDCUT);
log(`  FEDCUT balance: ${fmt(fedcutBalance)}`);

// Step C3: Borrow against FEDCUT (Module 05: loans.takeLoan)
// Predict+ is Stable+ subtype → 100% LTV at spot
log('C3: Borrowing USDB against FEDCUT...');
const loanFedcutTx = await client.loans.takeLoan(MAINTOKEN, FEDCUT, fedcutBalance, 10n);
log(`  ✓ Loan tx: ${loanFedcutTx.hash || loanFedcutTx}`);

const usdbAfterPathC = await getBalance(USDB);
log(`  USDB after Path C: ${fmt(usdbAfterPathC)}`);

// ============================================================
// PATH B: Buy LVTHN (Floor+) → borrow USDB against it
// ============================================================
log('\n========== PATH B: LVTHN (Floor+) → Borrow ==========');

// Use remaining USDB minus reserve
const pathBAmount = usdbAfterPathC - MIN_RESERVE;
if (pathBAmount <= 0n) {
  log('ERROR: Not enough USDB for Path B');
  process.exit(1);
}

// Step B1: Preview buy LVTHN (Module 04: getAmountsOut — 3-hop)
log('B1: Previewing LVTHN buy...');
const expectedLvthn = await client.trading.getAmountsOut(pathBAmount, [USDB, MAINTOKEN, LVTHN]);
const lvthnMinOut = expectedLvthn * 95n / 100n;
log(`  Input: ${fmt(pathBAmount)} USDB`);
log(`  Expected LVTHN out: ${fmt(expectedLvthn)}, minOut (5%): ${fmt(lvthnMinOut)}`);

// Step B2: Buy LVTHN (Module 04: buy)
log('B2: Buying LVTHN...');
const buyLvthnTx = await client.trading.buy(LVTHN, pathBAmount, lvthnMinOut);
log(`  ✓ Buy tx: ${buyLvthnTx.hash || buyLvthnTx}`);

// Check LVTHN balance
const lvthnBalance = await getBalance(LVTHN);
log(`  LVTHN balance: ${fmt(lvthnBalance)}`);

// Step B3: Borrow against LVTHN (Module 05: loans.takeLoan)
// Floor+ → LTV at floor price, not spot
log('B3: Borrowing USDB against LVTHN...');
const loanLvthnTx = await client.loans.takeLoan(MAINTOKEN, LVTHN, lvthnBalance, 10n);
log(`  ✓ Loan tx: ${loanLvthnTx.hash || loanLvthnTx}`);

const usdbAfterPathB = await getBalance(USDB);
log(`  USDB after Path B: ${fmt(usdbAfterPathB)}`);

// ============================================================
// FINAL STATUS
// ============================================================
log('\n========== FINAL STATUS ==========');
const finalUsdb = await getBalance(USDB);
const finalStasis = await getBalance(MAINTOKEN);
const finalStake = await client.staking.getUserStakeDetails(wallet);
const finalFedcut = await getBalance(FEDCUT);
const finalLvthn = await getBalance(LVTHN);

log(`USDB reserve: ${fmt(finalUsdb)}`);
log(`STASIS (loose): ${fmt(finalStasis)}`);
log(`wSTASIS locked: ${fmt(finalStake[1])}`);
log(`wSTASIS total STASIS value: ${fmt(finalStake[3])}`);
log(`FEDCUT held: ${fmt(finalFedcut)}`);
log(`LVTHN held: ${fmt(finalLvthn)}`);

// Check loans
const stasisLoanCount = await client.loans.getUserLoanCount(wallet, MAINTOKEN);
log(`\nActive loans: ${stasisLoanCount}`);

log('\n========== STRATEGY 2 COMPLETE ==========');
log('Positions:');
log('  1. wSTASIS (Path A) — earning vault yield from all platform fees');
log('  2. FEDCUT (Path C) — Predict+ exposure, price can only go up');
log('  3. LVTHN (Path B) — Floor+ with rising floor protection');
log('Categories hit: Trading, Staking, Lending, Predictions = 4 (diversity multiplier)');
log(`USDB reserve for extensions: ${fmt(finalUsdb)}`);
