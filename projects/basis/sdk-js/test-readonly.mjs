/**
 * Full read-only SDK tests against live BSC.
 */
import { BasisClient } from './dist/index.mjs';

const USDB = '0x78dD776204aA7e06BaF488959a90142f0B3027CE';
const MAINTOKEN = '0x76ACb5F98A422995a801008c8b7b28dBC23946Ff';
const MAX_TOKEN = '0x09A3b840ac0d151F2dfB427a7E006FE44970EDB9';
const MAX_MARKET = '0xf510891992a5004Be3783aE1b4D7Cfa67907D8d8';
const MARKET_TRADING = '0xCb64910a19B3641eb600b904741a074578Dda3F7';
const ZERO_ADDR = '0x0000000000000000000000000000000000000001';

const results = [];

async function test(name, fn) {
  try {
    const result = await fn();
    const str = typeof result === 'object' ? JSON.stringify(result).slice(0, 150) : String(result).slice(0, 150);
    results.push({ test: name, status: 'PASS', result: str });
    console.log(`  PASS ${name}: ${str.slice(0, 100)}`);
    return result;
  } catch (e) {
    results.push({ test: name, status: 'FAIL', error: e.message?.slice(0, 200) || String(e).slice(0, 200) });
    console.log(`  FAIL ${name}: ${e.message || e}`);
    return null;
  }
}

console.log('='.repeat(60));
console.log('Basis JS/TS SDK v0.1.0-beta.1 - Full Read-Only Tests');
console.log('='.repeat(60));

// 1. Init
console.log('\n1. Initialize client');
const client = new BasisClient();
const chainId = await client.publicClient.getChainId();
console.log(`  ${chainId === 56 ? 'PASS' : 'FAIL'} Connected to BSC (chain ${chainId})`);
results.push({ test: 'init', status: chainId === 56 ? 'PASS' : 'FAIL' });

// 2. Trading reads
console.log('\n2. Trading module');
await test('getUSDPrice(MAINTOKEN)', () => client.trading.getUSDPrice(MAINTOKEN));
await test('getTokenPrice(MAX_TOKEN)', () => client.trading.getTokenPrice(MAX_TOKEN));
await test('getAmountsOut(5 USDB -> MAINTOKEN)', () => client.trading.getAmountsOut(5n * 10n**18n, [USDB, MAINTOKEN]));
await test('getAmountsOut(5 USDB -> MAX 3-hop)', () => client.trading.getAmountsOut(5n * 10n**18n, [USDB, MAINTOKEN, MAX_TOKEN]));

// 3. Factory reads
console.log('\n3. Factory module');
await test('getTokenState(MAX_TOKEN)', () => client.factory.getTokenState(MAX_TOKEN));
await test('isEcosystemToken(MAX_TOKEN)', () => client.factory.isEcosystemToken(MAX_TOKEN));
await test('getFeeAmount()', () => client.factory.getFeeAmount());
await test('getTokensByCreator(zero)', () => client.factory.getTokensByCreator(ZERO_ADDR));

// 4. Staking reads
console.log('\n4. Staking module');
await test('convertToShares(100 STASIS)', () => client.staking.convertToShares(100n * 10n**18n));
await test('convertToAssets(100 wSTASIS)', () => client.staking.convertToAssets(100n * 10n**18n));

// 5. Taxes reads
console.log('\n5. Taxes module');
await test('getBaseTaxRates()', () => client.taxes.getBaseTaxRates());
await test('getCurrentSurgeTax(MAX_TOKEN)', () => client.taxes.getCurrentSurgeTax(MAX_TOKEN));
await test('getAvailableSurgeQuota(MAX_TOKEN)', () => client.taxes.getAvailableSurgeQuota(MAX_TOKEN));

// 6. Prediction markets reads
console.log('\n6. Prediction markets module');
await test('getMarketData(MAX_MARKET)', () => client.predictionMarkets.getMarketData(MAX_MARKET));
await test('getOutcome(MAX_MARKET, 0)', () => client.predictionMarkets.getOutcome(MAX_MARKET, 0));
await test('getInitialReserves(2)', () => client.predictionMarkets.getInitialReserves(2));
await test('getUserShares(MAX_MARKET, zero, 0)', () => client.predictionMarkets.getUserShares(MAX_MARKET, ZERO_ADDR, 0));

// 7. Agent identity reads
console.log('\n7. Agent identity module');
await test('isRegistered(zero)', () => client.agent.isRegistered(ZERO_ADDR));

// 8. Market reader reads
console.log('\n8. Market reader module');
await test('getAllOutcomes(MAX_MARKET)', () => client.marketReader.getAllOutcomes(MARKET_TRADING, MAX_MARKET));

// 9. Leverage simulator reads
console.log('\n9. Leverage simulator module');
await test('simulateLeverage(10 USDB, 7 days)', () => client.leverageSimulator.simulateLeverage(10n * 10n**18n, [USDB, MAINTOKEN], 7n));

// 10. Resolver reads
console.log('\n10. Resolver module');
await test('isResolved(MAX_MARKET)', () => client.resolver.isResolved(MAX_MARKET));
await test('isInDispute(MAX_MARKET)', () => client.resolver.isInDispute(MAX_MARKET));
await test('isInVeto(MAX_MARKET)', () => client.resolver.isInVeto(MAX_MARKET));
await test('getFinalOutcome(MAX_MARKET)', () => client.resolver.getFinalOutcome(MAX_MARKET));
await test('getCurrentRound(MAX_MARKET)', () => client.resolver.getCurrentRound(MAX_MARKET));

// 11. Loans reads
console.log('\n11. Loans module');
await test('getUserLoanCount(zero)', () => client.loans.getUserLoanCount(ZERO_ADDR));

// 12. Vesting reads
console.log('\n12. Vesting module');
await test('getClaimableAmount(0)', () => client.vesting.getClaimableAmount(0n));

// 13. Module availability
console.log('\n13. Module availability');
const modules = ['trading', 'factory', 'loans', 'staking', 'vesting', 'predictionMarkets',
  'orderBook', 'resolver', 'privateMarkets', 'marketReader', 'leverageSimulator', 'taxes', 'agent', 'api'];
for (const mod of modules) {
  const has = mod in client;
  results.push({ test: `has_${mod}`, status: has ? 'PASS' : 'FAIL' });
  console.log(`  ${has ? 'PASS' : 'FAIL'} client.${mod}`);
}

// 14. Package structure
console.log('\n14. Package checks');
import fs from 'fs';
const hasPkg = fs.existsSync('./package.json');
const hasDist = fs.existsSync('./dist/index.js');
const hasTypes = fs.existsSync('./dist/index.d.ts');
results.push({ test: 'has_package_json', status: hasPkg ? 'PASS' : 'FAIL' });
results.push({ test: 'has_dist_cjs', status: hasDist ? 'PASS' : 'FAIL' });
results.push({ test: 'has_types', status: hasTypes ? 'PASS' : 'FAIL' });
console.log(`  ${hasPkg ? 'PASS' : 'FAIL'} package.json`);
console.log(`  ${hasDist ? 'PASS' : 'FAIL'} dist/index.js (CJS)`);
console.log(`  ${hasTypes ? 'PASS' : 'FAIL'} dist/index.d.ts (types)`);

// Summary
console.log('\n' + '='.repeat(60));
const passed = results.filter(r => r.status === 'PASS').length;
const failed = results.filter(r => r.status === 'FAIL').length;
console.log(`Results: ${passed} passed, ${failed} failed, ${results.length} total`);
console.log('='.repeat(60));

if (failed > 0) {
  console.log('\nFailed tests:');
  results.filter(r => r.status === 'FAIL').forEach(r => {
    console.log(`  - ${r.test}: ${r.error || 'no error'}`);
  });
}

fs.writeFileSync('./test-readonly-results.json', JSON.stringify(results, null, 2));
console.log('\nResults saved to test-readonly-results.json');
