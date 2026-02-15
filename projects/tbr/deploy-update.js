/**
 * TBR Deploy — Upload build/ to FTP
 */
const ftp = require('basic-ftp');
const fs = require('fs');
const path = require('path');

const FTP_HOST = 'ftp.networkmarketingmakeover.com';
const FTP_USER = 'ai@trustedbusinessreviews.com';
const FTP_PASS = process.argv[2];
const BUILD_DIR = path.join(__dirname, 'build');

if (!FTP_PASS) { console.error('Usage: node deploy-update.js <password>'); process.exit(1); }

// Collect all files first
function collectFiles(dir, base = '') {
  const files = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const rel = base ? base + '/' + entry.name : entry.name;
    if (entry.isDirectory()) {
      files.push({ type: 'dir', remote: '/' + rel });
      files.push(...collectFiles(path.join(dir, entry.name), rel));
    } else {
      files.push({ type: 'file', local: path.join(dir, entry.name), remote: '/' + rel });
    }
  }
  return files;
}

async function deploy() {
  const client = new ftp.Client();
  client.ftp.verbose = false;

  try {
    console.log('Connecting...');
    await client.access({
      host: FTP_HOST, user: FTP_USER, password: FTP_PASS,
      secure: true, secureOptions: { rejectUnauthorized: false }
    });
    console.log('Connected!');

    const files = collectFiles(BUILD_DIR);
    
    // Create all dirs first
    for (const f of files) {
      if (f.type === 'dir') {
        try { await client.ensureDir(f.remote); } catch(e) {}
      }
    }
    
    // Upload all files
    for (const f of files) {
      if (f.type === 'file') {
        const dir = path.posix.dirname(f.remote);
        await client.cd(dir);
        console.log(`  ${f.remote}`);
        await client.uploadFrom(f.local, path.posix.basename(f.remote));
      }
    }
    
    console.log('\nDeploy complete!');
  } catch(e) {
    console.error('Error:', e.message);
    process.exit(1);
  } finally {
    client.close();
  }
}

deploy();
