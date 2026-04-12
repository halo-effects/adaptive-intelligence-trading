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

const loanHubAddr = client.loans.loanHubAddress;
const loanCountAbi = [{ name: 'userLoanCount', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: '', type: 'address' }], stateMutability: 'view' }];
const totalHubLoans = await client.publicClient.readContract({ address: loanHubAddr, abi: loanCountAbi, functionName: 'userLoanCount', args: [wallet] });

console.log(`Total hub loans ever: ${totalHubLoans}`);
for (let i = 1n; i <= totalHubLoans; i++) {
  try {
    const loan = await client.loans.getUserLoanDetails(wallet, i);
    // Print all fields with bigint conversion
    console.log(`\nHub ${i}:`, JSON.stringify(loan, (k, v) => typeof v === 'bigint' ? v.toString() : v));
    // Key fields
    console.log(`  collateralToken: ${loan[3]}`);
    console.log(`  collateral: ${fmt(loan[5])}`);
    console.log(`  borrowed: ${fmt(loan[8])}`);
    console.log(`  fullAmount (repay): ${fmt(loan[7])}`);
    console.log(`  active: ${loan[12]}`);
    console.log(`  liquidationTime: ${loan[9]} (${new Date(Number(loan[9]) * 1000).toISOString()})`);
  } catch (e) {
    console.log(`Hub ${i}: ${e.message.substring(0, 100)}`);
  }
}

// Also check via API
console.log('\n=== API Loans ===');
try {
  const apiLoans = await client.api.getLoans();
  console.log(JSON.stringify(apiLoans, null, 2));
} catch (e) {
  console.log('API loans error:', e.message.substring(0, 100));
}
