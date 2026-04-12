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

// Create client WITHOUT api key — should auto-generate one per Module 02
console.log('Creating client without API key (should auto-create)...');
try {
  const client = await BasisClient.create({ privateKey: env.BASIS_PRIVATE_KEY });
  console.log('Client created');
  console.log('apiKey property:', client.apiKey || client._apiKey || 'not found');
  console.log('Client keys:', Object.keys(client));
  
  // Check if ensureApiKey exists per Module 18
  if (client.ensureApiKey) {
    console.log('\nCalling ensureApiKey()...');
    const key = await client.ensureApiKey();
    console.log('New API key:', key);
  } else {
    console.log('ensureApiKey not found on client');
  }
  
  // Try to create one via API
  if (client.api?.createApiKey) {
    console.log('\nCalling api.createApiKey("geegee")...');
    const newKey = await client.api.createApiKey("geegee");
    console.log('New key:', newKey);
  } else {
    console.log('api.createApiKey not found');
  }

  // Try profile now
  console.log('\n=== Profile test ===');
  const profile = await client.api.getMyProfile();
  console.log(JSON.stringify(profile, null, 2));

} catch (e) {
  console.error('Error:', e.message);
}
