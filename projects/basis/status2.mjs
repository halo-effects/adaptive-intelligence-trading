import { BasisClient } from './dist/index.mjs';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load env manually
const envPath = path.join(__dirname, 'skill-scaffold', '.env');
const envText = fs.readFileSync(envPath, 'utf-8');
console.log('=== ENV File ===');
console.log(envText.split('\n').slice(0, 3).join('\n'));

const env = envText
  .split('\n')
  .filter(line => line.trim() && !line.startsWith('#'))
  .reduce((acc, line) => {
    const [key, ...rest] = line.split('=');
    acc[key.trim()] = rest.join('=').trim().replace(/^["']|["']$/g, '');
    return acc;
  }, {});

const PRIVATE_KEY = env.BASIS_PRIVATE_KEY;
const API_KEY = env.BASIS_API_KEY;

console.log(`\nPRIVATE_KEY: ${PRIVATE_KEY?.substring(0, 20)}...`);
console.log(`API_KEY: ${API_KEY?.substring(0, 20)}...`);

if (!PRIVATE_KEY) {
  console.error('BASIS_PRIVATE_KEY not found');
  process.exit(1);
}

console.log('\n=== Creating Basis Client ===');
try {
  const client = await BasisClient.create({
    privateKey: PRIVATE_KEY,
    apiKey: API_KEY,
  });
  
  console.log('=== Client Created ===');
  console.log(client);
  console.log(typeof client);
  console.log(Object.keys(client).slice(0, 10));
  
  if (client && client.account) {
    console.log(`\nWallet: ${client.account.address}`);
  } else {
    console.log('client.account is undefined');
    console.log('Client properties:', Object.keys(client));
  }
} catch (err) {
  console.error('Error creating client:', err.message);
  console.error(err);
}
