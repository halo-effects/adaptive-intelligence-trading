import { BasisClient } from 'basis-sdk';
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
const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];

console.log(`Wallet: ${wallet}`);
console.log(`USDB: ${client.usdbAddress}`);
console.log(`STASIS: ${client.mainTokenAddress}`);

// Balances
const usdb = await client.publicClient.readContract({ address: client.usdbAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
const stasis = await client.publicClient.readContract({ address: client.mainTokenAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
console.log(`\n=== Balances ===`);
console.log(`USDB: ${(Number(usdb) / 1e18).toFixed(4)}`);
console.log(`STASIS: ${(Number(stasis) / 1e18).toFixed(4)}`);

// Staking
const details = await client.staking.getUserStakeDetails(wallet);
console.log(`\n=== Staking ===`);
console.log(`Liquid wSTASIS: ${(Number(details[0]) / 1e18).toFixed(4)}`);
console.log(`Locked wSTASIS: ${(Number(details[1]) / 1e18).toFixed(4)}`);
console.log(`Total wSTASIS: ${(Number(details[2]) / 1e18).toFixed(4)}`);
console.log(`Total STASIS value: ${(Number(details[3]) / 1e18).toFixed(4)}`);

// Loans
console.log(`\n=== Loans ===`);
const stasisLoanCount = await client.loans.getUserLoanCount(wallet, client.mainTokenAddress);
console.log(`STASIS loans: ${stasisLoanCount}`);

// Agent registration
console.log(`\n=== Agent Identity ===`);
const isRegistered = await client.agent.isRegistered(wallet);
console.log(`Registered: ${isRegistered}`);

// Faucet
const faucet = await client.api.getFaucetStatus();
console.log(`\n=== Faucet ===`);
console.log(`Can claim: ${faucet.canClaim}`);
console.log(`Daily amount: ${faucet.dailyAmount} USDB`);

// Profile (needs API key auth)
console.log(`\n=== Profile ===`);
try {
  const profile = await client.api.getMyProfile();
  console.log(JSON.stringify(profile, null, 2));
} catch (e) { console.log(`Error: ${e.message.substring(0, 150)}`); }

// Moltbook
console.log(`\n=== Moltbook ===`);
try {
  const mb = await client.api.getMoltbookStatus();
  console.log(JSON.stringify(mb, null, 2));
} catch (e) { console.log(`Error: ${e.message.substring(0, 150)}`); }

// Token discovery
console.log(`\n=== All Tokens (newest 20) ===`);
try {
  const tokens = await client.api.getTokens({ limit: 20, sort: 'newest' });
  if (tokens?.data) {
    console.log(`Total: ${tokens.data.length}`);
    for (const t of tokens.data) {
      const type = t.isPrediction ? 'Predict+' : (t.multiplier === 100 ? 'Stable+' : `Floor+(${t.multiplier})`);
      console.log(`  ${t.symbol.padEnd(12)} | ${type.padEnd(12)} | liq=$${(t.liquidityUSD||0).toFixed(0).padStart(6)} | ${t.address}`);
    }
  }
} catch (e) { console.log(`Error: ${e.message.substring(0, 200)}`); }

// Prediction markets specifically
console.log(`\n=== Prediction Markets ===`);
try {
  const preds = await client.api.getTokens({ isPrediction: true, limit: 10, sort: 'newest' });
  if (preds?.data) {
    console.log(`Total: ${preds.data.length}`);
    for (const t of preds.data) {
      console.log(`  ${t.symbol.padEnd(12)} | ${t.name.substring(0,45).padEnd(45)} | ${t.address}`);
    }
  }
} catch (e) { console.log(`Error: ${e.message.substring(0, 200)}`); }

console.log(`\n=== STASIS Price ===`);
const price = await client.trading.getUSDPrice(client.mainTokenAddress);
console.log(`$${(Number(price) / 1e18).toFixed(6)}`);

// Claim faucet if eligible
if (faucet.canClaim) {
  console.log(`\n=== Claiming Faucet (${faucet.dailyAmount} USDB) ===`);
  try {
    const claim = await client.claimFaucet();
    console.log(`Claim result:`, JSON.stringify(claim, (k, v) => typeof v === 'bigint' ? v.toString() : v));
  } catch (e) { console.log(`Claim error: ${e.message.substring(0, 200)}`); }
}

console.log('\n=== Done ===');
