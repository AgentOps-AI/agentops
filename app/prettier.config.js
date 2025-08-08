// prettier.config.js
module.exports = {
    endOfLine: 'auto', // Use 'auto' for cross-platform compatibility
    semi: true,
    trailingComma: 'all',
    singleQuote: true,
    printWidth: 100,
    tabWidth: 2,
    useTabs: false,
    arrowParens: 'always',
    plugins: ['prettier-plugin-tailwindcss'],
    tailwindFunctions: ['clsx', 'cn'],
    // tailwindConfig is omitted - Prettier will auto-detect tailwind.config.js/ts
    // in subdirectories like dashboard/ and landing/
}; 