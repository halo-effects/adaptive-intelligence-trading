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

const client = await BasisClient.create({ privateKey: env.BASIS_PRIVATE_KEY });

// Delete the old key
console.log('Deleting old API key...');
try {
  await client.api.deleteApiKey('cmnuud7v500061fl1t9t2xkmj');
  console.log('Deleted ✓');
} catch (e) { console.log('Delete error:', e.message); }

// Create new key
console.log('Creating new API key...');
try {
  const newKey = await client.api.createApiKey('geegee');
  console.log('NEW API KEY:', JSON.stringify(newKey));
  console.log('\n⚠️  SAVE THIS KEY - it will only be shown once!');
} catch (e) { console.log('Create error:', e.message); }
