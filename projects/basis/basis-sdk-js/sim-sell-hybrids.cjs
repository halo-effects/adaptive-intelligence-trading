const { createPublicClient, http, parseUnits, formatUnits } = require('viem');
const { bsc } = require('viem/chains');
const fs = require('fs');

const SWAP_ABI = JSON.parse(fs.readFileSync('./src/abis/ASwap.json', 'utf8')).abi;

const client = createPublicClient({
  chain: bsc,
  transport: http('https://bsc-dataseed.binance.org'),
});

const SWAP = '0xa2483dd5d22D1A8a01473878f247fEC8dC952f1e';
const USDB = '0x217B82e4bAc4E4647B1F189F33554229Ce27c51A';
const STASIS = '0xE4b1ed74C77984EbFf1CE871E7F7c9414e5dd73b';

const tokens = [
  { symbol: 'HAPPY', hybrid: 1, address: '0xcae748f4bfcd091261ddc383d45b54cd87937b33' },
  { symbol: 'TH15', hybrid: 15, address: '0xf300e97967bddeeaf93514e86a6a16c787325250' },
  { symbol: 'TH30', hybrid: 30, address: '0x7f6c6a5e0fa11230653ca938913a9bcfeb8ea4ce' },
  { symbol: 'TH45', hybrid: 45, address: '0xa95b0db97d97e74c7cf298b1ebfe31d1699cef8c' },
  { symbol: 'TH60', hybrid: 60, address: '0x4d5ce0768f3bd2df239685ef236d7629ef779830' },
  { symbol: 'TH90', hybrid: 90, address: '0xda684cdf8248eae2b875a8c9bc2e968ffbc478a7' },
];

// Simulate selling tokens back to USDB
const sellAmounts = [10, 50, 100, 500, 1000];

async function simulate(token, tokenAmount) {
  const rawAmount = parseUnits(String(tokenAmount), 18);
  try {
    const result = await client.readContract({
      address: SWAP,
      abi: SWAP_ABI,
      functionName: 'getAmountsOut',
      args: [rawAmount, [token.address, STASIS, USDB]],
    });
    const usdbOut = parseFloat(formatUnits(result, 18));
    return usdbOut.toFixed(2);
  } catch (e) {
    return 'ERR: ' + (e.shortMessage || e.message).slice(0, 60);
  }
}

async function main() {
  console.log('SELL Simulation — hybridMultiplier Comparison (all startLP=1000)');
  console.log('================================================================');
  console.log('Shows USDB received when selling X tokens\n');
  
  const header = 'Hybrid | ' + sellAmounts.map(a => `Sell ${a} tokens`).join(' | ');
  console.log(header);
  console.log('-'.repeat(header.length));
  
  for (const token of tokens) {
    const results = [];
    for (const amt of sellAmounts) {
      const usdb = await simulate(token, amt);
      results.push(`$${usdb}`);
    }
    console.log(`  ${String(token.hybrid).padStart(3)} | ${results.join(' | ')}`);
  }
}

main().catch(console.error);
