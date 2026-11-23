const fs = require('fs');
const path = require('path');
const vm = require('vm');

// 1. Locate and load highlight.js from book/
const bookDir = path.resolve(__dirname, '..', 'book');
const files = fs.readdirSync(bookDir);
const hljsFile = files.find(f => f.startsWith('highlight-') && f.endsWith('.js'));
if (!hljsFile) {
    console.error('Could not find highlight-*.js in', bookDir);
    process.exit(1);
}

const hljsCode = fs.readFileSync(path.join(bookDir, hljsFile), 'utf8');
const context = { window: {}, document: {}, navigator: {} };
vm.createContext(context);
vm.runInContext(hljsCode, context);
const hljs = context.hljs;
console.log('Loaded Highlight.js with languages:', hljs.listLanguages().length);

// 2. Read print.html and force crisp Light print theme (never coal/dark in PDF!)
const printHtmlPath = path.join(bookDir, 'print.html');
let html = fs.readFileSync(printHtmlPath, 'utf8');

html = html
    .replace(/<html([^>]*?)class="[^"]*"/, '<html$1class="light"')
    .replace(/const default_dark_theme = [^;]+;/g, 'const default_dark_theme = "light";')
    .replace(/const default_light_theme = [^;]+;/g, 'const default_light_theme = "light";')
    .replace(/const default_theme = [^;]+;/g, 'const default_theme = "light";')
    .replace(/<h1 id="cover">[\s\S]*?<\/h1>/, '');

function unescapeHtml(str) {
    return str
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'")
        .replace(/&amp;/g, '&');
}

// 3. Highlight code blocks
let highlightedCount = 0;
const langMap = {
    'c++': 'cpp',
    'rs': 'rust',
    'sh': 'bash',
    'zsh': 'bash'
};

const regex = /(<pre[^>]*><code\s+class="([^"]*)">)([\s\S]*?)(<\/code><\/pre>)/g;

html = html.replace(regex, (match, openTag, classNames, codeBody, closeTag) => {
    // Find language class
    const matchLang = classNames.match(/\blanguage-([\w+-]+)\b/);
    if (!matchLang) {
        return match;
    }
    let lang = matchLang[1].toLowerCase();
    if (langMap[lang]) lang = langMap[lang];

    if (!hljs.getLanguage(lang)) {
        // unsupported or plaintext
        return match;
    }

    try {
        const rawCode = unescapeHtml(codeBody);
        const highlighted = hljs.highlight(lang, rawCode).value;
        highlightedCount++;
        
        // Ensure 'hljs' is in the code tag's class
        let newOpenTag = openTag;
        if (!classNames.includes('hljs')) {
            newOpenTag = openTag.replace(`class="${classNames}"`, `class="hljs ${classNames}"`);
        }
        return `${newOpenTag}${highlighted}${closeTag}`;
    } catch (err) {
        console.warn(`Failed to highlight block for lang ${lang}:`, err.message);
        return match;
    }
});

console.log(`Successfully pre-highlighted ${highlightedCount} code blocks in print.html`);
fs.writeFileSync(printHtmlPath, html, 'utf8');
