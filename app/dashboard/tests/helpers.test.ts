import { formatPrice } from '../lib/utils';

test('formats price correctly', () => {
  expect(formatPrice(100_000_000)).toBe('$10.00');
  expect(formatPrice(100_000_000.0001)).toBe('$10.00');
  expect(formatPrice(100_100_000.01)).toBe('$10.01');
  expect(formatPrice(null)).toBe('');
  expect(formatPrice(500_000, { decimals: 4 })).toBe('$0.05');
  expect(formatPrice(500_000, { decimals: 2 })).toBe('$0.05');
  expect(formatPrice(1_000_000, { decimals: 4 })).toBe('$0.10');
  expect(formatPrice(1_000_000, { decimals: 2 })).toBe('$0.10');
  expect(formatPrice(0.1, { decimals: 4 })).toBe('$0.00');
  expect(formatPrice(1_000, { decimals: 4 })).toBe('$0.0001');
  expect(formatPrice(23_000, { decimals: 4 })).toBe('$0.0023');
  expect(formatPrice(0, { decimals: 4 })).toBe('$0.00');
  expect(formatPrice(18_000, { decimals: 4 })).toBe('$0.0018');
  expect(formatPrice(100_000_000.0001, { decimals: 4 })).toBe('$10.00');
  expect(formatPrice(-1, { decimals: 2 })).toBe('$0.00');
});
