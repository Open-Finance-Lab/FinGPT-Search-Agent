const path = require('path');
const fs = require('fs');

// Read all CSS files and combine them
const stylesDir = path.join(__dirname, 'src/modules/styles');
const cssFiles = ['popup.css', 'header.css', 'chat.css', 'windows.css', 'theme.css'];

let combinedCSS = '/* Combined CSS for Agentic FinSearch Extension */\n\n';

cssFiles.forEach(file => {
    const filePath = path.join(stylesDir, file);
    const content = fs.readFileSync(filePath, 'utf8');
    combinedCSS += `/* ===== ${file} ===== */\n${content}\n\n`;
});

// Write combined CSS to dist
const distDir = path.join(__dirname, 'dist');
if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir, { recursive: true });
}

fs.writeFileSync(path.join(distDir, 'styles.css'), combinedCSS);
console.log('✅ Combined CSS created at dist/styles.css');