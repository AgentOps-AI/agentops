const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const branchName = execSync('git rev-parse --abbrev-ref HEAD').toString().trim();

const now = new Date();
const timestamp = now
  .toLocaleString('en-US', {
    month: 'long',
    day: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
  .replace(/[\/:]/g, '_')
  .replace(/,/g, '')
  .replace(/\s+/g, '_');

const targetDir = path.join('bundle_analytics', branchName, timestamp);
fs.mkdirSync(targetDir, { recursive: true });

const sourceDir = path.join('.next', 'analyze');
const files = fs.readdirSync(sourceDir);

files.forEach((file) => {
  if (file.endsWith('.html')) {
    const sourcePath = path.join(sourceDir, file);
    const targetPath = path.join(targetDir, file);
    fs.copyFileSync(sourcePath, targetPath);
    console.log(`Copied ${file} to ${targetPath}`);
  }
});

console.log(`\nBundle analytics organized in: ${targetDir}`);
