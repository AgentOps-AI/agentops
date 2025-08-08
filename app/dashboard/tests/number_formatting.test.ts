import {
  formatNumber,
  formatPrice,
  formatMetric,
  formatPercentage,
  formatTokens,
} from '../lib/number_formatting_utils';

describe('Number Formatting Utilities', () => {
  describe('formatNumber', () => {
    it('formats numbers with default options', () => {
      expect(formatNumber(1234.5678)).toBe('1,235');
      expect(formatNumber(1000000)).toBe('1,000,000');
      expect(formatNumber(0)).toBe('0');
    });

    it('handles decimal places', () => {
      expect(formatNumber(1234.5678, 2)).toBe('1,234.57');
      expect(formatNumber(1234.5678, 1)).toBe('1,234.6');
    });

    it('handles invalid inputs', () => {
      expect(formatNumber(null)).toBe('');
      expect(formatNumber(undefined)).toBe('');
      expect(formatNumber('invalid')).toBe('');
    });
  });

  describe('formatPrice', () => {
    it('formats prices with default options (USD)', () => {
      expect(formatPrice(1234.5678)).toBe('$1,234.57');
      expect(formatPrice(1000000)).toBe('$1,000,000.00');
      expect(formatPrice(0)).toBe('$0');
    });

    it('formats prices with different currencies', () => {
      expect(formatPrice(1234.5678, { currency: 'EUR' })).toBe('€1,234.57');
      expect(formatPrice(1234.5678, { currency: 'GBP' })).toBe('£1,234.57');
      expect(formatPrice(1234.5678, { currency: 'JPY' })).toBe('¥1,235');
    });

    it('formats prices with different locales', () => {
      expect(formatPrice(1234.5678, { locale: 'de-DE', currency: 'EUR' })).toBe('1.234,57 €');
      expect(formatPrice(1234.5678, { locale: 'fr-FR', currency: 'EUR' })).toBe('1 234,57 €');
      expect(formatPrice(1234.5678, { locale: 'ja-JP', currency: 'JPY' })).toBe('¥1,235');
    });

    it('handles custom decimal places', () => {
      expect(formatPrice(1234.5678, { decimals: 2 })).toBe('$1,234.57');
      expect(formatPrice(1234.5678, { decimals: 1 })).toBe('$1,234.6');
      expect(formatPrice(1234.5678, { decimals: 0 })).toBe('$1,235');
    });

    it('handles very small prices', () => {
      expect(formatPrice(0.0001)).toBe('< $0.01');
      expect(formatPrice(0.00001, { decimals: 4 })).toBe('< $0.0001');
      expect(formatPrice(0.00001, { currency: 'EUR', decimals: 4 })).toBe('< €0.0001');
    });

    it('handles invalid inputs', () => {
      expect(formatPrice(null)).toBe('');
      expect(formatPrice(undefined)).toBe('');
      expect(formatPrice('invalid')).toBe('');
    });
  });

  describe('formatMetric', () => {
    it('formats metrics with default options', () => {
      expect(formatMetric(1234.5678)).toBe('1234.57');
      expect(formatMetric(0)).toBe('0');
      expect(formatMetric(0.0001)).toBe('0.000');
    });

    it('handles prefixes and suffixes', () => {
      expect(formatMetric(1234.5678, { prefix: '$' })).toBe('$1234.57');
      expect(formatMetric(1234.5678, { suffix: 'ms' })).toBe('1234.57ms');
    });

    it('handles small numbers', () => {
      expect(formatMetric(0.0001)).toBe('0.000');
      expect(formatMetric(0.01)).toBe('0.01');
    });

    it('handles invalid inputs', () => {
      expect(formatMetric(null)).toBe('N/A');
      expect(formatMetric(undefined)).toBe('N/A');
      expect(formatMetric('invalid')).toBe('N/A');
    });
  });

  describe('formatPercentage', () => {
    it('formats percentages with default options', () => {
      expect(formatPercentage(0.1234)).toBe('12.34%');
      expect(formatPercentage(0)).toBe('0.00%');
      expect(formatPercentage(1)).toBe('100.00%');
    });

    it('handles already multiplied values', () => {
      expect(formatPercentage(12.34, { alreadyMultiplied: true })).toBe('12.34%');
      expect(formatPercentage(100, { alreadyMultiplied: true })).toBe('100.00%');
    });

    it('handles invalid inputs', () => {
      expect(formatPercentage(null)).toBe('N/A');
      expect(formatPercentage(undefined)).toBe('N/A');
      expect(formatPercentage('invalid')).toBe('N/A');
    });
  });

  describe('formatTokens', () => {
    it('formats regular numbers with commas', () => {
      expect(formatTokens(1234)).toEqual({ display: '1,234', full: '1,234' });
      expect(formatTokens(1000000)).toEqual({ display: '1,000,000', full: '1,000,000' });
      expect(formatTokens(0)).toEqual({ display: '0', full: '0' });
    });

    it('handles numbers larger than 8 digits', () => {
      expect(formatTokens(123456789)).toEqual({ display: '123M', full: '123,456,789' });
      expect(formatTokens(1000000000)).toEqual({ display: '1,000M', full: '1,000,000,000' });
    });

    it('handles string inputs', () => {
      expect(formatTokens('1234')).toEqual({ display: '1,234', full: '1,234' });
      expect(formatTokens('123456789')).toEqual({ display: '123M', full: '123,456,789' });
    });

    it('handles invalid inputs', () => {
      expect(formatTokens(null)).toEqual({ display: '0', full: '0' });
      expect(formatTokens(undefined)).toEqual({ display: '0', full: '0' });
      expect(formatTokens('invalid')).toEqual({ display: '0', full: '0' });
    });

    it('never shows decimal places', () => {
      expect(formatTokens(1234.5678)).toEqual({ display: '1,235', full: '1,235' });
      expect(formatTokens(1234.1)).toEqual({ display: '1,234', full: '1,234' });
      expect(formatTokens('1234.9999')).toEqual({ display: '1,235', full: '1,235' });
    });
  });
});
