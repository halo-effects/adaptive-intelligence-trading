const { createPublicClient, createWalletClient, http, parseEther, formatEther } = require('viem');
const { bsc } = require('viem/chains');
const { privateKeyToAccount } = require('viem/accounts');
const fs = require('fs');

const FACTORY_ABI = JSON.parse(fs.readFileSync('./src/abis/ATokenFactory.json', 'utf8')).abi;

const FACTORY = '0xd80850a3b712E6B9dB4d3e487c76b7c1F904E273';
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
  { symbol: 'TH15', name: 'Test Hybrid 15', hybridMultiplier: 15n },
  { symbol: 'TH30', name: 'Test Hybrid 30', hybridMultiplier: 30n },
  { symbol: 'TH45', name: 'Test Hybrid 45', hybridMultiplier: 45n },
  { symbol: 'TH60', name: 'Test Hybrid 60', hybridMultiplier: 60n },
  { symbol: 'TH90', name: 'Test Hybrid 90', hybridMultiplier: 90n },
];

async function createToken(token) {
  console.log(`\nCreating ${token.symbol} (hybridMultiplier=${token.hybridMultiplier})...`);
  
  // Get creation fee
  const feeAmount = await publicClient.readContract({
    address: FACTORY,
    abi: FACTORY_ABI,
    functionName: 'feeAmount',
  });
  console.log(`  Fee: ${formatEther(feeAmount)} BNB`);

  // Simulate first
  const { request } = await publicClient.simulateContract({
    account,
    address: FACTORY,
    abi: FACTORY_ABI,
    functionName: 'createToken',
    args: [
      token.symbol,
      token.name,
      token.hybridMultiplier,
      false,       // frozen
      0n,          // usdbForBonding
      1000n,       // startLP (same for all)
      false,       // autoVest
      0n,          // autoVestDuration
      false,       // gradualAutovest
    ],
    value: feeAmount,
  });

  // Execute
  const hash = await walletClient.writeContract(request);
  console.log(`  TX: ${hash}`);
  
  const receipt = await publicClient.waitForTransactionReceipt({ hash });
  console.log(`  Status: ${receipt.status}`);
  
  // Parse token address from logs (Transfer event from factory)
  const tokenCreatedLog = receipt.logs.find(log => log.topics.length > 0);
  if (receipt.logs.length > 0) {
    // The new token address is typically in the logs
    for (const log of receipt.logs) {
      if (log.address && log.address.toLowerCase() !== FACTORY.toLowerCase()) {
        console.log(`  Token address: ${log.address}`);
        return { ...token, address: log.address, hash };
      }
    }
  }
  console.log(`  Logs: ${JSON.stringify(receipt.logs.map(l => l.address))}`);
  return { ...token, hash, logs: receipt.logs };
}

async function main() {
  console.log('Creating 5 test tokens with different hybridMultiplier values...');
  console.log('All with startLP=1000, frozen=false, no bonding\n');
  
  const bnb = await publicClient.getBalance({ address: account.address });
  console.log(`Wallet BNB: ${formatEther(bnb)}`);
  
  const results = [];
  for (const token of tokens) {
    try {
      const result = await createToken(token);
      results.push(result);
      // Small delay between txs
      await new Promise(r => setTimeout(r, 3000));
    } catch (e) {
      console.log(`  ERROR: ${(e.shortMessage || e.message).slice(0, 200)}`);
      results.push({ ...token, error: e.shortMessage || e.message });
    }
  }
  
  console.log('\n=== RESULTS ===');
  for (const r of results) {
    console.log(`${r.symbol} (hybrid=${r.hybridMultiplier}): ${r.address || 'FAILED - ' + (r.error || 'unknown')}`);
  }
  
  // Save results
  fs.writeFileSync('./hybrid-test-tokens.json', JSON.stringify(results, (k, v) => typeof v === 'bigint' ? v.toString() : v, 2));
  console.log('\nSaved to hybrid-test-tokens.json');
}

main().catch(console.error);
