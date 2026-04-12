import { BasisClient } from 'basis-sdk';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load env
const envPath = path.join(__dirname, '..', 'skill-scaffold', '.env');
const env = fs.readFileSync(envPath, 'utf-8')
  .split('\n')
  .filter(line => line.trim() && !line.startsWith('#'))
  .reduce((acc, line) => {
    const [key, ...rest] = line.split('=');
    acc[key.trim()] = rest.join('=').trim().replace(/^["']|["']$/g, '');
    return acc;
  }, {});

const PRIVATE_KEY = env.BASIS_PRIVATE_KEY;
const API_KEY = env.BASIS_API_KEY;

console.log('=== BasisClient imported ===');
console.log('BasisClient.create:', typeof BasisClient?.create);

console.log('\n=== Creating client ===');
try {
  const client = await BasisClient.create({ privateKey: PRIVATE_KEY, apiKey: API_KEY });
  console.log('Client created ✓');
  console.log('Client keys:', Object.keys(client).slice(0, 15));
  
  // Find the wallet address
  const wallet = client.walletClient?.account?.address || client.account?.address;
  console.log(`Wallet: ${wallet}`);
  console.log(`USDB address: ${client.usdbAddress}`);
  console.log(`STASIS address: ${client.mainTokenAddress}`);
  
  // Try auth
  console.log('\n=== Authenticating ===');
  try {
    const session = await client.authenticate();
    console.log('Auth result:', JSON.stringify(session).substring(0, 200));
  } catch (e) { console.log('Auth error:', e.message); }
  
  // Try faucet status
  console.log('\n=== Faucet ===');
  try {
    const faucet = await client.api.getFaucetStatus();
    console.log(JSON.stringify(faucet, null, 2));
  } catch (e) { console.log('Faucet error:', e.message); }
  
  // Try profile
  console.log('\n=== Profile ===');
  try {
    const profile = await client.api.getMyProfile();
    console.log(JSON.stringify(profile, null, 2));
  } catch (e) { console.log('Profile error:', e.message); }

  // Try getTokens
  console.log('\n=== Tokens ===');
  try {
    const tokens = await client.api.getTokens({ limit: 10, sort: 'newest' });
    if (tokens?.data) {
      console.log(`Found ${tokens.data.length} tokens:`);
      for (const t of tokens.data.slice(0, 5)) {
        console.log(`  ${t.symbol} | mult=${t.multiplier} | addr: ${t.address}`);
      }
    } else {
      console.log('Tokens response:', JSON.stringify(tokens).substring(0, 300));
    }
  } catch (e) { console.log('Tokens error:', e.message); }

  // On-chain balance
  console.log('\n=== On-Chain Balances ===');
  const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
  try {
    const usdb = await client.publicClient.readContract({ address: client.usdbAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
    console.log(`USDB: ${Number(usdb) / 10**18}`);
  } catch (e) { console.log('USDB error:', e.message); }
  try {
    const stasis = await client.publicClient.readContract({ address: client.mainTokenAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
    console.log(`STASIS: ${Number(stasis) / 10**18}`);
  } catch (e) { console.log('STASIS error:', e.message); }

  // Staking details
  console.log('\n=== Staking ===');
  try {
    const details = await client.staking.getUserStakeDetails(wallet);
    console.log('Stake details:', JSON.stringify(details, (k, v) => typeof v === 'bigint' ? v.toString() : v, 2));
  } catch (e) { console.log('Staking error:', e.message); }
  
  // Loan count
  console.log('\n=== Loans ===');
  try {
    // Per Module 18: getUserLoanCount(wallet, tokenAddress)
    const stasisLoans = await client.loans.getUserLoanCount(wallet, client.mainTokenAddress);
    console.log(`STASIS loan count: ${stasisLoans}`);
  } catch (e) { console.log('Loans error:', e.message); }

} catch (e) {
  console.error('Client creation error:', e.message);
  console.error(e);
}
