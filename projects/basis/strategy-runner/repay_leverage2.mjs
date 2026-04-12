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

// Module 18 says: repayLoan(tokenAddress, loanIndex)
// The leverage loan is on token 0xbb8c... with loanId/loanIndex 1
const LEV_TOKEN = '0xbb8c70bdc0fe13b25753e81af676c23ddcfd6e28';

console.log('=== Before ===');
const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
const usdbBefore = await client.publicClient.readContract({ address: client.usdbAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
console.log(`USDB: ${fmt(usdbBefore)}`);

// Try repayLoan with tokenAddress (not hubId)
console.log(`\nAttempting repayLoan('${LEV_TOKEN}', 1)...`);
try {
  const tx = await client.loans.repayLoan(LEV_TOKEN, 1);
  console.log(`✓ Repaid: ${tx.hash || tx}`);
} catch (e) {
  console.log(`Error: ${e.message.substring(0, 250)}`);
  
  // Try loanIndex 0 instead
  console.log(`\nAttempting repayLoan('${LEV_TOKEN}', 0)...`);
  try {
    const tx = await client.loans.repayLoan(LEV_TOKEN, 0);
    console.log(`✓ Repaid: ${tx.hash || tx}`);
  } catch (e2) {
    console.log(`Error: ${e2.message.substring(0, 200)}`);
  }
}

// Check result
console.log('\n=== After ===');
const usdbAfter = await client.publicClient.readContract({ address: client.usdbAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
console.log(`USDB: ${fmt(usdbAfter)}`);

const loans = await client.api.getLoans();
const active = loans.data?.filter(l => l.active) || [];
console.log(`Active loans: ${active.length}`);
