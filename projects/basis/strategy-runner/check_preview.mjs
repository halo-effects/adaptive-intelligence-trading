import { BasisClient } from 'basis-sdk';
import { parseUnits } from 'viem';
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
const preview = await client.trading.getAmountsOut(parseUnits('200', 18), [client.usdbAddress, client.mainTokenAddress]);
console.log('type:', typeof preview, Array.isArray(preview));
console.log('raw:', preview);
console.log('element type:', typeof preview[preview.length - 1]);
console.log('BigInt?', typeof preview[0] === 'bigint');
// Try accessing as string
for (let i = 0; i < preview.length; i++) {
  console.log(`  [${i}]: ${preview[i]} (type: ${typeof preview[i]})`);
}
