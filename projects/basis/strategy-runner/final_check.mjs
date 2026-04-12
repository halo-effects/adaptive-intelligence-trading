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

const fmt = (v) => formatUnits(v, 18);

// Balances
const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
const usdb = await client.publicClient.readContract({ address: client.usdbAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
console.log(`USDB: ${fmt(usdb)}`);

// Staking
const stake = await client.staking.getUserStakeDetails(wallet);
console.log(`\nwSTASIS liquid: ${fmt(stake[0])}`);
console.log(`wSTASIS locked: ${fmt(stake[1])}`);
console.log(`wSTASIS total: ${fmt(stake[2])}`);
console.log(`STASIS value: ${fmt(stake[3])}`);

// All loans (check both STASIS loans and token loans via getUserLoanCount per token)
const FEDCUT = '0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06';
const LVTHN = '0xFf84209eBCCAc7328070E0011e973451c4a045F9';

console.log('\n=== Loans ===');
// FEDCUT loans
const fedcutLoanCount = await client.loans.getUserLoanCount(wallet, FEDCUT);
console.log(`FEDCUT loans: ${fedcutLoanCount}`);
for (let i = 1; i <= Number(fedcutLoanCount); i++) {
  const loan = await client.loans.getUserLoanDetails(wallet, FEDCUT, i);
  const now = Math.floor(Date.now() / 1000);
  const daysLeft = (Number(loan[9]) - now) / 86400;
  console.log(`  Loan ${i}: collateral=${fmt(loan[5])}, borrowed=${fmt(loan[8])}, repay=${fmt(loan[7])}, active=${loan[12]}, expires in ${daysLeft.toFixed(1)} days`);
}

// LVTHN loans
const lvthnLoanCount = await client.loans.getUserLoanCount(wallet, LVTHN);
console.log(`LVTHN loans: ${lvthnLoanCount}`);
for (let i = 1; i <= Number(lvthnLoanCount); i++) {
  const loan = await client.loans.getUserLoanDetails(wallet, LVTHN, i);
  const now = Math.floor(Date.now() / 1000);
  const daysLeft = (Number(loan[9]) - now) / 86400;
  console.log(`  Loan ${i}: collateral=${fmt(loan[5])}, borrowed=${fmt(loan[8])}, repay=${fmt(loan[7])}, active=${loan[12]}, expires in ${daysLeft.toFixed(1)} days`);
}

// STASIS loans (from earlier)
const stasisLoanCount = await client.loans.getUserLoanCount(wallet, MAINTOKEN);
console.log(`STASIS loans: ${stasisLoanCount}`);

// Vault loan details
const availableStasis = await client.staking.getAvailableStasis(wallet);
console.log(`\nAvailable STASIS for new borrowing: ${fmt(availableStasis)}`);

// Prices
const stasisPrice = await client.trading.getUSDPrice(MAINTOKEN);
const fedcutPrice = await client.trading.getUSDPrice(FEDCUT);
const lvthnPrice = await client.trading.getUSDPrice(LVTHN);
console.log(`\n=== Prices ===`);
console.log(`STASIS: $${fmt(stasisPrice)}`);
console.log(`FEDCUT: $${fmt(fedcutPrice)}`);
console.log(`LVTHN: $${fmt(lvthnPrice)}`);

// Floor price for LVTHN
const lvthnFloor = await client.factory.getFloorPrice(LVTHN);
console.log(`LVTHN floor: $${fmt(lvthnFloor)}`);
