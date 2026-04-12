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
const MAINTOKEN = client.mainTokenAddress;
const FEDCUT = '0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06';
const LVTHN = '0xFf84209eBCCAc7328070E0011e973451c4a045F9';
const fmt = (v) => formatUnits(v, 18);

// Balances
const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
const usdb = await client.publicClient.readContract({ address: client.usdbAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
console.log(`USDB: ${fmt(usdb)}`);

// Staking
const stake = await client.staking.getUserStakeDetails(wallet);
console.log(`\nwSTASIS liquid: ${fmt(stake[0])}`);
console.log(`wSTASIS locked: ${fmt(stake[1])}`);
console.log(`STASIS value: ${fmt(stake[3])}`);

// All hub loans by counting via userLoanCount (global, not per-token)
// The contract has userLoanCount(address) which returns total hub loans
const loanHubAddr = client.loans.loanHubAddress;
const loanCountAbi = [{ name: 'userLoanCount', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: '', type: 'address' }], stateMutability: 'view' }];
const totalHubLoans = await client.publicClient.readContract({ address: loanHubAddr, abi: loanCountAbi, functionName: 'userLoanCount', args: [wallet] });
console.log(`\nTotal hub loans: ${totalHubLoans}`);

// Get details for each hub loan
const now = Math.floor(Date.now() / 1000);
for (let i = 1n; i <= totalHubLoans; i++) {
  try {
    const loan = await client.loans.getUserLoanDetails(wallet, i);
    // FullLoanDetails tuple: hubId, ecosystem, coreLoanId, collateralToken, token, 
    // collateralAmount, liquidatedAmount, fullAmount, borrowedAmount, liquidationTime, 
    // liquidationClaim, isLiquidated, active, creationTime
    const collateralToken = loan[3] || loan.collateralToken;
    const collateralAmt = loan[5] || loan.collateralAmount;
    const borrowed = loan[8] || loan.borrowedAmount;
    const repay = loan[7] || loan.fullAmount;
    const liqTime = loan[9] || loan.liquidationTime;
    const active = loan[12] !== undefined ? loan[12] : loan.active;
    const daysLeft = (Number(liqTime) - now) / 86400;
    
    let tokenName = 'unknown';
    if (collateralToken?.toLowerCase() === FEDCUT.toLowerCase()) tokenName = 'FEDCUT';
    else if (collateralToken?.toLowerCase() === LVTHN.toLowerCase()) tokenName = 'LVTHN';
    else if (collateralToken?.toLowerCase() === MAINTOKEN.toLowerCase()) tokenName = 'STASIS';
    
    console.log(`  Hub ${i}: ${tokenName} | collateral=${fmt(collateralAmt)} | borrowed=${fmt(borrowed)} | repay=${fmt(repay)} | active=${active} | ${daysLeft.toFixed(1)}d left`);
  } catch (e) {
    console.log(`  Hub ${i}: error — ${e.message.substring(0, 80)}`);
  }
}

// Prices
const stasisPrice = await client.trading.getUSDPrice(MAINTOKEN);
const fedcutPrice = await client.trading.getUSDPrice(FEDCUT);
const lvthnPrice = await client.trading.getUSDPrice(LVTHN);
const lvthnFloor = await client.factory.getFloorPrice(LVTHN);
console.log(`\nPrices: STASIS=$${fmt(stasisPrice)}, FEDCUT=$${fmt(fedcutPrice)}, LVTHN=$${fmt(lvthnPrice)} (floor=$${fmt(lvthnFloor)})`);

// Profile + stats
const profile = await client.api.getMyProfile();
console.log(`\nRank: #${profile.rank} | Tier: ${profile.tier} ${profile.tierEmoji} | Streak: ${profile.streak}`);
