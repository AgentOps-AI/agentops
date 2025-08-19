'use client';

import { openDB, DBSchema, IDBPDatabase, deleteDB } from 'idb';
import { ISessionAndStats } from './interfaces';
import { addBreadcrumb, captureException } from '@sentry/nextjs';

interface DB extends DBSchema {
  sessions: {
    key: string;
    value: ISessionAndStats;
    indexes: { init_timestamp: string };
  };
}

async function getDB(): Promise<IDBPDatabase<DB>> {
  return openDB<DB>('AgentOpsCache', 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('sessions')) {
        const store = db.createObjectStore('sessions', { keyPath: 'id' });
        store.createIndex('init_timestamp', 'init_timestamp');
      }
    },
  });
}

export async function setIdbSessions(sessions: ISessionAndStats[]): Promise<void> {
  try {
    const db = await getDB();
    const tx = db.transaction('sessions', 'readwrite');
    const store = tx.objectStore('sessions');

    for (const session of sessions) {
      store.put(session);
    }

    return tx.done;
  } catch (e) {
    console.error(e);
    addBreadcrumb({
      category: 'Sessions',
      data: { sessions: sessions },
    });
    captureException(e);
  }
}

export async function getIdbSessions(): Promise<ISessionAndStats[]>;
export async function getIdbSessions(id: string): Promise<ISessionAndStats | undefined>;
export async function getIdbSessions(id?: string) {
  const db = await getDB();
  if (id) {
    return db.get('sessions', id);
  }
  const sessions = db.transaction('sessions').store.index('init_timestamp');
  return (await sessions.getAll()).reverse();
}

export async function clearIdbSessions(): Promise<void> {
  const db = await getDB();
  const tx = db.transaction('sessions', 'readwrite');
  const store = tx.objectStore('sessions');
  store.clear();

  return tx.done;
}

export async function deleteIdbSessions(ids: string[]): Promise<void> {
  const db = await getDB();
  const tx = db.transaction('sessions', 'readwrite');
  const store = tx.objectStore('sessions');

  for (const id of ids) {
    store.delete(id);
  }

  return tx.done;
}

export async function deleteCache() {
  await deleteDB('AgentOpsCache');
}

export function setOnboardingSkipped(isSkipped: boolean): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('onboardingSkipped', isSkipped.toString());
  }
}

export function getOnboardingSkipped(): boolean | undefined {
  if (typeof window !== 'undefined') {
    const onboardingSkipped = JSON.parse(localStorage.getItem('onboardingSkipped') ?? 'null');
    return JSON.parse(onboardingSkipped) ?? undefined;
  }
  return undefined;
}

export function setTutorialSkipped(isSkippedTutorial: boolean): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('tutorialSkipped', isSkippedTutorial.toString());
  }
}
export function getTutorialSkipped(): boolean {
  if (typeof window !== 'undefined') {
    return JSON.parse(localStorage.getItem('tutorialSkipped') || 'false');
  }
  return false;
}
