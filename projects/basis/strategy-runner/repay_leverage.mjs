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

// API says: loanId: 1, hubId: null, fullAmount: 64.11 USDB
// Try repayLoan with loanId=1
console.log('Attempting repayLoan(1)...');
try {
  const tx = await client.loans.repayLoan(1n);
  console.log(`✓ Repaid: ${tx.hash || tx}`);
} catch (e) {
  console.log(`Error: ${e.message.substring(0, 200)}`);
}

// Try repayLoan with other possible IDs
for (const id of [3n, 4n, 5n]) {
  console.log(`\nAttempting repayLoan(${id})...`);
  try {
    const tx = await client.loans.repayLoan(id);
    console.log(`✓ Repaid: ${tx.hash || tx}`);
    break;
  } catch (e) {
    console.log(`Error: ${e.message.substring(0, 150)}`);
  }
}

// Check result
const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
const usdb = await client.publicClient.readContract({ address: client.usdbAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
console.log(`\nUSDB: ${fmt(usdb)}`);

const loans = await client.api.getLoans();
const active = loans.data?.filter(l => l.active) || [];
console.log(`Active loans: ${active.length}`);
