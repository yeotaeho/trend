const fs = require('fs');
const scan = JSON.parse(fs.readFileSync('.ua/intermediate/scan-result.json', 'utf8'));
const files = (scan.files || scan.fileList || []).map(f => typeof f === 'string' ? f : f.path);
fs.writeFileSync('.ua/intermediate/fingerprint-input.json', JSON.stringify({
  projectRoot: 'C:/Users/COM-KMAB/Documents/trend',
  sourceFilePaths: files,
  gitCommitHash: '688aeb86f0378d7299b7b3d713f4545429565742'
}, null, 2));
console.log('sourceFilePaths', files.length);
