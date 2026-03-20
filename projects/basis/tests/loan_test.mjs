/**
 * Buy $50 STASIS then take a $25 loan — JS/TS SDK
 */
import { fileURLToPath, pathToFileURL } from 'url';
import path from 'path';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const sdkPath = pathToFileURL(path.resolve(__dirname, '..', 'basis-sdk-js', 'dist', 'index.mjs')).href;
const { BasisClient } = await import(sdkPath);

const PK = '0x062ca8b12746fdbff645cba64851d70f735a97d406c537386d606c9ce5d2b6f4';
const WALLET = '0x2D087a119271Ef50C72eC5F01183f85Ab7E74Fe2';

async function main() {
  const client = await BasisClient.create({ privateKey: PK });
  const MAIN = client.mainTokenAddress;
  const USDB = client.usdbAddress;

  // Step 1: Buy $50 of STASIS
  console.log("=== Step 1: Buy $50 STASIS ===");
  const buyResult = await client.trading.buy(MAIN, 50n * 10n**18n);
  console.log(`Buy tx: ${buyResult.hash.slice(0, 20)}...`);

  // Wait for block
  await new Promise(r => setTimeout(r, 5000));

  // Check STASIS balance
  const stasisBal = await client.publicClient.readContract({
    address: MAIN,
    abi: [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}],
    functionName: 'balanceOf',
    args: [WALLET],
  });
  console.log(`STASIS balance: ${Number(stasisBal) / 1e18}`);

  // Step 2: Take a loan — 25 STASIS collateral, 10 days
  console.log("\n=== Step 2: Take loan (25 STASIS collateral, 10 days) ===");
  try {
    const loanResult = await client.loans.takeLoan(MAIN, MAIN, 25n * 10n**18n, 10n);
    console.log(`Loan tx: ${loanResult.hash.slice(0, 20)}...`);
  } catch (e) {
    console.log(`Loan failed: ${e.message || e}`);
  }

  await new Promise(r => setTimeout(r, 3000));

  // Check loan count
  console.log("\n=== Loan Status ===");
  try {
    const count = await client.loans.getUserLoanCount(WALLET);
    console.log(`Loan count: ${count}`);

    for (let i = 0n; i < count; i++) {
      try {
        const details = await client.loans.getUserLoanDetails(WALLET, i);
        console.log(`Loan ${i}:`, details);
      } catch (e) {
        console.log(`Loan ${i}: error — ${e.message || e}`);
      }
    }
  } catch (e) {
    console.log(`Error getting loan count: ${e.message || e}`);
  }

  // Check remaining balances
  const erc20Abi = [{"inputs":[{"name":"account","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"stateMutability":"view","type":"function"}];
  const usdbBal = await client.publicClient.readContract({
    address: USDB, abi: erc20Abi, functionName: 'balanceOf', args: [WALLET],
  });
  const stasisBal2 = await client.publicClient.readContract({
    address: MAIN, abi: erc20Abi, functionName: 'balanceOf', args: [WALLET],
  });
  console.log(`\nUSDB:   ${Number(usdbBal) / 1e18}`);
  console.log(`STASIS: ${Number(stasisBal2) / 1e18}`);
}

main().catch(e => { console.error(e); process.exit(1); });
