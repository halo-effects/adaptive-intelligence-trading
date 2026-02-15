/**
 * TBR Deploy Script — Upload build/ to FTP server
 * Usage: node deploy.js <password>
 * 
 * Steps:
 * 1. Create backup_wordpress_20260214/ on server
 * 2. Move WordPress files into backup
 * 3. Upload build/ contents to web root
 */
const ftp = require('basic-ftp');
const fs = require('fs');
const path = require('path');

const FTP_HOST = 'ftp.networkmarketingmakeover.com';
const FTP_USER = 'ai@trustedbusinessreviews.com';
const FTP_PASS = process.argv[2];
const BUILD_DIR = path.join(__dirname, 'build');
const BACKUP_DIR = 'backup_wordpress_20260214';

// WordPress files/dirs to back up (move, not delete)
const WP_FILES = [
  'wp-admin', 'wp-content', 'wp-includes',
  'wp-config.php', 'wp-login.php', 'wp-cron.php',
  'wp-settings.php', 'wp-blog-header.php', 'wp-load.php',
  'wp-links-opml.php', 'wp-mail.php', 'wp-signup.php',
  'wp-trackback.php', 'wp-activate.php', 'wp-comments-post.php',
  'xmlrpc.php', 'index.php', 'license.txt', 'readme.html',
  'wp-config-sample.php'
];

if (!FTP_PASS) {
  console.error('Usage: node deploy.js <ftp-password>');
  process.exit(1);
}

async function deploy() {
  const client = new ftp.Client();
  client.ftp.verbose = true;
  
  try {
    console.log('Connecting to FTP...');
    await client.access({
      host: FTP_HOST,
      user: FTP_USER,
      password: FTP_PASS,
      secure: true,
      secureOptions: { rejectUnauthorized: false }
    });
    
    console.log('Connected! Current directory:', await client.pwd());
    
    // List current files
    const files = await client.list();
    console.log('Files on server:', files.map(f => f.name).join(', '));
    
    // Step 1: Create backup directory
    console.log(`\n=== Step 1: Creating ${BACKUP_DIR}/ ===`);
    try {
      await client.ensureDir(BACKUP_DIR);
      await client.cd('/');
    } catch (e) {
      console.log('Backup dir may already exist, continuing...');
      await client.cd('/');
    }
    
    // Step 2: Move WordPress files to backup
    console.log('\n=== Step 2: Moving WordPress files to backup ===');
    for (const name of WP_FILES) {
      const exists = files.find(f => f.name === name);
      if (exists) {
        try {
          await client.rename(name, `${BACKUP_DIR}/${name}`);
          console.log(`  Moved: ${name} → ${BACKUP_DIR}/${name}`);
        } catch (e) {
          console.log(`  Skip ${name}: ${e.message}`);
        }
      }
    }
    
    // Also move any other WP-related files
    for (const f of files) {
      if (f.name.startsWith('wp-') && !WP_FILES.includes(f.name)) {
        try {
          await client.rename(f.name, `${BACKUP_DIR}/${f.name}`);
          console.log(`  Moved: ${f.name} → ${BACKUP_DIR}/${f.name}`);
        } catch (e) {
          console.log(`  Skip ${f.name}: ${e.message}`);
        }
      }
    }
    
    // Step 3: Upload build/ contents
    console.log('\n=== Step 3: Uploading build/ contents ===');
    await client.cd('/');
    await uploadDir(client, BUILD_DIR, '/');
    
    console.log('\n=== Deploy complete! ===');
    console.log('Verify at: https://trustedbusinessreviews.com/');
    
  } catch (e) {
    console.error('Deploy error:', e.message);
  } finally {
    client.close();
  }
}

async function uploadDir(client, localDir, remoteDir) {
  const entries = fs.readdirSync(localDir, { withFileTypes: true });
  
  for (const entry of entries) {
    const localPath = path.join(localDir, entry.name);
    const remotePath = remoteDir === '/' ? `/${entry.name}` : `${remoteDir}/${entry.name}`;
    
    if (entry.isDirectory()) {
      try {
        await client.ensureDir(remotePath);
      } catch (e) { /* dir exists */ }
      await client.cd(remotePath);
      await uploadDir(client, localPath, remotePath);
      await client.cd('..');
    } else {
      console.log(`  Upload: ${remotePath}`);
      await client.cd(remoteDir);
      await client.uploadFrom(localPath, entry.name);
    }
  }
}

deploy();
