'use client';

import { useState, useEffect, useCallback } from 'react';

// -------- Types --------
interface UseBookmarksReturn {
  bookmarks: Set<string>;
  toggleBookmark: (traceId: string) => void;
  isBookmarked: (traceId: string) => boolean;
  clearBookmarks: () => void;
}

// -------- Constants --------
const BOOKMARKS_STORAGE_KEY = 'agentops-trace-bookmarks';

// -------- Global store --------

// The single source of truth for bookmarked trace IDs.
let globalBookmarks: Set<string> = (() => {
  if (typeof window === 'undefined') return new Set();

  try {
    const stored = localStorage.getItem(BOOKMARKS_STORAGE_KEY);
    return stored ? new Set<string>(JSON.parse(stored)) : new Set<string>();
  } catch (error) {
    console.error('[useBookmarks] Failed to load bookmarks from localStorage:', error);
    return new Set<string>();
  }
})();

// Attached listeners will be notified any time the global set mutates.
type Listener = (next: Set<string>) => void;
const listeners = new Set<Listener>();

const notifyAll = () => {
  const snapshot = new Set<string>(globalBookmarks); // clone to avoid accidental external mutation
  listeners.forEach((listener) => listener(snapshot));

  // Persist immediately so we stay in sync with the global state
  try {
    if (typeof window !== 'undefined') {
      localStorage.setItem(BOOKMARKS_STORAGE_KEY, JSON.stringify(Array.from(globalBookmarks)));
    }
  } catch (error) {
    console.error('[useBookmarks] Failed to persist bookmarks to localStorage:', error);
  }
};

// -------- Hook implementation --------
export function useBookmarks(): UseBookmarksReturn {
  const [bookmarks, setBookmarks] = useState<Set<string>>(globalBookmarks);

  // Subscribe to external updates.
  useEffect(() => {
    listeners.add(setBookmarks);
    return () => {
      listeners.delete(setBookmarks);
    };
  }, []);

  // Toggle a trace bookmark in the global store and notify all subscribers.
  const toggleBookmark = useCallback((traceId: string) => {
    if (!traceId) return;

    if (globalBookmarks.has(traceId)) {
      globalBookmarks.delete(traceId);
    } else {
      globalBookmarks.add(traceId);
    }

    notifyAll();
  }, []);

  // Clear all bookmarks from the global store and notify.
  const clearBookmarks = useCallback(() => {
    globalBookmarks = new Set<string>();
    notifyAll();
  }, []);

  // Check if a trace ID is bookmarked using the current snapshot for this hook instance.
  const isBookmarked = useCallback(
    (traceId: string) => {
      return bookmarks.has(traceId);
    },
    [bookmarks],
  );

  return {
    bookmarks,
    toggleBookmark,
    isBookmarked,
    clearBookmarks,
  };
}