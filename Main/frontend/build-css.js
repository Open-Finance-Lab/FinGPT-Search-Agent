const path = require('path');
const fs = require('fs');

const stylesDir = path.join(__dirname, 'src/modules/styles');
const cssFiles = ['popup.css', 'header.css', 'chat.css', 'windows.css', 'theme.css'];
const katexCssPath = path.join(__dirname, 'node_modules', 'katex', 'dist', 'katex.min.css');
const katexFontsSource = path.join(__dirname, 'node_modules', 'katex', 'dist', 'fonts');
const distDir = path.join(__dirname, 'dist');
const distFontsDir = path.join(distDir, 'fonts');

let combinedCSS = '/* Combined CSS for Agentic FinSearch Extension */\n\n';

cssFiles.forEach(file => {
    const filePath = path.join(stylesDir, file);
    const content = fs.readFileSync(filePath, 'utf8');
    combinedCSS += `/* ===== ${file} ===== */\n${content}\n\n`;
});

if (fs.existsSync(katexCssPath)) {
    const katexCssContent = fs.readFileSync(katexCssPath, 'utf8');
    combinedCSS += `/* ===== katex.min.css ===== */\n${katexCssContent}\n\n`;
} else {
    console.warn('KaTeX CSS not found; math styles may be missing.');
}

if (!fs.existsSync(distDir)) {
    fs.mkdirSync(distDir, { recursive: true });
}

fs.writeFileSync(path.join(distDir, 'styles.css'), combinedCSS);
console.log('Combined CSS created at dist/styles.css');

function copyDirectory(source, destination) {
    if (!fs.existsSync(source)) {
        return;
    }
    if (!fs.existsSync(destination)) {
        fs.mkdirSync(destination, { recursive: true });
    }

    for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
        const srcPath = path.join(source, entry.name);
        const destPath = path.join(destination, entry.name);

        if (entry.isDirectory()) {
            copyDirectory(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

if (fs.existsSync(katexFontsSource)) {
    copyDirectory(katexFontsSource, distFontsDir);
    console.log('KaTeX fonts copied to dist/fonts');
} else {
    console.warn('KaTeX fonts directory not found; math fonts may be missing.');
}
