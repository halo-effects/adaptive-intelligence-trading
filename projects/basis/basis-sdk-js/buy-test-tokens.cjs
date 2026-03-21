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

const publicClient = createPublicClient({
  chain: bsc,
  transport: http('https://bsc-dataseed.binance.org'),
});

const walletClient = createWalletClient({
  account,
  chain: bsc,
  transport: http('https://bsc-dataseed.binance.org'),
});

const tokens = [
  { symbol: 'HAPPY', hybrid: 1, address: '0xcae748f4bfcd091261ddc383d45b54cd87937b33' },
  { symbol: 'TH15', hybrid: 15, address: '0xf300e97967bddeeaf93514e86a6a16c787325250' },
  { symbol: 'TH30', hybrid: 30, address: '0x7f6c6a5e0fa11230653ca938913a9bcfeb8ea4ce' },
  { symbol: 'TH45', hybrid: 45, address: '0xa95b0db97d97e74c7cf298b1ebfe31d1699cef8c' },
  { symbol: 'TH60', hybrid: 60, address: '0x4d5ce0768f3bd2df239685ef236d7629ef779830' },
  { symbol: 'TH90', hybrid: 90, address: '0xda684cdf8248eae2b875a8c9bc2e968ffbc478a7' },
];

const BUY_AMOUNT = parseUnits('1', 18); // $1 USDB

async function approveUSDB() {
  // Check current allowance
  const allowance = await publicClient.readContract({
    address: USDB,
    abi: ERC20_ABI,
    functionName: 'allowance',
    args: [account.address, SWAP],
  });
  
  if (allowance < parseUnits('100', 18)) {
    console.log('Approving USDB for SWAP contract...');
    const { request } = await publicClient.simulateContract({
      account,
      address: USDB,
      abi: ERC20_ABI,
      functionName: 'approve',
      args: [SWAP, parseUnits('1000', 18)],
    });
    const hash = await walletClient.writeContract(request);
    await publicClient.waitForTransactionReceipt({ hash });
    console.log('Approved!\n');
  }
}

async function buyToken(token) {
  console.log(`Buying $1 of ${token.symbol} (hybrid=${token.hybrid})...`);
  
  const path = [USDB, STASIS, token.address];
  
  try {
    const { request } = await publicClient.simulateContract({
      account,
      address: SWAP,
      abi: SWAP_ABI,
      functionName: 'buyTokens',
      args: [BUY_AMOUNT, 0n, path, false], // amount, minOut, path, wrapTokens
    });
    
    const hash = await walletClient.writeContract(request);
    const receipt = await publicClient.waitForTransactionReceipt({ hash });
    
    // Check token balance after
    const balance = await publicClient.readContract({
      address: token.address,
      abi: ERC20_ABI,
      functionName: 'balanceOf',
      args: [account.address],
    });
    
    console.log(`  TX: ${hash}`);
    console.log(`  Status: ${receipt.status}`);
    console.log(`  Token balance: ${formatUnits(balance, 18)}`);
    
    // Now simulate what we'd get selling those tokens back
    const sellQuote = await publicClient.readContract({
      address: SWAP,
      abi: SWAP_ABI,
      functionName: 'getAmountsOut',
      args: [balance, [token.address, STASIS, USDB]],
    });
    console.log(`  Sell quote: $${formatUnits(sellQuote, 18)} USDB`);
    console.log('');
    
    return { symbol: token.symbol, hybrid: token.hybrid, balance: formatUnits(balance, 18), sellQuote: formatUnits(sellQuote, 18) };
  } catch (e) {
    console.log(`  ERROR: ${(e.shortMessage || e.message).slice(0, 200)}\n`);
    return { symbol: token.symbol, hybrid: token.hybrid, error: true };
  }
}

async function main() {
  console.log('Buying $1 USDB of each token, then checking sell quotes\n');
  
  await approveUSDB();
  
  const results = [];
  for (const token of tokens) {
    const result = await buyToken(token);
    results.push(result);
    await new Promise(r => setTimeout(r, 2000));
  }
  
  console.log('\n=== SUMMARY ===');
  console.log('Token | Hybrid | Tokens Received | Sell Quote');
  console.log('----------------------------------------------');
  for (const r of results) {
    if (r.error) {
      console.log(`${r.symbol} | ${r.hybrid} | ERROR`);
    } else {
      console.log(`${r.symbol} | ${r.hybrid} | ${r.balance} | $${r.sellQuote}`);
    }
  }
}

main().catch(console.error);
