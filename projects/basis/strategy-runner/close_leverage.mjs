/**
 * Close the old leverage position on 0xbb8c...
 * Per Module 04 Section 3d: getLeverageCount(wallet, tokenAddress) → positionId
 * Then hubPartialLoanSell(positionId, 100, true, 0)
 */
import { BasisClient } from 'basis-sdk';
import { formatUnits } from 'viem';
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
const MAINTOKEN = client.mainTokenAddress;
const USDB = client.usdbAddress;
const LEV_TOKEN = '0xbb8c70bdc0fe13b25753e81af676c23ddcfd6e28';
const fmt = (v) => formatUnits(v, 18);

const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
async function getBalance(addr) {
  return client.publicClient.readContract({ address: addr, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
}

console.log('=== Pre-state ===');
console.log(`USDB: ${fmt(await getBalance(USDB))}`);

// The leverage was created with a path that went through MAINTOKEN
// Per Module 04: getLeverageCount(wallet, tokenAddress) where tokenAddress
// is the TOKEN being leveraged (the collateral token)
// But the docs example uses client.mainTokenAddress... let me check both

console.log('\n=== Leverage positions ===');

// Check on MAINTOKEN (STASIS)
const levOnMain = await client.trading.getLeverageCount(wallet, MAINTOKEN);
console.log(`Leverage on MAINTOKEN: ${levOnMain}`);
if (levOnMain > 0n) {
  for (let i = 1n; i <= levOnMain; i++) {
    const pos = await client.trading.getLeveragePosition(wallet, MAINTOKEN, i);
    console.log(`  Position ${i}:`, JSON.stringify(pos, (k,v) => typeof v === 'bigint' ? v.toString() : v));
  }
}

// Check on the leverage token itself
const levOnToken = await client.trading.getLeverageCount(wallet, LEV_TOKEN);
console.log(`\nLeverage on ${LEV_TOKEN.substring(0,10)}...: ${levOnToken}`);
if (levOnToken > 0n) {
  for (let i = 1n; i <= levOnToken; i++) {
    const pos = await client.trading.getLeveragePosition(wallet, LEV_TOKEN, i);
    console.log(`  Position ${i}:`, JSON.stringify(pos, (k,v) => typeof v === 'bigint' ? v.toString() : v));
  }
}

// Try to get token info
console.log('\n=== Token info ===');
try {
  const tokenInfo = await client.api.getToken(LEV_TOKEN);
  console.log(JSON.stringify(tokenInfo?.data, null, 2));
} catch (e) {
  console.log(`Token info error: ${e.message.substring(0, 100)}`);
}

// The API showed the leverage loan with loanId=1 on this token
// Per the contract ABI, hubPartialLoanSell takes (hubId, percentage, isLeverage, minOut)
// For leverage, the ID should come from getLeverageCount on the collateral token
// But getLeverageCount(wallet, MAINTOKEN) = 1 and that might be this position

// Let's try closing it with the MAINTOKEN leverage position ID
if (levOnMain > 0n) {
  console.log('\n=== Attempting to close leverage position 1 on MAINTOKEN ===');
  try {
    // Per Module 04: hubPartialLoanSell(positionId, percentage, isLeverage=true, minOut)
    const tx = await client.loans.hubPartialLoanSell(1n, 100n, true, 0n);
    console.log(`✓ Closed: ${tx.hash || tx}`);
  } catch (e) {
    console.log(`Error: ${e.message.substring(0, 200)}`);
    
    // Maybe the position ID is different. The API says loanId=1 for this leverage
    // Let's check what getLeveragePosition returns to understand the mapping
    console.log('\nPosition details from getLeveragePosition(wallet, MAINTOKEN, 1):');
    const pos = await client.trading.getLeveragePosition(wallet, MAINTOKEN, 1n);
    console.log(JSON.stringify(pos, (k,v) => typeof v === 'bigint' ? v.toString() : v, 2));
  }
}

console.log('\n=== Post-state ===');
console.log(`USDB: ${fmt(await getBalance(USDB))}`);

// Check remaining loans
const apiLoans = await client.api.getLoans();
const active = apiLoans.data?.filter(l => l.active) || [];
console.log(`Active loans: ${active.length}`);
for (const l of active) {
  console.log(`  ${l.source} | token=${l.token} | repay=${fmt(BigInt(l.fullAmount))}`);
}
