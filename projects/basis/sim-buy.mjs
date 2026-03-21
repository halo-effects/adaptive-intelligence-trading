import { createPublicClient, http, parseUnits, formatUnits } from 'viem';
import { bsc } from 'viem/chains';
import { readFileSync } from 'fs';

const SWAP_ABI = JSON.parse(readFileSync('./basis-sdk-js/src/abi/ASwap.json', 'utf8')).abi;

const client = createPublicClient({
  chain: bsc,
  transport: http('https://bsc-dataseed.binance.org'),
});

const SWAP = '0xa2483dd5d22D1A8a01473878f247fEC8dC952f1e';
const USDB = '0x217B82e4bAc4E4647B1F189F33554229Ce27c51A';
const STASIS = '0xE4b1ed74C77984EbFf1CE871E7F7c9414e5dd73b';
const HAPPY = '0xcae748f4bfcd091261ddc383d45b54cd87937b33';

// Simulate buying HAPPY with various USDB amounts
const amounts = [10, 50, 100, 500, 1000];

for (const amt of amounts) {
  const rawAmount = parseUnits(String(amt), 18);
  // Path: USDB -> STASIS -> HAPPY
  try {
    const result = await client.readContract({
      address: SWAP,
      abi: SWAP_ABI,
      functionName: 'getAmountsOut',
      args: [rawAmount, [USDB, STASIS, HAPPY]],
    });
    console.log(`$${amt} USDB -> ${formatUnits(result, 18)} HAPPY tokens`);
  } catch (e) {
    console.log(`$${amt} USDB -> ERROR: ${e.message?.slice(0, 100)}`);
  }
}
