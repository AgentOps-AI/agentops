import {
  cn,
  truncateString,
  titleCase,
  parseTags,
  formatTime,
  formatTimeRange,
  formatDate,
} from '../lib/utils';
import { ansiToHtml } from '../utils/ansi-to-html.util';

describe('Utility Functions', () => {
  describe('cn', () => {
    it('combines class names correctly', () => {
      expect(cn('base', 'additional')).toBe('base additional');
      expect(cn('base', { conditional: true })).toBe('base conditional');
      expect(cn('base', { conditional: false })).toBe('base');
    });
  });

  describe('truncateString', () => {
    it('truncates strings correctly', () => {
      expect(truncateString('Hello World', 5)).toBe('Hello...');
      expect(truncateString('Hello World', 20)).toBe('Hello World');
      expect(truncateString(null)).toBe('');
      expect(truncateString('Hello World')).toBe('Hello World');
    });
  });

  describe('titleCase', () => {
    it('converts strings to title case', () => {
      expect(titleCase('hello world')).toBe('Hello World');
      expect(titleCase('HELLO WORLD')).toBe('Hello World');
      expect(titleCase('hello-world')).toBe('Hello-World');
    });
  });

  describe('parseTags', () => {
    it('parses valid JSON arrays', () => {
      expect(parseTags(JSON.stringify(['tag1', 'tag2']))).toEqual(['tag1', 'tag2']);
      expect(parseTags(JSON.stringify([]))).toEqual([]);
    });

    it('handles invalid inputs', () => {
      expect(parseTags(null)).toEqual([]);
      expect(parseTags(undefined)).toEqual([]);
      expect(parseTags('invalid json')).toEqual([]);
      expect(parseTags(JSON.stringify([1, 2]))).toEqual([]);
    });
  });

  describe('formatTime', () => {
    it('formats milliseconds correctly', () => {
      expect(formatTime(500000)).toBe('0.50ms');
      expect(formatTime(1000000)).toBe('1.00ms');
    });

    it('formats seconds correctly', () => {
      expect(formatTime(1000000000)).toBe('1.00s');
      expect(formatTime(5000000000)).toBe('5.00s');
    });

    it('formats minutes and hours correctly', () => {
      expect(formatTime(60000000000)).toBe('01m 00s');
      expect(formatTime(3600000000000)).toBe('01h 00m 00s');
    });
  });

  describe('formatTimeRange', () => {
    it('formats time ranges correctly', () => {
      expect(formatTimeRange(0, 60)).toBe('0m 0s - 1m 0s');
      expect(formatTimeRange(60, 120)).toBe('1m 0s - 3m 0s');
    });
  });

  describe('formatDate', () => {
    it('formats dates correctly', () => {
      const date = new Date('2024-01-01T12:00:00Z');
      const formatted = formatDate(date.toISOString());
      expect(formatted).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}, \d{1,2}:\d{2} [AP]M/);
    });
  });

  describe('ansiToHtml', () => {
    it('converts ANSI color codes to HTML spans', () => {
      const input = '2025-05-02 21:16:01,760 - INFO - \u001b[33mAssistant\u001b[0m (to User):';
      const output = ansiToHtml(input);
      // Should contain a span with yellow color and the word Assistant
      expect(output).toContain('<span style="color:#cc0;">');
      expect(output).toContain('Assistant');
      // Should not contain any ANSI codes
      expect(output).not.toMatch(/\u001b\[33m|\u001b\[0m|\x1b\[33m|\x1b\[0m|\[33m|\[0m/);
      // Should preserve the rest of the string
      expect(output).toContain('2025-05-02 21:16:01,760 - INFO - ');
      expect(output).toContain(' (to User):');
    });
  });
});
