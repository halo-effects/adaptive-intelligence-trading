/**
 * Custom Stacking Strategy - Step 2
 * Create a Floor+ token
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
const fmt = (v) => formatUnits(v, 18);

console.log('========== STEP 2: Create Token ==========\n');

// Check creation fee
const fee = await client.factory.getFeeAmount();
console.log(`Creation fee: ${fmt(fee)} BNB`);

// Create a Floor+ token (hybridMultiplier=50 = balanced Floor+)
console.log('\nCreating LOBSTER (Floor+ balanced, mult=50, LP=1000)...');
const result = await client.factory.createTokenWithMetadata({
  symbol: "LOBSTER",
  name: "Lobster Protocol",
  hybridMultiplier: 50n,
  startLP: 1000n,
  description: "Stack like a lobster. Built for the custom stacking strategy test.",
  imageUrl: "https://cyan-abundant-swordtail-589.mypinata.cloud/ipfs/bafkreifi7ysl4wftlsw2ncvo33i7y37i4ij5dwvmfpka2r4wrgraidygwm",
  website: "https://launchonbasis.com",
});

console.log(`\n✓ Token created!`);
console.log(`  Address: ${result.tokenAddress}`);
console.log(`  Hash: ${result.hash}`);
console.log(`  Image: ${result.imageUrl}`);

// Verify token state
const state = await client.factory.getTokenState(result.tokenAddress);
console.log(`\nToken state:`, JSON.stringify(state, (k,v) => typeof v === 'bigint' ? v.toString() : v));

const isEco = await client.factory.isEcosystemToken(result.tokenAddress);
console.log(`Is ecosystem token: ${isEco}`);
