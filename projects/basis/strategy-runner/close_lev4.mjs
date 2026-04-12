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

// Check positions 0, 1, 2
for (const i of [0n, 1n, 2n]) {
  try {
    const pos = await client.trading.getLeveragePosition(wallet, i);
    console.log(`\nPosition ${i}:`, JSON.stringify(pos, (k,v) => typeof v === 'bigint' ? v.toString() : v));
  } catch (e) {
    console.log(`\nPosition ${i}: ${e.message.substring(0, 100)}`);
  }
}

// Try closing position 1
console.log('\n--- Closing position 1 ---');
try {
  const tx = await client.trading.partialLoanSell(1n, 100n, true, 0n);
  console.log(`✓ Closed: ${tx.hash || tx}`);
} catch (e) {
  console.log(`Error: ${e.message.substring(0, 250)}`);
}

console.log('\n=== After ===');
console.log(`USDB: ${fmt(await getBalance(client.usdbAddress))}`);

const loans = await client.api.getLoans();
const active = loans.data?.filter(l => l.active) || [];
console.log(`Active loans: ${active.length}`);
