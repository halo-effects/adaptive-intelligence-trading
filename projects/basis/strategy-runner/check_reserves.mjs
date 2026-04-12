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
const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];

// Get all tokens
const allTokens = await client.api.getTokens({ limit: 100 });
console.log(`Total tokens: ${allTokens.data.length}`);
console.log(`\nChecking ALL token fields for first few tokens:\n`);

// Print full token object for first 3
for (const t of allTokens.data.slice(0, 3)) {
  console.log(JSON.stringify(t, null, 2));
  console.log('---');
}

// Check on-chain state for a few tokens
console.log('\n=== On-chain checks ===\n');
const candidates = [
  { symbol: 'FEDCUT', addr: '0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06', type: 'Predict+' },
  { symbol: 'TGEQ2', addr: '0x22acB59faEBDEf1133016D96752Ab3366aB3bFC1', type: 'Predict+' },
  { symbol: 'CSTACK', addr: '0xADeCa6980c92466947704875c7D1e6aa9081cCB7', type: 'Floor+' },
  { symbol: 'LVTHN', addr: '0xFf84209eBCCAc7328070E0011e973451c4a045F9', type: 'Floor+' },
];

for (const c of candidates) {
  console.log(`${c.symbol} (${c.type}) — ${c.addr}`);
  
  // Check token state via factory
  try {
    const state = await client.factory.getTokenState(c.addr);
    console.log(`  Token state:`, JSON.stringify(state, (k,v) => typeof v === 'bigint' ? v.toString() : v));
  } catch (e) { console.log(`  State error: ${e.message.substring(0, 80)}`); }

  // Check price
  try {
    const price = await client.trading.getUSDPrice(c.addr);
    console.log(`  USD price: $${(Number(price) / 1e18).toFixed(6)}`);
  } catch (e) { console.log(`  Price error: ${e.message.substring(0, 80)}`); }

  // Is it an ecosystem token?
  try {
    const isEco = await client.factory.isEcosystemToken(c.addr);
    console.log(`  Ecosystem token: ${isEco}`);
  } catch (e) { console.log(`  Eco check error: ${e.message.substring(0, 80)}`); }

  // If predict+, check market data
  if (c.type === 'Predict+') {
    try {
      const market = await client.predictionMarkets.getMarketData(c.addr);
      console.log(`  Market:`, JSON.stringify(market, (k,v) => typeof v === 'bigint' ? v.toString() : v).substring(0, 400));
    } catch (e) { console.log(`  Market error: ${e.message.substring(0, 80)}`); }
  }

  // If Floor+, check floor price
  if (c.type === 'Floor+') {
    try {
      const floor = await client.factory.getFloorPrice(c.addr);
      console.log(`  Floor price: $${(Number(floor) / 1e18).toFixed(6)}`);
    } catch (e) { console.log(`  Floor error: ${e.message.substring(0, 80)}`); }
  }

  console.log();
}
