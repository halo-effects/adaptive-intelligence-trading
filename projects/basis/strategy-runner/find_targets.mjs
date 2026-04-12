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

// Get ALL tokens, sort by liquidity
console.log('=== All tokens with liquidity > 0 ===\n');
const allTokens = await client.api.getTokens({ limit: 100, sort: 'liquidity' });
if (allTokens?.data) {
  const withLiq = allTokens.data.filter(t => t.liquidityUSD > 0);
  console.log(`Tokens with liquidity: ${withLiq.length} / ${allTokens.data.length}\n`);

  // Categorize
  const predictTokens = withLiq.filter(t => t.isPrediction);
  const floorTokens = withLiq.filter(t => !t.isPrediction && t.multiplier < 100);
  const stableTokens = withLiq.filter(t => !t.isPrediction && t.multiplier === 100);

  console.log('--- Predict+ tokens with liquidity ---');
  for (const t of predictTokens) {
    console.log(`  ${t.symbol.padEnd(12)} | liq=$${t.liquidityUSD.toFixed(0).padStart(8)} | ${t.name.substring(0, 50)} | ${t.address}`);
  }
  
  console.log('\n--- Floor+ tokens with liquidity ---');
  for (const t of floorTokens) {
    console.log(`  ${t.symbol.padEnd(12)} | liq=$${t.liquidityUSD.toFixed(0).padStart(8)} | mult=${t.multiplier} | ${t.name?.substring(0, 30)} | ${t.address}`);
  }
  
  console.log('\n--- Stable+ tokens with liquidity ---');
  for (const t of stableTokens) {
    console.log(`  ${t.symbol.padEnd(12)} | liq=$${t.liquidityUSD.toFixed(0).padStart(8)} | ${t.name?.substring(0, 30)} | ${t.address}`);
  }

  // Also show top tokens by volume if available
  console.log('\n--- All tokens by liquidity (top 15) ---');
  for (const t of withLiq.slice(0, 15)) {
    const type = t.isPrediction ? 'Predict+' : (t.multiplier === 100 ? 'Stable+' : `Floor+(${t.multiplier})`);
    console.log(`  ${t.symbol.padEnd(12)} | ${type.padEnd(12)} | liq=$${t.liquidityUSD.toFixed(0).padStart(8)} | vol=$${(t.volume24h||0).toFixed(0).padStart(8)} | ${t.address}`);
  }
} else {
  console.log('No token data returned');
  console.log(JSON.stringify(allTokens).substring(0, 500));
}

// Also check prediction market details for any active ones
console.log('\n=== Prediction Market Details ===');
const preds = await client.api.getTokens({ isPrediction: true, limit: 20 });
if (preds?.data) {
  for (const t of preds.data.filter(p => p.liquidityUSD > 0)) {
    console.log(`\n  ${t.symbol} | ${t.name}`);
    console.log(`  Liquidity: $${t.liquidityUSD} | Address: ${t.address}`);
    // Get market data
    try {
      const market = await client.predictionMarkets.getMarketData(t.address);
      console.log(`  Market data:`, JSON.stringify(market, (k,v) => typeof v === 'bigint' ? v.toString() : v).substring(0, 300));
    } catch (e) { console.log(`  Market error: ${e.message.substring(0, 100)}`); }
  }
}
