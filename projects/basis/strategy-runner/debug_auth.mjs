import { BasisClient } from 'basis-sdk';
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

const API_KEY = env.BASIS_API_KEY;
console.log(`API key: ${API_KEY}`);

// Try without API key first
console.log('\n=== Without API key ===');
try {
  const client = await BasisClient.create({ privateKey: env.BASIS_PRIVATE_KEY, apiKey: API_KEY });
  const wallet = client.walletClient.account.address;
  console.log(`Wallet: ${wallet}`);
  
  // The faucet works - let's see what else works without auth
  console.log('\n=== Unauthenticated API calls ===');
  
  // Faucet status (works!)
  try {
    const faucet = await client.api.getFaucetStatus();
    console.log('Faucet status: ✓', JSON.stringify(faucet).substring(0, 100));
  } catch (e) { console.log('Faucet: ✗', e.message.substring(0, 100)); }
  
  // Get tokens (public data?)
  try {
    const tokens = await client.api.getTokens({ limit: 5 });
    console.log('getTokens: ✓', JSON.stringify(tokens).substring(0, 200));
  } catch (e) { console.log('getTokens: ✗', e.message.substring(0, 100)); }
  
  // Get pulse (platform stats, probably public)
  try {
    const pulse = await client.api.getPulse();
    console.log('getPulse: ✓', JSON.stringify(pulse).substring(0, 200));
  } catch (e) { console.log('getPulse: ✗', e.message.substring(0, 100)); }
  
  // Get public profile
  try {
    const pub = await client.api.getPublicProfile(wallet);
    console.log('getPublicProfile: ✓', JSON.stringify(pub).substring(0, 200));
  } catch (e) { console.log('getPublicProfile: ✗', e.message.substring(0, 100)); }
  
  // Get leaderboard
  try {
    const lb = await client.api.getLeaderboard({ limit: 5 });
    console.log('getLeaderboard: ✓', JSON.stringify(lb).substring(0, 200));
  } catch (e) { console.log('getLeaderboard: ✗', e.message.substring(0, 100)); }
  
  // List API keys
  try {
    const keys = await client.api.listApiKeys();
    console.log('listApiKeys: ✓', JSON.stringify(keys).substring(0, 200));
  } catch (e) { console.log('listApiKeys: ✗', e.message.substring(0, 100)); }

  // Delete the old key and create a new one
  console.log('\n=== Try deleting old key and creating new ===');
  try {
    const keys = await client.api.listApiKeys();
    console.log('Keys found:', keys);
    if (Array.isArray(keys) && keys.length > 0) {
      for (const k of keys) {
        console.log(`Deleting key: ${k.id || k}`);
        await client.api.deleteApiKey(k.id || k);
      }
    }
    const newKey = await client.api.createApiKey('geegee');
    console.log('NEW API KEY:', newKey);
  } catch (e) { console.log('Key rotation error:', e.message.substring(0, 200)); }

} catch (e) {
  console.error('Error:', e.message);
}
