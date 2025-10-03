// check-dist.js
const fs = require('fs');
const path = require('path');

const distDir = path.resolve(__dirname, 'dist');
const requiredFiles = ['manifest.json', 'main.js', 'vendors.js', 'katex.js', 'styles.css', 'assets/16x16_icon.png', 'assets/32x32_icon.png']; 

let allGood = true;

console.log(`\n🔍 Validating extension build in: ${distDir}\n`);

for (const file of requiredFiles) {
  const filePath = path.join(distDir, file);
  if (!fs.existsSync(filePath)) {
    console.error(`❌ Missing: ${file}`);
    allGood = false;
  } else {
    console.log(`✅ Found: ${file}`);
  }
}

if (allGood) {
  console.log(`\n🎉 All required files are present in dist/. Update the plugin in your browser to verify the updates!\n`);
  process.exit(0);
} else {
  console.error(`\n🚨 Some files are missing. Make sure Webpack and copy-webpack-plugin ran correctly.\n`);
  process.exit(1);
}
