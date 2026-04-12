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
const fmt = (v) => formatUnits(v, 18);

const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
async function getBalance(addr) {
  return client.publicClient.readContract({ address: addr, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
}

console.log('=== Before ===');
console.log(`USDB: ${fmt(await getBalance(client.usdbAddress))}`);

// Step 1: Read positions with correct signature — getLeverageCount(wallet) 
const count = await client.trading.getLeverageCount(wallet);
console.log(`\nLeverage positions: ${count}`);

const positions = [];
for (let i = 0n; i < count; i++) {
  const pos = await client.trading.getLeveragePosition(wallet, i);
  console.log(`\nPosition ${i}:`, JSON.stringify(pos, (k,v) => typeof v === 'bigint' ? v.toString() : v, 2));
  positions.push({ index: i, data: pos });
}

// Step 2: Close any active positions
for (const { index, data } of positions) {
  // Check if active (look for non-zero data)
  const isActive = data.active ?? data[8] ?? true; // try named or positional
  console.log(`\nPosition ${index} active: ${isActive}`);
  
  if (isActive || true) { // try regardless since we're debugging
    console.log(`Closing position ${index} via partialLoanSell...`);
    try {
      const tx = await client.trading.partialLoanSell(index, 100n, true, 0n);
      console.log(`✓ Closed: ${tx.hash || tx}`);
    } catch (e) {
      console.log(`Error: ${e.message.substring(0, 250)}`);
    }
  }
}

// Final state
console.log('\n=== After ===');
console.log(`USDB: ${fmt(await getBalance(client.usdbAddress))}`);

const loans = await client.api.getLoans();
const active = loans.data?.filter(l => l.active) || [];
console.log(`Active loans: ${active.length}`);
for (const l of active) {
  console.log(`  ${l.source} | ${l.token.substring(0,10)}... | repay=${fmt(BigInt(l.fullAmount))}`);
}
