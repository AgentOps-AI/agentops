// Utility to convert ANSI escape codes to HTML spans with inline styles
// Supports the ConsoleColors Java class codes and \u001B[xxm] style codes

// Match both \x1b and \u001B (ESC) ANSI codes
const ANSI_REGEX = /(?:(?:\x1b|\u001b|\u001B)|\\u001b|\\x1b)\[(\d{1,3}(;\d{1,3})*)m/g;

// Map ANSI codes to CSS styles
const ANSI_STYLES: Record<string, string> = {
  // Reset
  '0': 'color:inherit;background:none;font-weight:normal;text-decoration:none;',

  // Regular colors
  '30': 'color:#000;', // Black
  '31': 'color:#c00;', // Red
  '32': 'color:#0c0;', // Green
  '33': 'color:#cc0;', // Yellow
  '34': 'color:#00c;', // Blue
  '35': 'color:#a0a;', // Purple
  '36': 'color:#0cc;', // Cyan
  '37': 'color:#ccc;', // White

  // Bold
  '1;30': 'color:#000;font-weight:bold;',
  '1;31': 'color:#c00;font-weight:bold;',
  '1;32': 'color:#0c0;font-weight:bold;',
  '1;33': 'color:#cc0;font-weight:bold;',
  '1;34': 'color:#00c;font-weight:bold;',
  '1;35': 'color:#a0a;font-weight:bold;',
  '1;36': 'color:#0cc;font-weight:bold;',
  '1;37': 'color:#ccc;font-weight:bold;',

  // Underline
  '4;30': 'color:#000;text-decoration:underline;',
  '4;31': 'color:#c00;text-decoration:underline;',
  '4;32': 'color:#0c0;text-decoration:underline;',
  '4;33': 'color:#cc0;text-decoration:underline;',
  '4;34': 'color:#00c;text-decoration:underline;',
  '4;35': 'color:#a0a;text-decoration:underline;',
  '4;36': 'color:#0cc;text-decoration:underline;',
  '4;37': 'color:#ccc;text-decoration:underline;',

  // Background
  '40': 'background:#000;',
  '41': 'background:#c00;',
  '42': 'background:#0c0;',
  '43': 'background:#cc0;',
  '44': 'background:#00c;',
  '45': 'background:#a0a;',
  '46': 'background:#0cc;',
  '47': 'background:#ccc;',

  // High Intensity
  '90': 'color:#555;',
  '91': 'color:#f55;',
  '92': 'color:#5f5;',
  '93': 'color:#ff5;',
  '94': 'color:#55f;',
  '95': 'color:#f5f;',
  '96': 'color:#5ff;',
  '97': 'color:#fff;',

  // Bold High Intensity
  '1;90': 'color:#555;font-weight:bold;',
  '1;91': 'color:#f55;font-weight:bold;',
  '1;92': 'color:#5f5;font-weight:bold;',
  '1;93': 'color:#ff5;font-weight:bold;',
  '1;94': 'color:#55f;font-weight:bold;',
  '1;95': 'color:#f5f;font-weight:bold;',
  '1;96': 'color:#5ff;font-weight:bold;',
  '1;97': 'color:#fff;font-weight:bold;',

  // High Intensity backgrounds
  '100': 'background:#555;',
  '101': 'background:#f55;',
  '102': 'background:#5f5;',
  '103': 'background:#ff5;',
  '104': 'background:#55f;',
  '105': 'background:#f5f;',
  '106': 'background:#5ff;',
  '107': 'background:#fff;',
};

function getStyleFromCodes(codes: string): string {
  // Try full code first, then fallback to each part
  if (ANSI_STYLES[codes]) return ANSI_STYLES[codes];
  return codes
    .split(';')
    .map((code) => ANSI_STYLES[code] || '')
    .join('');
}

export function ansiToHtml(str: string): string {
  let html = '';
  let lastIndex = 0;
  let currentSpanOpen = false;

  // Reset regex index for safety if called multiple times
  ANSI_REGEX.lastIndex = 0;

  let match;
  while ((match = ANSI_REGEX.exec(str)) !== null) {
    const codes = match[1];
    const offset = match.index;

    // 1. Get text BEFORE the current code
    const textSegment = escapeHtml(str.slice(lastIndex, offset));

    // 2. Append the preceding text. It belongs inside the currently open span (if any)
    html += textSegment;

    // 3. Process the code that followed the text
    const style = getStyleFromCodes(codes);

    // 4. Close the current span *before* processing the new code, IF a span is open
    if (currentSpanOpen) {
      html += '</span>';
      currentSpanOpen = false;
    }

    // 5. Open a new span if the code is a style code (not reset '0')
    if (codes !== '0' && style) {
      html += `<span style="${style} !important">`;
      currentSpanOpen = true;
    }

    // 6. Update index to be after the processed ANSI code
    lastIndex = ANSI_REGEX.lastIndex;
  }

  // Append the final text segment after the last code
  const lastTextSegment = escapeHtml(str.slice(lastIndex));
  html += lastTextSegment;

  // Close the last span if it was left open
  if (currentSpanOpen) {
    html += '</span>';
  }

  return html;
}

function escapeHtml(text: string): string {
  return text.replace(/[&<>"'']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || c;
  });
}

/**
 * Remove all ANSI escape codes from a string, including bare [xxm] and [xx;xxm] sequences
 * Handles cases where codes are adjacent or split (e.g. '\x1b' and '[32m')
 */
export function stripAnsiCodes(str: string): string {
  // Remove escape-prefixed codes
  let result = str.replace(/(?:\x1b|\u001b|\u001B)\[(\d{1,3}(;\d{1,3})*)m/g, '');
  // Remove any remaining bare [xxm] or [xx;xxm] codes
  result = result.replace(/\[(\d{1,3}(;\d{1,3})*)m/g, '');
  // Remove any remaining [**m patterns (where ** is any content between brackets ending with m)
  result = result.replace(/\[[^\]]*m/g, '');
  // Remove any remaining [0-9;]*m patterns
  result = result.replace(/\[[0-9;]*m/g, '');
  // Final catch-all: remove any [ ... m pattern (non-greedy)
  result = result.replace(/\[[^\]]*?m/g, '');
  // Remove any remaining ESC characters
  result = result.replace(/(?:\x1b|\u001b|\u001B)/g, '');
  result = result.replace(/\u001b/g, '');
  // Remove string literals '\u001b' and '\x1b' (escaped in JS strings)
  result = result.replace(/\\u001b|\\x1b/gi, '');
  return result;
}
