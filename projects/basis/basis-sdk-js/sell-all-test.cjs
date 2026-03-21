const { createPublicClient, createWalletClient, http, parseUnits, formatUnits } = require('viem');
const { bsc } = require('viem/chains');
const { privateKeyToAccount } = require('viem/accounts');
const fs = require('fs');

const SWAP_ABI = JSON.parse(fs.readFileSync('./src/abis/ASwap.json', 'utf8')).abi;
const ERC20_ABI = JSON.parse(fs.readFileSync('./src/abis/IERC20.json', 'utf8')).abi;

const SWAP = '0xa2483dd5d22D1A8a01473878f247fEC8dC952f1e';
const USDB = '0x217B82e4bAc4E4647B1F189F33554229Ce27c51A';
const STASIS = '0xE4b1ed74C77984EbFf1CE871E7F7c9414e5dd73b';
const PRIVATE_KEY = '0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4';

const account = privateKeyToAccount(PRIVATE_KEY);
const publicClient = createPublicClient({ chain: bsc, transport: http('https://bsc-dataseed.binance.org') });
const walletClient = createWalletClient({ account, chain: bsc, transport: http('https://bsc-dataseed.binance.org') });

const tokens = [
  { s: 'TH15', h: 15, a: '0xf300e97967bddeeaf93514e86a6a16c787325250' },
  { s: 'TH30', h: 30, a: '0x7f6c6a5e0fa11230653ca938913a9bcfeb8ea4ce' },
  { s: 'TH45', h: 45, a: '0xa95b0db97d97e74c7cf298b1ebfe31d1699cef8c' },
  { s: 'TH60', h: 60, a: '0x4d5ce0768f3bd2df239685ef236d7629ef779830' },
  { s: 'TH90', h: 90, a: '0xda684cdf8248eae2b875a8c9bc2e968ffbc478a7' },
];

async function getPrice(tokenAddr) {
  const tiny = parseUnits('0.001', 18);
  const out = await publicClient.readContract({
    address: SWAP, abi: SWAP_ABI, functionName: 'getAmountsOut',
    args: [tiny, [USDB, STASIS, tokenAddr]],
  });
  return 0.001 / parseFloat(formatUnits(out, 18));
}

async function main() {
  console.log('Prices BEFORE sell:');
  for (const t of tokens) {
    const p = await getPrice(t.a);
    console.log(`  ${t.s} (h=${t.h}): $${p.toFixed(6)}`);
  }

  console.log('\nSelling ALL tokens on each...\n');

  for (const t of tokens) {
    try {
      // Get balance
      const balance = await publicClient.readContract({
        address: t.a, abi: ERC20_ABI, functionName: 'balanceOf', args: [account.address],
      });
      console.log(`  ${t.s}: balance = ${formatUnits(balance, 18)} tokens`);
      
      if (balance === 0n) {
        console.log(`  ${t.s}: no tokens to sell\n`);
        continue;
      }

      // Approve token for SWAP
      const allowance = await publicClient.readContract({
        address: t.a, abi: ERC20_ABI, functionName: 'allowance', args: [account.address, SWAP],
      });
      if (allowance < balance) {
        const { request: approveReq } = await publicClient.simulateContract({
          account, address: t.a, abi: ERC20_ABI, functionName: 'approve',
          args: [SWAP, balance],
        });
        const approveHash = await walletClient.writeContract(approveReq);
        await publicClient.waitForTransactionReceipt({ hash: approveHash });
        console.log(`  ${t.s}: approved`);
      }

      // Sell via sellTokens
      const { request } = await publicClient.simulateContract({
        account, address: SWAP, abi: SWAP_ABI, functionName: 'sellTokens',
        args: [balance, 0n, [t.a, STASIS, USDB], false], // amount, minOut, path, toEth
      });
      const hash = await walletClient.writeContract(request);
      const receipt = await publicClient.waitForTransactionReceipt({ hash });
      console.log(`  ${t.s}: SOLD - tx ${receipt.status}\n`);
    } catch (e) {
      console.log(`  ${t.s}: ERROR - ${(e.shortMessage || e.message).slice(0, 150)}\n`);
    }
    await new Promise(r => setTimeout(r, 2000));
  }

  console.log('Prices AFTER selling all:');
  for (const t of tokens) {
    const p = await getPrice(t.a);
    console.log(`  ${t.s} (h=${t.h}): $${p.toFixed(6)}`);
  }
}

main().catch(console.error);
