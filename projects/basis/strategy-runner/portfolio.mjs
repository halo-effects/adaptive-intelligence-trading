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

// Module 10: getMyProfile, getMyStats, getMyProjects
console.log('=== Profile ===');
const profile = await client.api.getMyProfile();
console.log(JSON.stringify(profile, null, 2));

console.log('\n=== Stats ===');
try {
  const stats = await client.api.getMyStats();
  console.log(JSON.stringify(stats, null, 2));
} catch (e) { console.log(`Error: ${e.message.substring(0, 100)}`); }

console.log('\n=== My Projects ===');
try {
  const projects = await client.api.getMyProjects();
  console.log(JSON.stringify(projects, null, 2));
} catch (e) { console.log(`Error: ${e.message.substring(0, 100)}`); }

console.log('\n=== Loans ===');
const loans = await client.api.getLoans();
console.log(JSON.stringify(loans, null, 2));

console.log('\n=== Wallet Transactions (recent) ===');
try {
  const txs = await client.api.getWalletTransactions({ limit: 10 });
  console.log(JSON.stringify(txs, null, 2));
} catch (e) { console.log(`Error: ${e.message.substring(0, 100)}`); }
