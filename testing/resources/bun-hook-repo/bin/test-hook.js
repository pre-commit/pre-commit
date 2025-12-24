#!/usr/bin/env node
// Simple test hook that validates file content
const fs = require('fs');

const files = process.argv.slice(2);
let failed = false;

files.forEach(file => {
  const content = fs.readFileSync(file, 'utf8');
  if (content.includes('bad')) {
    console.error(`Error in ${file}: contains 'bad'`);
    failed = true;
  }
});

process.exit(failed ? 1 : 0);
