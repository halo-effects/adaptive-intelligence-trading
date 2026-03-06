
// CONFIG
var CONFIG = {
  statusUrl: 'data/v14etf/status.json',
  tradesUrl: 'data/v14etf/trades.csv',
  scannerUrl: 'data/v14/cycle_scanner.json',
  refreshInterval: 60
};

// HELPERS
var $ = function(id){return document.getElementById(id)};
var fmt = function(n,d){d=d!=null?d:2;return n==null?'--':Number(n).toFixed(d)};
var fUsd = function(n,d){d=d!=null?d:2;return n==null?'--':'$'+Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d})};
var pC = function(v){return v>0?'var(--green)':v<0?'var(--red)':'var(--text)'};
var pDec = function(p){return p>1000?2:p>1?4:6};

var COIN_BASE = {
  SOL:{icon:'sol',label:'SOL',name:'Solana',color:'#9945FF'},
  XRP:{icon:'xrp',label:'XRP',name:'XRP',color:'#23292F'},
  LTC:{icon:'ltc',label:'LTC',name:'Litecoin',color:'#BFBBBB'},
  HBAR:{icon:'hbar',label:'HBAR',name:'Hedera',color:'#3A3A3A'},
  ADA:{icon:'ada',label:'ADA',name:'Cardano',color:'#0033AD'}
};
function cm(sym){var b=sym.split('/')[0];return COIN_BASE[b]||{icon:'sol',label:b,name:b,color:'#888'}}

var PHASE_DESC = {
  LONG_DCA:'Long grid active — buying dips, cycling TPs',
  SHORT_DCA:'Short grid active — selling rallies, cycling TPs',
  ROUTER:'Evaluating direction — waiting for signal confirmation'
};
var PHASES = ['LONG_DCA','ROUTER','SHORT_DCA'];
var REGIME_CLS = {ACCUMULATION:'rb-ACCUMULATION',ACC:'rb-ACC',TRENDING:'rb-TRENDING',TREND:'rb-TREND',RANGING:'rb-RANGING',EXTREME:'rb-EXTREME',CRASH:'rb-CRASH',CHOPPY:'rb-CHOPPY',DISTRIBUTION:'rb-DISTRIBUTION',LONG_DCA:'rb-ACC',SHORT_DCA:'rb-EXTREME',ROUTER:'rb-RANGING'};

var S=null, trades=[], eqChart=null, countdownVal=CONFIG.refreshInterval, tradePage=0, oppPage=0, scannerData=null;

function parseCSV(t){var l=t.trim().split('\n');if(l.length<2)return[];var h=l[0].split(',').map(function(x){return x.trim()});return l.slice(1).map(function(r){var v=r.split(',');var o={};h.forEach(function(k,i){o[k]=v[i]?v[i].trim():''});return o})}

async function fetchData(){
  if(CONFIG.scannerUrl){
    try{var r3=await fetch(CONFIG.scannerUrl+'?t='+Date.now());if(r3.ok){scannerData=await r3.json()}}catch(e){console.warn('scanner fetch',e)}
  }
  try{var r=await fetch(CONFIG.statusUrl+'?t='+Date.now());if(r.ok){S=await r.json();render()}}catch(e){console.warn('status fetch',e)}
  try{var r2=await fetch(CONFIG.tradesUrl+'?t='+Date.now());if(r2.ok){trades=parseCSV(await r2.text());renderTrades();renderEquityChart();try{renderCompounding()}catch(e){}try{renderStats()}catch(e){}}}catch(e){}
}

// RENDER MAIN
function render(){
  if(!S)return;

  $('statusDot').className='status-dot '+(S.running?(S.halted?'stopped':'running'):'stopped');
  $('statusLabel').textContent=S.running?(S.halted?'Halted':'Running'):'Stopped';
  $('updateTime').textContent=S.last_update?new Date(S.last_update).toLocaleString():'--';

  var rg=S.regime||'--';
  var rgClass='regime-dist';
  if(rg==='ACCUMULATION'||rg==='RANGING')rgClass='regime-acc';
  else if(rg==='EXTREME'||rg==='CRASH')rgClass='regime-ext';
  else if(rg==='DISTRIBUTION'||rg==='CHOPPY')rgClass='regime-dist';
  $('hdrRegime').className='header-badge '+rgClass;
  $('hdrRegime').textContent=rg;

  var tr=S.trend_direction||'--';
  var tCls=tr==='bullish'?'trend-bull':'trend-bear';
  var tArrow=tr==='bullish'?'\u25B2 ':tr==='bearish'?'\u25BC ':'';
  $('hdrTrend').className='header-badge '+tCls;
  $('hdrTrend').textContent=tArrow+tr.charAt(0).toUpperCase()+tr.slice(1);

  var syms=S.symbols||Object.keys(S.coins||{});
  $('hdrCoins').textContent=syms.join(', ')+' \u00B7 '+(S.timeframe||'1h');

  var fns=[renderStats,renderRiskProfile,renderPortfolioAlloc,renderPositions,renderAIPanel,renderCompounding,renderMacro,renderCapDonut,renderFlowDiagram,renderBottomBar];
  fns.forEach(function(fn){try{fn()}catch(e){console.warn(fn.name,e)}});
}

// STATS ROW
function renderStats(){
  var cap=S.capital||0, eq=S.equity||0;
  var growthPct=cap>0?((eq-cap)/cap*100):0;

  $('vEq').textContent=fUsd(eq);
  $('vEqSub').innerHTML='Capital: '+fUsd(cap)+' &middot; '+'<span style="color:'+pC(growthPct)+'">'+(growthPct>=0?'+':'')+fmt(growthPct)+'%</span>';

  var rpnl=S.total_realized_pnl||0;
  var deals=S.deals_completed||0;
  if(deals===0 && trades.length>0) deals=trades.length;
  var totalFees=S.total_fees||0;
  $('vRPnl').innerHTML='<span style="color:'+pC(rpnl)+'">'+(rpnl>=0?'+':'')+fUsd(rpnl)+'</span>';
  $('vRPnlSub').textContent=deals+' completed deals'+(totalFees>0?' · after '+fUsd(totalFees)+' fees':'');

  var syms=S.symbols||Object.keys(S.coins||{});
  var totalUpnl=0, totalInv=0;
  syms.forEach(function(sym){var c=(S.coins||{})[sym]||{};totalUpnl+=(c.unrealized_pnl||0);totalInv+=(c.invested||0)});
  var upnlPct=totalInv>0?(totalUpnl/totalInv*100):0;
  $('vUPnl').innerHTML='<span style="color:'+pC(totalUpnl)+'">'+(totalUpnl>=0?'+':'')+fUsd(totalUpnl)+'</span>';
  $('vUPnlSub').textContent=fmt(upnlPct,2)+'% on '+fUsd(totalInv)+' invested';

  var wins=0, losses=0;
  if(trades.length>0){
    trades.forEach(function(t){var p=parseFloat(t.pnl||t.PnL||0);if(p>0)wins++;else if(p!==0)losses++});
  } else {
    var dc=S.deals_completed||0, wr0=S.win_rate||0;
    wins=Math.round(dc*wr0/100);losses=dc-wins;
  }
  var totalTrades=wins+losses;
  $('vWL').innerHTML='<span style="color:var(--green)">'+wins+'W</span> / <span style="color:var(--red)">'+losses+'L</span>';
  $('vWLSub').textContent=totalTrades+' total';

  var wr=totalTrades>0?(wins/totalTrades*100):(S.win_rate||0);
  $('vWR').textContent=fmt(wr,1)+'%';
  $('vWRSub').textContent=totalTrades+' trades';

  var days=1;
  if(trades&&trades.length>0){
    var f0=new Date(trades[0].open_time);
    var now=new Date();
    days=Math.max((now-f0)/(1000*60*60*24),1);
  } else if(S.uptime_hours>24){ days=S.uptime_hours/24; }
  var dailyRoi=growthPct/days;
  $('vROI').innerHTML='<span style="color:'+pC(dailyRoi)+'">'+(dailyRoi>=0?'+':'')+fmt(dailyRoi,3)+'%</span>';
  $('vROISub').textContent='on '+fUsd(cap)+' capital';
}

// RISK PROFILE & REGIME
function renderRiskProfile(){
  var profile=(S.profile||'medium').toLowerCase();
  var badgeCls=profile==='low'?'low':profile==='high'?'high':'medium';
  var rg=S.regime||'--';
  var tr=S.trend_direction||'--';
  var tArr=tr==='bullish'?'\u25B2':tr==='bearish'?'\u25BC':'\u2014';
  var tCol=tr==='bullish'?'var(--green)':tr==='bearish'?'var(--red)':'var(--text2)';
  var rgDesc={ACCUMULATION:'Low-volatility accumulation phase - tight grid spacing, frequent captures',DISTRIBUTION:'Distribution detected - preparing to exit positions',TRENDING:'Strong directional trend - wider parameters, trailing stops active',RANGING:'Range-bound market - ideal conditions for grid trading',CHOPPY:'Noisy price action - cautious position sizing',EXTREME:'Extreme volatility - capital protection mode engaged'};

  $('riskGrid').innerHTML=
    '<div class="risk-col">'+
      '<h3>Risk Profile</h3>'+
      '<div class="risk-badge '+badgeCls+'">'+profile.toUpperCase()+'</div>'+
      '<div class="risk-params">'+
        '<div class="risk-param"><div class="rp-label">BO</div><div class="rp-val">40%</div></div>'+
        '<div class="risk-param"><div class="rp-label">DEV</div><div class="rp-val">'+(profile==='high'?'1.5%':'2.0%')+'</div></div>'+
        '<div class="risk-param"><div class="rp-label">LAYERS</div><div class="rp-val">'+(profile==='high'?'12':'10')+'</div></div>'+
        '<div class="risk-param"><div class="rp-label">TP</div><div class="rp-val">1.5%</div></div>'+
        '<div class="risk-param"><div class="rp-label">MULT</div><div class="rp-val">1.5&times;</div></div>'+
        '<div class="risk-param"><div class="rp-label">LEVERAGE</div><div class="rp-val">'+(profile==='low'?'1.0&times;':'1.5&times;')+'</div></div>'+
      '</div>'+
    '</div>'+
    '<div class="risk-col" style="text-align:center;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;padding:24px 20px">'+
      '<div style="font-size:.75rem;text-transform:uppercase;letter-spacing:1.5px;color:var(--text3);font-weight:600">Market Conditions</div>'+
      '<span class="regime-badge '+(REGIME_CLS[rg]||'')+'" style="font-size:1.1rem;padding:10px 28px;font-weight:700;letter-spacing:1px">'+rg+'</span>'+
      '<div class="regime-desc" style="margin:0;font-size:.95rem;color:var(--text2);max-width:280px;line-height:1.5">'+(rgDesc[rg]||'Analyzing market conditions...')+'</div>'+
      '<div style="display:flex;align-items:center;gap:10px;color:'+tCol+';margin-top:4px"><span style="font-size:2rem">'+tArr+'</span><span style="font-size:1.15rem;font-weight:700">'+tr.charAt(0).toUpperCase()+tr.slice(1)+' Trend</span></div>'+
    '</div>';
}

// PORTFOLIO ALLOCATION
function renderPortfolioAlloc(){
  var syms=S.symbols||Object.keys(S.coins||{});
  var eq=S.equity||0;
  var items=[];
  var totalInv=0;
  syms.forEach(function(sym){
    var c=(S.coins||{})[sym]||{};
    var m=cm(sym);
    var inv=c.invested||0;
    totalInv+=inv;
    items.push({name:m.label,inv:inv,pnl:c.unrealized_pnl||0,color:m.color});
  });
  var cash=Math.max((S.cash||0),eq-totalInv,0);
  items.push({name:'Cash',inv:cash,pnl:0,color:'#666'});
  var total=items.reduce(function(a,i){return a+i.inv},0)||1;

  var r=80,cx=100,cy=100,sw=28;
  var angle=-90,paths='';
  items.forEach(function(item){
    var pct=item.inv/total;
    if(pct<0.001)return;
    var sweep=pct*360;
    var rad=function(n){return n*Math.PI/180};
    var x1=cx+r*Math.cos(rad(angle)),y1=cy+r*Math.sin(rad(angle));
    var x2=cx+r*Math.cos(rad(angle+sweep)),y2=cy+r*Math.sin(rad(angle+sweep));
    var large=sweep>180?1:0;
    paths+='<path d="M'+x1+','+y1+' A'+r+','+r+' 0 '+large+',1 '+x2+','+y2+'" stroke="'+item.color+'" stroke-width="'+sw+'" fill="none"/>';
    angle+=sweep;
  });

  var tableRows=items.map(function(i){
    var pct=(i.inv/total*100);
    return '<tr><td><span class="alloc-dot" style="background:'+i.color+'"></span>'+i.name+'</td><td>'+fmt(pct,1)+'%</td><td>'+fUsd(i.inv)+'</td><td style="color:'+pC(i.pnl)+'">'+(i.pnl!==0?(i.pnl>0?'+':'')+fUsd(i.pnl):'--')+'</td></tr>';
  }).join('');

  $('allocInner').innerHTML=
    '<div class="alloc-donut" style="position:relative;width:200px;height:200px">'+
      '<svg width="200" height="200" viewBox="0 0 200 200">'+paths+'</svg>'+
      '<div class="alloc-center"><div class="ac-val">'+fUsd(eq)+'</div><div class="ac-lbl">Total Equity</div></div>'+
    '</div>'+
    '<div class="alloc-table"><table><thead><tr><th>Asset</th><th>Alloc</th><th>Value</th><th>PnL</th></tr></thead><tbody>'+tableRows+'</tbody></table></div>';
}

// POSITIONS
function renderPositions(){
  var syms=S.symbols||Object.keys(S.coins||{});
  var html='';
  syms.forEach(function(sym){
    var c=(S.coins||{})[sym]||{};
    var m=cm(sym);
    var phase=c.lifecycle_phase||c.state||'ROUTER';
    var side=(c.side||'long').toLowerCase();
    if(phase==='SHORT_DCA') side='short';
    else if(phase==='LONG_DCA') side='long';
    var pd_=pDec(c.current_price||0);

    var price=c.current_price||0;
    var entry=c.avg_entry||0;
    var tp=c.next_tp_price||0;
    var inv=c.invested||0;
    var upnl=c.unrealized_pnl||0;
    var rpnl=c.realized_pnl||0;
    var layers=c.layers||0;
    var maxLayers=10;

    html+='<div class="position-card">';
    html+='<div class="position-head"><div class="position-head-left">';
    html+='<div class="coin-icon '+m.icon+'" style="width:32px;height:32px;font-size:.7rem">'+m.label+'</div>';
    html+='<span style="font-weight:700;font-size:1rem">'+m.name+'</span>';
    html+='<span class="dir-badge '+side+'">'+side.toUpperCase()+'</span>';
    html+='</div>';
    html+='<span class="pb pb-'+phase+'">'+phase.replace('_',' ')+'</span>';
    html+='</div>';

    // Stats
    html+='<div class="position-stats">';
    html+='<div class="position-stat"><div class="ps-label">Current Price</div><div class="ps-val">'+fUsd(price,pd_)+'</div></div>';
    html+='<div class="position-stat"><div class="ps-label">Avg Entry</div><div class="ps-val">'+fUsd(entry,pd_)+'</div></div>';
    html+='<div class="position-stat"><div class="ps-label">Invested</div><div class="ps-val">'+fUsd(inv)+'</div></div>';
    html+='<div class="position-stat"><div class="ps-label">Grid Layers</div><div class="ps-val">'+layers+' / '+maxLayers+'</div></div>';
    html+='<div class="position-stat"><div class="ps-label">TP Target</div><div class="ps-val" style="color:var(--green)">'+fUsd(tp,pd_)+'</div></div>';
    var liqPrice=c.liquidation_price||null;
    var liqDist=c.distance_to_liq_pct||null;
    html+='<div class="position-stat"><div class="ps-label">Liquidation</div><div class="ps-val" style="color:var(--red)">'+(liqPrice?fUsd(liqPrice,pd_):'N/A')+'</div></div>';
    html+='<div class="position-stat"><div class="ps-label">Dist to Liq</div><div class="ps-val" style="color:'+(liqDist!=null&&liqDist<20?'var(--amber)':'var(--text2)')+'">'+(liqDist!=null?fmt(liqDist,1)+'%':'N/A')+'</div></div>';
    html+='<div class="position-stat"><div class="ps-label">Unrealized PnL</div><div class="ps-val" style="color:'+pC(upnl)+'">'+(upnl>=0?'+':'')+fUsd(upnl)+'</div></div>';
    html+='<div class="position-stat"><div class="ps-label">Realized PnL</div><div class="ps-val" style="color:'+pC(rpnl)+'">'+(rpnl>=0?'+':'')+fUsd(rpnl)+'</div></div>';
    var netVal=inv+upnl;
    html+='<div class="position-stat"><div class="ps-label">Net Value</div><div class="ps-val" style="color:'+pC(netVal-inv)+'">'+fUsd(netVal)+'</div></div>';
    html+='</div>';

    // Grid depth bar
    if(layers>0){
      var gridPct=Math.min(layers/maxLayers*100,100);
      html+='<div style="margin-top:8px"><div style="display:flex;justify-content:space-between;font-size:.65rem;color:var(--text3);margin-bottom:4px"><span>Grid Depth</span><span>'+layers+'/'+maxLayers+' layers</span></div>';
      html+='<div class="meter-bar"><div class="meter-fill" style="width:'+gridPct+'%;background:'+(phase==='LONG_DCA'?'var(--green)':phase==='SHORT_DCA'?'var(--red)':'var(--accent)')+'"></div></div></div>';
    }

    // Price position bar
    if(entry>0&&price>0){
      var pts=[price,entry];
      if(tp>0)pts.push(tp);
      if(liqPrice)pts.push(liqPrice);
      var mn=Math.min.apply(null,pts), mx=Math.max.apply(null,pts);
      var rng=mx-mn||1;
      var pctOf=function(v){return Math.max(2,Math.min(98,((v-mn)/rng)*100))};

      html+='<div class="price-bar" style="margin-top:10px">';
      html+='<div class="price-bar-fill" style="width:'+pctOf(price)+'%"></div>';
      if(liqPrice)html+='<div class="pb-dot so" style="left:'+pctOf(liqPrice)+'%;background:var(--red)"><div class="pb-label" style="color:var(--red)">Liq</div></div>';
      if(tp>0)html+='<div class="pb-dot tp" style="left:'+pctOf(tp)+'%"><div class="pb-label">TP</div></div>';
      html+='<div class="pb-dot current" style="left:'+pctOf(price)+'%"><div class="pb-label" style="color:var(--accent)">Now</div></div>';
      html+='</div>';
    }

    html+='</div>';
  });
  $('positionsGrid').innerHTML=html||'<div style="color:var(--text3);text-align:center;padding:40px">No positions</div>';
}

// ADAPTIVE INTELLIGENCE (Per-Coin)
function renderAIPanel(){
  var syms=S.symbols||Object.keys(S.coins||{});
  var html='';

  syms.forEach(function(sym){
    var c=(S.coins||{})[sym]||{};
    var m=cm(sym);
    var phase=c.lifecycle_phase||c.state||'ROUTER';
    var cfgi=c.cfgi!=null?c.cfgi:null;
    var cfgiCol=cfgi!=null?(cfgi<=25?'var(--red)':cfgi<=45?'var(--amber)':cfgi<=55?'var(--text2)':'var(--green)'):'var(--text3)';
    var layers=c.layers||0;
    var maxLayers=10;
    var gridPct=Math.min(layers/maxLayers*100,100);
    var side=(phase==='SHORT_DCA')?'short':'long';
    var dirText=side==='long'?'LONG \u25B2':'SHORT \u25BC';
    var dirCol=side==='long'?'var(--green)':'var(--red)';

    // Top detection and conviction status
    var topStatus=phase==='SHORT_DCA'?'fired':(phase==='ROUTER'?'armed':'monitoring');
    var convictionStatus=phase==='LONG_DCA'?'fired':(phase==='ROUTER'?'pending':'monitoring');

    html+='<div class="ai-coin-card">';
    html+='<div class="ai-coin-head">';
    html+='<div class="ai-coin-name"><div class="coin-icon '+m.icon+'" style="width:28px;height:28px;font-size:.6rem">'+m.label+'</div>'+m.name+'</div>';
    html+='<span class="pb pb-'+phase+'" style="font-size:.6rem;padding:3px 8px">'+phase.replace('_',' ')+'</span>';
    html+='</div>';

    // Direction
    html+='<div style="margin-bottom:10px;font-size:.85rem;font-weight:700;color:'+dirCol+'">'+dirText+'</div>';

    // Grid depth
    html+='<div style="margin-bottom:10px"><div class="meter-hdr"><span class="meter-title">Grid Depth</span><span class="meter-val">Layer '+layers+'/'+maxLayers+'</span></div>';
    html+='<div class="meter-bar"><div class="meter-fill" style="width:'+gridPct+'%;background:'+(phase==='LONG_DCA'?'var(--green)':phase==='SHORT_DCA'?'var(--red)':'var(--accent)')+'"></div></div></div>';

    // CFGI
    if(cfgi!=null){
      html+='<div style="margin-bottom:10px"><div class="meter-hdr"><span class="meter-title">CFGI</span><span class="meter-val" style="color:'+cfgiCol+'">'+cfgi+'</span></div>';
      html+='<div class="meter-bar"><div class="meter-fill" style="width:'+cfgi+'%;background:'+cfgiCol+'"></div></div>';
      html+='<div class="meter-note"><span>Fear</span><span>Greed</span></div></div>';
    }

    // Top Detection & Conviction
    html+='<div style="display:flex;gap:8px;flex-wrap:wrap">';
    html+='<span class="status-indicator '+topStatus+'">Top Detection: '+topStatus.charAt(0).toUpperCase()+topStatus.slice(1)+'</span>';
    html+='<span class="status-indicator '+convictionStatus+'">Conviction: '+convictionStatus.charAt(0).toUpperCase()+convictionStatus.slice(1)+'</span>';
    html+='</div>';

    html+='</div>';
  });

  $('aiGrid').innerHTML=html||'<div style="color:var(--text3);padding:20px;text-align:center">No AI data</div>';
}

// COMPOUNDING TRACKER
function renderCompounding(){
  var cap=S.capital||10000, eq=S.equity||cap;
  var rpnl=0, deals=0, wins=0;
  if(trades.length>0){
    trades.forEach(function(t){var p=parseFloat(t.pnl||t.PnL||0);rpnl+=p;deals++;if(p>0)wins++});
  } else {
    rpnl=S.total_realized_pnl||0;
    deals=S.deals_completed||0;
    wins=Math.round(deals*(S.win_rate||0)/100);
  }
  var wr=deals>0?(wins/deals*100):0;
  var growth=cap>0?((eq-cap)/cap*100):0;
  var days=1;
  if(trades&&trades.length>1){
    var first=new Date(trades[0].open_time);
    var last=new Date(trades[trades.length-1].close_time||trades[trades.length-1].open_time);
    days=Math.max((last-first)/(1000*60*60*24),1);
  } else if(S.uptime_hours>24){ days=S.uptime_hours/24; }
  var dailyRate=rpnl/days;
  var monthlyProj=dailyRate*30;
  var dailyPct=cap>0?(dailyRate/cap):0;
  var annualProj=dailyPct>0&&dailyPct<0.1?cap*(Math.pow(1+dailyPct,365)-1):dailyRate*365;

  $('compCards').innerHTML=
    '<div class="comp-card"><div class="cc-lbl">Starting Capital</div><div class="cc-val">'+fUsd(cap)+'</div></div>'+
    '<div class="comp-card"><div class="cc-lbl">Current Equity</div><div class="cc-val" style="color:'+pC(eq-cap)+'">'+fUsd(eq)+'</div></div>'+
    '<div class="comp-card"><div class="cc-lbl">Growth</div><div class="cc-val" style="color:'+pC(growth)+'">'+(growth>=0?'+':'')+fmt(growth)+'%</div></div>'+
    '<div class="comp-card"><div class="cc-lbl">Deals / Win Rate</div><div class="cc-val">'+deals+'</div><div class="cc-sub">'+fmt(wr,1)+'% win rate</div></div>';

  var milestones=[25000,50000,100000,250000,500000,1000000];
  var target=cap*2;
  for(var mi=0;mi<milestones.length;mi++){if(milestones[mi]>eq){target=milestones[mi];break}}
  var fillPct=Math.min(Math.max((eq/target)*100,0),100);
  $('compFill').style.width=fillPct+'%';
  $('compStart').textContent=fUsd(cap);
  $('compTarget').textContent='Next: '+fUsd(target);

  $('projCards').innerHTML=
    '<div class="proj-card"><div class="pj-lbl">Daily Rate</div><div class="pj-val">'+fUsd(dailyRate)+'</div><div class="pj-sub">'+fmt(cap>0?(dailyRate/cap*100):0,3)+'% / day</div></div>'+
    '<div class="proj-card"><div class="pj-lbl">Monthly Projection</div><div class="pj-val">'+fUsd(monthlyProj)+'</div><div class="pj-sub">Based on '+fmt(days,0)+' days data</div></div>'+
    '<div class="proj-card"><div class="pj-lbl">Annual Projection</div><div class="pj-val">'+fUsd(annualProj)+'</div><div class="pj-sub">Compound estimate</div></div>';
}

// MACRO INDICATORS
function renderMacro(){
  var fgi=S.fear_greed_index!=null?S.fear_greed_index:null;
  var fgiVal=fgi!=null?fgi:'--';
  var fgiLabel=fgi!=null?(fgi<=20?'Extreme Fear':fgi<=40?'Fear':fgi<=60?'Neutral':fgi<=80?'Greed':'Extreme Greed'):'--';
  var fgiCol=fgi!=null?(fgi<=20?'var(--red)':fgi<=40?'var(--amber)':fgi<=60?'var(--text2)':'var(--green)'):'var(--text2)';

  var syms=S.symbols||[];
  var cfgiHtml='';
  var hasCfgi=false;
  syms.forEach(function(sym){
    var c=(S.coins||{})[sym]||{};
    if(c.cfgi!=null){hasCfgi=true;var base=sym.split('/')[0];var cv=c.cfgi;var cc=cv<=25?'var(--red)':cv<=45?'var(--amber)':cv<=55?'var(--text2)':'var(--green)';cfgiHtml+='<div style="margin:4px 0"><span style="font-weight:600">'+base+':</span> <span style="color:'+cc+';font-weight:700;font-size:1.1rem">'+cv+'</span></div>'}
  });
  if(!hasCfgi)cfgiHtml='<div class="mc-val" style="color:var(--text3)">--</div><div style="font-size:.7rem;color:var(--text3)">Not yet available</div>';

  // Sentiment Gates
  var gateHtml='';
  var symsGate=S.symbols||[];
  var hasGateData=false;
  symsGate.forEach(function(sym){
    var c=(S.coins||{})[sym]||{};
    var phase=c.lifecycle_phase||c.state||'ROUTER';
    var base=sym.split('/')[0];
    var phaseCol=phase==='LONG_DCA'?'var(--green)':phase==='SHORT_DCA'?'var(--red)':'var(--accent2)';
    gateHtml+='<div style="margin:6px 0"><span style="font-weight:600">'+base+':</span> <span style="color:'+phaseCol+';font-weight:700">'+phase.replace('_',' ')+'</span></div>';
    hasGateData=true;
  });
  if(!hasGateData)gateHtml='<div class="mc-val" style="color:var(--text3)">Monitoring</div>';

  $('macroGrid').innerHTML=
    '<div class="macro-card"><div class="mc-title">Fear &amp; Greed Index</div><div class="mc-val" style="color:'+fgiCol+'">'+fgiVal+'</div><div class="mc-label" style="color:'+fgiCol+'">'+fgiLabel+'</div><div class="fg-bar">'+(fgi!=null?'<div class="fg-dot" style="left:'+fgi+'%"></div>':'')+'</div><div class="fg-labels"><span>Extreme Fear</span><span>Neutral</span><span>Extreme Greed</span></div></div>'+
    '<div class="macro-card"><div class="mc-title">Coin Sentiment</div>'+cfgiHtml+'</div>'+
    '<div class="macro-card"><div class="mc-title">Phase Status</div>'+gateHtml+'</div>';
}

// CAP DONUT
function renderCapDonut(){
  var syms=S.symbols||Object.keys(S.coins||{});
  var longInv=0, shortInv=0;
  syms.forEach(function(sym){
    var c=(S.coins||{})[sym]||{};
    var phase=c.lifecycle_phase||c.state||'ROUTER';
    if(phase==='LONG_DCA')longInv+=(c.invested||0);
    else if(phase==='SHORT_DCA')shortInv+=(c.invested||0);
  });
  var cash=S.cash||0;
  var total=longInv+shortInv+cash||1;
  var utilPct=((total-cash)/total*100);

  var legs=[
    {label:'Long DCA Invested',val:longInv,color:'var(--green)',hex:'#22c55e'},
    {label:'Short DCA Invested',val:shortInv,color:'var(--red)',hex:'#ef4444'},
    {label:'Cash Reserve',val:cash,color:'var(--text3)',hex:'#1e1e2e'}
  ];
  $('capLegend').innerHTML='<div style="font-size:.8rem;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">Utilization</div><div style="font-size:2.5rem;font-weight:700;margin-bottom:12px;color:'+(utilPct>80?'var(--green)':utilPct>40?'var(--amber)':'var(--text)')+'">'+fmt(utilPct,1)+'%</div>'+legs.map(function(l){return '<div style="display:flex;align-items:center;gap:10px;font-size:.88rem;color:var(--text2);margin-bottom:4px"><span style="width:14px;height:14px;border-radius:50%;flex-shrink:0;background:'+l.color+'"></span>'+l.label+'<span style="margin-left:auto;font-weight:600;font-size:.95rem;color:var(--text)">'+fUsd(l.val)+'</span></div>'}).join('');

  var cvs=$('capDonut'),ctx=cvs.getContext('2d');
  var dpr=window.devicePixelRatio||1,sz=200;
  cvs.width=sz*dpr;cvs.height=sz*dpr;cvs.style.width=sz+'px';cvs.style.height=sz+'px';
  ctx.scale(dpr,dpr);
  var cx2=sz/2,cy2=sz/2,r2=72,lw2=22;
  ctx.clearRect(0,0,sz,sz);
  ctx.beginPath();ctx.arc(cx2,cy2,r2,0,Math.PI*2);ctx.strokeStyle='#1e1e2e';ctx.lineWidth=lw2;ctx.stroke();
  var segs=legs.filter(function(l){return l.val>0});
  var angle2=-Math.PI/2;
  segs.forEach(function(s){
    var sweep=(s.val/total)*Math.PI*2;
    if(sweep<0.01)return;
    ctx.beginPath();ctx.arc(cx2,cy2,r2,angle2,angle2+sweep);
    ctx.strokeStyle=s.hex;ctx.lineWidth=lw2;ctx.lineCap='butt';ctx.stroke();
    angle2+=sweep;
  });
  ctx.fillStyle='#e2e8f0';ctx.font='bold 28px Inter,system-ui';ctx.textAlign='center';ctx.textBaseline='middle';
  ctx.fillText(fmt(utilPct,0)+'%',cx2,cy2);
}

// PHASE FLOW DIAGRAM + OPPORTUNITY TABLE
function renderFlowDiagram(){
  var activeSyms=S.symbols||Object.keys(S.coins||{});

  // Phase flow diagram - 3 phases
  var phaseCoinMap={LONG_DCA:[],ROUTER:[],SHORT_DCA:[]};
  activeSyms.forEach(function(sym){
    var c=(S.coins||{})[sym]||{};
    var phase=c.lifecycle_phase||c.state||'ROUTER';
    if(phaseCoinMap[phase])phaseCoinMap[phase].push(sym);
  });

  var flowHtml='';
  var flowNodes=[
    {phase:'LONG_DCA',label:'LONG DCA',desc:'Buying dips, cycling TPs',trigger:'Bottom conviction'},
    {phase:'ROUTER',label:'ROUTER',desc:'Evaluating direction',trigger:''},
    {phase:'SHORT_DCA',label:'SHORT DCA',desc:'Selling rallies, cycling TPs',trigger:'Top signals'}
  ];
  flowNodes.forEach(function(fn,i){
    var hasActive=phaseCoinMap[fn.phase]&&phaseCoinMap[fn.phase].length>0;
    flowHtml+='<div class="pf-node">';
    flowHtml+='<div class="pf-circle '+fn.phase+(hasActive?' active':'')+'">'+fn.label.replace(' ','<br>')+'</div>';
    flowHtml+='<div class="pf-label">'+fn.label+'</div>';
    flowHtml+='<div class="pf-desc">'+fn.desc+'</div>';
    if(fn.trigger)flowHtml+='<div style="font-size:.55rem;color:var(--text3);margin-top:2px;font-style:italic">\u2191 '+fn.trigger+'</div>';
    // Coin dots
    if(phaseCoinMap[fn.phase]&&phaseCoinMap[fn.phase].length>0){
      flowHtml+='<div class="pf-coins">';
      phaseCoinMap[fn.phase].forEach(function(sym){
        var m=cm(sym);
        flowHtml+='<div class="fc-dot '+m.icon+'">'+m.label.charAt(0)+'</div>';
      });
      flowHtml+='</div>';
    }
    flowHtml+='</div>';
    if(i<flowNodes.length-1)flowHtml+='<div class="pf-arrow">\u2194</div>';
  });
  $('phaseFlow').innerHTML=flowHtml;

  // Opportunity table
  var selectedWindow=$('scanWindow')?$('scanWindow').value:'30d';
  var scanWindow=scannerData&&scannerData.windows&&scannerData.windows[selectedWindow];
  var scanCoins=scanWindow&&scanWindow.rankings||[];

  // Top picks summary
  var tpEl=$('topPicksSummary');
  if(tpEl&&scannerData&&scannerData.top_picks){
    var tp=scannerData.top_picks;
    function findCoinScore(coin,field){var v='';scanCoins.forEach(function(sc){if(sc.coin===coin&&sc[field]!=null)v=sc[field]});return v}
    var tpParts=[];
    if(tp.best_score)tpParts.push('\uD83C\uDFC6 Best: '+tp.best_score+' ('+findCoinScore(tp.best_score,'dca_score')+')');
    if(tp.fastest_cycler)tpParts.push('\u26A1 Fastest: '+tp.fastest_cycler+' ('+findCoinScore(tp.fastest_cycler,'deals_per_week')+'/wk)');
    if(tp.lowest_dd)tpParts.push('\uD83D\uDEE1\uFE0F Lowest DD: '+tp.lowest_dd+' ('+findCoinScore(tp.lowest_dd,'max_drawdown_pct')+'%)');
    if(tp.most_capital_free){var cfVal=findCoinScore(tp.most_capital_free,'capital_freedom');tpParts.push('\uD83D\uDCB0 Most Free: '+tp.most_capital_free+' ('+(cfVal?Math.round(cfVal*100)+'%':'')+')');} 
    tpEl.innerHTML=tpParts.join(' &nbsp;|&nbsp; ');
    tpEl.style.display=tpParts.length?'block':'none';
  }else if(tpEl){tpEl.style.display='none'}

  // Scanner timestamp
  var tsEl=$('scanTimestamp');
  if(tsEl&&scannerData&&scannerData.generated_at){
    var genTime=new Date(scannerData.generated_at);
    var agoMs=Date.now()-genTime.getTime();
    var agoMin=Math.round(agoMs/60000);
    var agoStr=agoMin<60?agoMin+'m ago':Math.round(agoMin/60)+'h ago';
    tsEl.textContent='Scanner: '+agoStr;
  }

  var allSyms=[];
  activeSyms.forEach(function(s){ allSyms.push(s) });
  scanCoins.forEach(function(c){
    var sym=c.symbol;
    if(allSyms.indexOf(sym)===-1) allSyms.push(sym);
  });
  var syms=allSyms.length>0?allSyms:activeSyms;

  var phaseColors={LONG_DCA:'var(--phase-long-dca)',SHORT_DCA:'var(--phase-short-dca)',ROUTER:'var(--phase-router)'};

  function dcaGrade(s){
    if(s==null)return{letter:'--',color:'var(--text3)'};
    if(s>=30)return{letter:'S',color:'var(--green)'};
    if(s>=15)return{letter:'A',color:'var(--green)'};
    if(s>=8)return{letter:'B',color:'#22d3ee'};
    if(s>=4)return{letter:'C',color:'var(--amber)'};
    return{letter:'D',color:'var(--red)'};
  }
  function scoreColor(v){return v>10?'var(--green)':v>=5?'var(--amber)':'var(--red)'}
  function capColor(v){return v>0.7?'var(--green)':v>=0.5?'var(--amber)':'var(--red)'}
  function ddColor(v){return v<30?'var(--green)':v<=45?'var(--amber)':'var(--red)'}

  var rowData=[];
  syms.forEach(function(sym){
    var c=(S.coins||{})[sym]||{};
    var m=cm(sym);
    var isActive=activeSyms.indexOf(sym)!==-1;
    var phase=isActive?(c.lifecycle_phase||c.state||'ROUTER'):'--';

    var scanCoinData=null;
    scanCoins.forEach(function(sc){if(sc.symbol===sym||sc.coin===sym.split('/')[0])scanCoinData=sc});

    var dcaScore=scanCoinData?scanCoinData.dca_score:null;
    var dealsWk=scanCoinData?scanCoinData.deals_per_week:null;
    var avgCycle=scanCoinData?scanCoinData.avg_cycle_hours:null;
    var capFree=scanCoinData?scanCoinData.capital_freedom:null;
    var ddPct=scanCoinData?scanCoinData.max_drawdown_pct:null;

    var trendData=null;
    var coinKey=sym.split('/')[0];
    if(scannerData&&scannerData.trend_scores&&scannerData.trend_scores[coinKey]){trendData=scannerData.trend_scores[coinKey]}

    rowData.push({sym:sym,m:m,isActive:isActive,phase:phase,dcaScore:dcaScore,dealsWk:dealsWk,avgCycle:avgCycle,capFree:capFree,ddPct:ddPct,trend:trendData});
  });

  rowData.sort(function(a,b){
    var as=a.dcaScore!=null?a.dcaScore:-999;
    var bs=b.dcaScore!=null?b.dcaScore:-999;
    return bs-as;
  });

  var h='';
  rowData.forEach(function(rd){
    var phaseHtml=rd.phase==='--'?'<span class="phase-pill" style="background:rgba(99,102,241,.1);color:var(--text3)"><span class="pd" style="background:var(--text3)"></span>Scanner</span>':'<span class="phase-pill"><span class="pd" style="background:'+(phaseColors[rd.phase]||'var(--text3)')+'"></span>'+rd.phase.replace('_',' ')+'</span>';

    var g=dcaGrade(rd.dcaScore);
    var scoreHtml=rd.dcaScore!=null?'<span style="font-weight:800;font-size:1.05rem;color:'+scoreColor(rd.dcaScore)+'">'+rd.dcaScore.toFixed(1)+'</span> <span style="font-size:.7rem;color:'+g.color+'">'+g.letter+'</span>':'<span style="color:var(--text3)">--</span>';

    var dealsHtml=rd.dealsWk!=null?rd.dealsWk.toFixed(1):'--';
    var cycleHtml=rd.avgCycle!=null?rd.avgCycle.toFixed(1)+'h':'--';
    var capHtml=rd.capFree!=null?'<span style="color:'+capColor(rd.capFree)+'">'+Math.round(rd.capFree*100)+'%</span>':'--';
    var ddHtml=rd.ddPct!=null?'<span style="color:'+ddColor(rd.ddPct)+'">'+rd.ddPct.toFixed(1)+'%</span>':'--';

    h+='<tr'+(rd.isActive?' style="background:rgba(99,102,241,.06)"':'')+'>';
    h+='<td class="coin-name">'+rd.m.label+(rd.isActive?' <span style="font-size:.55rem;color:var(--accent2);vertical-align:middle">ACTIVE</span>':'')+'</td>';
    h+='<td>'+phaseHtml+'</td>';
    h+='<td style="text-align:center">'+scoreHtml+'</td>';
    var trendHtml='<span style="color:var(--text3)">--</span>';
    if(rd.trend){var td=rd.trend;var tdir=td.direction;var tmult=td.trend_multiplier;if(tdir==='accelerating'){trendHtml='<span style="color:var(--profit);font-size:1.2rem" title="Score accelerating (''+tmult.toFixed(2)+''x)">&#x2197;</span>'}else if(tdir==='declining'){trendHtml='<span style="color:var(--loss);font-size:1.2rem" title="Score declining (''+tmult.toFixed(2)+''x)">&#x2198;</span>'}else{trendHtml='<span style="color:var(--text2);font-size:1.2rem" title="Score stable (''+tmult.toFixed(2)+''x)">&#x2192;</span>'}}
    h+='<td style="text-align:center">'+trendHtml+'</td>';
    h+='<td style="text-align:center">'+dealsHtml+'</td>';
    h+='<td style="text-align:center">'+cycleHtml+'</td>';
    h+='<td style="text-align:center">'+capHtml+'</td>';
    h+='<td style="text-align:center">'+ddHtml+'</td>';
    h+='</tr>';
  });

  // Pagination
  var oppRows=h?h.match(/<tr[\s\S]*?<\/tr>/g):[];
  var ops=parseInt($('oppPageSize').value)||10;
  var oppMaxPage=Math.max(0,Math.ceil(oppRows.length/ops)-1);
  oppPage=Math.min(oppPage,oppMaxPage);
  var oppPageRows=oppRows.slice(oppPage*ops,(oppPage+1)*ops);
  $('oppBody').innerHTML=oppPageRows.length?oppPageRows.join(''):'<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:30px">No coin data</td></tr>';
  if(oppRows.length>ops){
    $('oppPagBar').style.display='flex';
    $('oppPagInfo').textContent='Page '+(oppPage+1)+' of '+(oppMaxPage+1);
    $('oppPagPrev').disabled=oppPage===0;
    $('oppPagNext').disabled=oppPage>=oppMaxPage;
  }else{$('oppPagBar').style.display='none'}
}

// TRADES
function renderTrades(){
  var empty=$('tradeEmpty'), pagB=$('pagBar');
  if(!trades.length){$('tradeBody').innerHTML='';empty.style.display='block';pagB.style.display='none';$('tradeCount').textContent='';return}
  empty.style.display='none';pagB.style.display='flex';
  var ps=parseInt($('pageSize').value)||25;
  var total=trades.length;
  var maxPage=Math.max(0,Math.ceil(total/ps)-1);
  tradePage=Math.min(tradePage,maxPage);
  var rev=trades.slice().reverse();
  var page=rev.slice(tradePage*ps,(tradePage+1)*ps);
  $('tradeCount').textContent='('+total+' total)';
  $('pagInfo').textContent='Page '+(tradePage+1)+' of '+(maxPage+1);
  $('pagPrev').disabled=tradePage===0;
  $('pagNext').disabled=tradePage>=maxPage;

  $('tradeBody').innerHTML=page.map(function(t){
    var pnl=parseFloat(t.pnl||t.PnL||0);
    var cls=pnl>0?'pnl-pos':pnl<0?'pnl-neg':'';
    var time=t.close_time||t.timestamp||t.time||'--';
    var sym=t.symbol||t.Symbol||'--';
    var layers=t.layers||'--';
    var invested=parseFloat(t.invested||0);
    var regime=t.regime||t.Regime||'--';
    var ret=t.return_pct||t.ReturnPct||'--';
    var dur=t.duration_h||t.duration||'--';
    if(dur!=='--')dur=parseFloat(dur).toFixed(1)+'h';
    return '<tr><td>'+(time!=='--'?new Date(time).toLocaleString():'--')+'</td><td><strong>'+sym+'</strong></td><td>'+layers+'</td><td>'+(invested>0?fUsd(invested):'--')+'</td><td class="'+cls+'">'+(pnl!==0?(pnl>0?'+':'')+fUsd(pnl):'--')+'</td><td>'+(ret!=='--'?ret+'%':'--')+'</td><td>'+dur+'</td><td>'+(regime!=='--'?'<span class="regime-badge '+(REGIME_CLS[regime]||'')+'">'+regime+'</span>':'--')+'</td></tr>';
  }).join('');
}

// Pagination
document.addEventListener('DOMContentLoaded',function(){
  $('pagPrev').onclick=function(){tradePage--;renderTrades()};
  $('pagNext').onclick=function(){tradePage++;renderTrades()};
  $('pageSize').onchange=function(){tradePage=0;renderTrades()};
  $('oppPagPrev').onclick=function(){oppPage--;renderFlowDiagram()};
  $('oppPagNext').onclick=function(){oppPage++;renderFlowDiagram()};
  $('oppPageSize').onchange=function(){oppPage=0;renderFlowDiagram()};
  if($('scanWindow'))$('scanWindow').onchange=function(){oppPage=0;renderFlowDiagram()};
});

// EQUITY CHART
function renderEquityChart(){
  var ctx=$('equityChart').getContext('2d');
  var cap=S?S.capital||10000:10000;
  var lev=S?S.leverage||1:1;
  var eq=cap; var pts=[];
  if(trades.length){
    // Sort trades by close_time for correct chronological equity curve
    var sorted=trades.slice().sort(function(a,b){
      var ta=a.close_time||a.open_time||'';
      var tb=b.close_time||b.open_time||'';
      return ta<tb?-1:ta>tb?1:0;
    });
    var t0=sorted[0]?sorted[0].close_time||sorted[0].open_time:null;
    if(t0)pts.push({x:new Date(t0),y:cap});
    sorted.forEach(function(t){
      var p=parseFloat(t.pnl||t.PnL||0)*lev;
      if(p){eq+=p;var tm=t.close_time||t.open_time;if(tm)pts.push({x:new Date(tm),y:eq})}
    });
  }
  if(S)pts.push({x:new Date(),y:S.equity||cap});
  if(pts.length<2)pts.unshift({x:new Date(Date.now()-3600000),y:cap});

  if(eqChart)eqChart.destroy();
  var grad=ctx.createLinearGradient(0,0,0,280);
  grad.addColorStop(0,'rgba(99,102,241,.25)');grad.addColorStop(1,'rgba(99,102,241,0)');

  eqChart=new Chart(ctx,{type:'line',data:{datasets:[
    {label:'Equity',data:pts,borderColor:'#6366f1',backgroundColor:grad,borderWidth:2,fill:true,tension:.3,pointRadius:0,pointHitRadius:10},
    {label:'Starting Capital',data:pts.map(function(p){return{x:p.x,y:cap}}),borderColor:'rgba(148,163,184,.3)',borderWidth:1,borderDash:[6,4],pointRadius:0,fill:false}
  ]},options:{responsive:true,maintainAspectRatio:false,interaction:{intersect:false,mode:'index'},plugins:{legend:{display:false},tooltip:{backgroundColor:'#12121a',borderColor:'#1e1e2e',borderWidth:1,titleColor:'#94a3b8',bodyColor:'#e2e8f0',callbacks:{label:function(c){return c.dataset.label+': $'+c.parsed.y.toFixed(2)}}}},scales:{x:{type:'time',grid:{color:'rgba(30,30,46,.5)'},ticks:{color:'#64748b',font:{size:10}}},y:{grid:{color:'rgba(30,30,46,.5)'},ticks:{color:'#64748b',font:{size:10},callback:function(v){return '$'+v.toLocaleString()}}}}}});
}

// BOTTOM BAR
function renderBottomBar(){
  var syms=S.symbols||[];
  $('bCoins').innerHTML=syms.map(function(s){var m=cm(s);return '<span class="coin-icon '+m.icon+'" style="width:22px;height:22px;font-size:.5rem;display:inline-flex;vertical-align:middle;margin:0 2px">'+m.label+'</span>'}).join('');
  var tpTrades=trades.filter(function(t){return parseFloat(t.pnl||0)!==0});
  var avgP=tpTrades.length?tpTrades.reduce(function(a,t){return a+parseFloat(t.pnl||0)},0)/tpTrades.length:0;
  $('bAvgProfit').innerHTML='<span style="color:'+pC(avgP)+'">'+fUsd(avgP)+'</span>';
  var durs=trades.map(function(t){return parseFloat(t.duration_h||t.duration||t.Duration||0)}).filter(function(v){return v>0});
  var avgDur=durs.length?durs.reduce(function(a,b){return a+b},0)/durs.length:0;
  $('bAvgDur').textContent=durs.length?fmt(avgDur,1)+'h':'--';
  $('bUptime').textContent=S.uptime_hours!=null?fmt(S.uptime_hours,1)+'h':'--';
  var dd=S.max_drawdown_pct||0;
  var ddCol=dd>25?'var(--red)':dd>10?'var(--amber)':'var(--green)';
  $('bDD').innerHTML='<span style="color:'+ddCol+'">'+fmt(dd)+'%</span>';
  $('bDDBar').style.width=Math.min(dd*4,100)+'%';
  $('bDDBar').style.background=ddCol;
  var profile=S.profile||'medium';
  var profileCls=profile==='high'?'high':profile==='low'?'low':'medium';
  $('bProfile').innerHTML='<span class="risk-badge '+profileCls+'" style="font-size:.65rem;padding:2px 8px;margin:0">'+profile.toUpperCase()+'</span>';
}

// REFRESH LOOP
setInterval(function(){countdownVal--;$('countdown').textContent=countdownVal;if(countdownVal<=0){countdownVal=CONFIG.refreshInterval;fetchData()}},1000);
renderTrades();
fetchData();

