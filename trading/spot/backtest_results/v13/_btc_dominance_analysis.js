// BTC Dominance + CFGI Combo Signal Analysis (Node.js version)
// Tests: falling BTC dominance + rising alt CFGI = bullish for alts

const Database = require('better-sqlite3');
const DB_PATH = 'C:/Users/Never/.openclaw/workspace/trading/spot/data/candles.db';

const COINS = {
  HBAR: { candle: 'HBAR/USDT', cfgi: null },
  ATOM: { candle: 'ATOM/USDT', cfgi: 'ATOM' },
  LINK: { candle: 'LINK/USDT', cfgi: 'LINK' },
  NEAR: { candle: 'NEAR/USDT', cfgi: 'NEAR' },
};
const WINDOWS = [7, 14, 30];
const ROC_THRESHOLD = -3.0;

function mean(arr) { return arr.reduce((a,b)=>a+b,0)/arr.length; }
function median(arr) { const s=[...arr].sort((a,b)=>a-b); const m=Math.floor(s.length/2); return s.length%2?s[m]:(s[m-1]+s[m])/2; }

function forwardReturn(priceMap, dates, date, days) {
  const idx = dates.indexOf(date);
  if (idx < 0 || idx + days >= dates.length) return null;
  const p0 = priceMap[dates[idx]], p1 = priceMap[dates[idx+days]];
  return p0 > 0 ? ((p1-p0)/p0)*100 : null;
}

function dateOffset(dateStr, days) {
  const d = new Date(dateStr + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().split('T')[0];
}

function main() {
  const db = new Database(DB_PATH, { readonly: true });
  
  // Load BTC dominance
  const btcD = {};
  for (const r of db.prepare('SELECT date, dominance_pct, dominance_sma30, dominance_roc30 FROM btc_dominance ORDER BY date').all()) {
    btcD[r.date] = { dom: r.dominance_pct, sma30: r.dominance_sma30, roc30: r.dominance_roc30 };
  }
  
  // Load CFGI
  const cfgi = {};
  for (const r of db.prepare('SELECT symbol, date, cfgi FROM cfgi_daily ORDER BY date').all()) {
    if (!cfgi[r.symbol]) cfgi[r.symbol] = {};
    cfgi[r.symbol][r.date] = r.cfgi;
  }
  
  console.log('='.repeat(80));
  console.log('BTC DOMINANCE + CFGI COMBO SIGNAL ANALYSIS');
  console.log('='.repeat(80));
  
  const btcDates = Object.keys(btcD).sort();
  const domValues = btcDates.map(d => btcD[d].dom);
  const rocValues = btcDates.filter(d => btcD[d].roc30 !== null).map(d => btcD[d].roc30);
  
  console.log(`\nBTC.D data: ${btcDates[0]} to ${btcDates[btcDates.length-1]} (${btcDates.length} days)`);
  console.log(`BTC.D range: ${Math.min(...domValues).toFixed(1)}% - ${Math.max(...domValues).toFixed(1)}% (avg ${mean(domValues).toFixed(1)}%)`);
  console.log(`BTC.D ROC30 range: ${Math.min(...rocValues).toFixed(2)}% to ${Math.max(...rocValues).toFixed(2)}%`);
  const fallingDays = rocValues.filter(r => r < ROC_THRESHOLD).length;
  console.log(`Days with ROC30 < ${ROC_THRESHOLD}%: ${fallingDays}/${rocValues.length}`);
  
  for (const [coin, info] of Object.entries(COINS)) {
    console.log(`\n${'='.repeat(80)}`);
    console.log(`  ${coin}`);
    console.log('='.repeat(80));
    
    // Load prices
    const priceMap = {};
    for (const r of db.prepare('SELECT date, close FROM candles_daily WHERE symbol = ? ORDER BY date').all(info.candle)) {
      priceMap[r.date] = r.close;
    }
    const priceDates = Object.keys(priceMap).sort();
    
    if (!priceDates.length) { console.log('  No price data'); continue; }
    console.log(`  Price: ${priceDates[0]} to ${priceDates[priceDates.length-1]} (${priceDates.length} days)`);
    
    const coinCfgi = info.cfgi ? (cfgi[info.cfgi] || {}) : null;
    if (coinCfgi) console.log(`  CFGI data: ${Object.keys(coinCfgi).length} days`);
    
    // Find signal dates
    const signalDates = [], noSignalDates = [];
    
    for (const date of priceDates) {
      if (!btcD[date] || btcD[date].roc30 === null) continue;
      const roc30 = btcD[date].roc30;
      const btcFalling = roc30 < ROC_THRESHOLD;
      
      let cfgiRising = false;
      if (coinCfgi) {
        const cfgiNow = coinCfgi[date];
        const date30ago = dateOffset(date, -30);
        const cfgi30ago = coinCfgi[date30ago];
        cfgiRising = cfgiNow != null && cfgi30ago != null && cfgiNow > cfgi30ago;
      }
      
      if (coinCfgi && btcFalling && cfgiRising) {
        signalDates.push(date);
      } else {
        noSignalDates.push(date);
      }
    }
    
    if (coinCfgi) {
      console.log(`\n  COMBO signal (BTC.D ROC30 < ${ROC_THRESHOLD}% AND CFGI rising): ${signalDates.length} days`);
      console.log(`  No signal: ${noSignalDates.length} days`);
      if (signalDates.length) console.log(`  Sample signal dates: ${signalDates.slice(0,5).join(', ')}`);
      
      printTable('COMBO', signalDates, noSignalDates, priceMap, priceDates);
    }
    
    // BTC.D-only signal
    const btcSig = [], btcNoSig = [];
    for (const date of priceDates) {
      if (!btcD[date] || btcD[date].roc30 === null) continue;
      if (btcD[date].roc30 < ROC_THRESHOLD) btcSig.push(date);
      else btcNoSig.push(date);
    }
    
    console.log(`\n  BTC.D-only signal (ROC30 < ${ROC_THRESHOLD}%): ${btcSig.length} days`);
    printTable('BTC.D-only', btcSig, btcNoSig, priceMap, priceDates);
  }
  
  db.close();
}

function printTable(label, sigDates, noSigDates, priceMap, priceDates) {
  if (!sigDates.length) { console.log('  No signal dates'); return; }
  
  console.log(`\n  ${label} Forward Returns:`);
  console.log(`  ${'Window'.padStart(8)} | ${'Sig Avg'.padStart(10)} | ${'Sig Med'.padStart(10)} | ${'NoSig Avg'.padStart(10)} | ${'NoSig Med'.padStart(10)} | ${'Edge'.padStart(8)} | ${'Win%'.padStart(6)} | ${'N'.padStart(4)}`);
  console.log(`  ${'-'.repeat(8)} | ${'-'.repeat(10)} | ${'-'.repeat(10)} | ${'-'.repeat(10)} | ${'-'.repeat(10)} | ${'-'.repeat(8)} | ${'-'.repeat(6)} | ${'-'.repeat(4)}`);
  
  for (const w of WINDOWS) {
    const sigR = sigDates.map(d => forwardReturn(priceMap, priceDates, d, w)).filter(r => r !== null);
    const nosR = noSigDates.filter((_,i) => i%3===0).map(d => forwardReturn(priceMap, priceDates, d, w)).filter(r => r !== null);
    
    if (sigR.length >= 3 && nosR.length >= 3) {
      const sa = mean(sigR), sm = median(sigR);
      const na = mean(nosR), nm = median(nosR);
      const edge = sa - na;
      const wp = (sigR.filter(r => r > 0).length / sigR.length * 100);
      console.log(`  ${(w+'d').padStart(8)} | ${(sa>=0?'+':'')+sa.toFixed(2)+'%'} | ${(sm>=0?'+':'')+sm.toFixed(2)+'%'} | ${(na>=0?'+':'')+na.toFixed(2)+'%'} | ${(nm>=0?'+':'')+nm.toFixed(2)+'%'} | ${(edge>=0?'+':'')+edge.toFixed(2)+'%'} | ${wp.toFixed(1)+'%'} | ${sigR.length}`);
    } else {
      console.log(`  ${(w+'d').padStart(8)} | insufficient data (sig=${sigR.length}, nosig=${nosR.length})`);
    }
  }
}

main();
