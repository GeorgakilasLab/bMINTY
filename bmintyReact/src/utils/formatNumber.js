/**
 * Format a number to include thousand separators
 * @param {number} num - The number to format
 * @returns {string} - The formatted number (e.g., 1000 -> "1,000")
 */
export function formatNumber(num) {
  if (num === null || num === undefined) return '0';
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}
