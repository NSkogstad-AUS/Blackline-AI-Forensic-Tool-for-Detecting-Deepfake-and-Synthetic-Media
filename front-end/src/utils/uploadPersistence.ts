// Utility for persisting File objects in IndexedDB so uploads survive page navigation
// (Metadata is stored in localStorage separately.)
// This is intentionally lightweight to avoid adding a dependency.

const DB_NAME = 'bl_uploads_db';
const STORE = 'files';
let dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
    req.onerror = () => reject(req.error || new Error('IndexedDB open error'));
    req.onsuccess = () => resolve(req.result);
  });
  return dbPromise;
}

export async function persistFile(id: string, file: File): Promise<void> {
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.onabort = () => reject(tx.error || new Error('tx aborted'));
      tx.onerror = () => reject(tx.error || new Error('tx error'));
      tx.oncomplete = () => resolve();
      tx.objectStore(STORE).put(file, id);
    });
  } catch (e) {
    // swallow errors (private / incognito modes may block IDB)
    // eslint-disable-next-line no-console
    console.warn('[uploadPersistence] persistFile failed', e);
  }
}

export async function loadFile(id: string): Promise<File | undefined> {
  try {
    const db = await openDB();
    return await new Promise<File | undefined>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      tx.onabort = () => reject(tx.error || new Error('tx abort'));
      tx.onerror = () => reject(tx.error || new Error('tx error'));
      const req = tx.objectStore(STORE).get(id);
      req.onsuccess = () => resolve(req.result as File | undefined);
      req.onerror = () => reject(req.error || new Error('get error'));
    });
  } catch {
    return undefined;
  }
}

export async function removeFile(id: string): Promise<void> {
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.onabort = () => reject(tx.error || new Error('tx abort'));
      tx.onerror = () => reject(tx.error || new Error('tx error'));
      tx.oncomplete = () => resolve();
      tx.objectStore(STORE).delete(id);
    });
  } catch {}
}

// Remove all files whose key starts with a given prefix. Used to clean up
// per-page uploads when a File Analysis page is deleted. Supports both the
// current namespaced format `${user}::${pageKey}::id` and the legacy
// `${pageKey}::id` format.
export async function removeByPrefix(prefix: string): Promise<void> {
  try {
    const db = await openDB();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      const store = tx.objectStore(STORE);
      const req = store.openKeyCursor();
      req.onerror = () => reject(req.error || new Error('cursor error'));
      req.onsuccess = () => {
        const cursor = req.result as IDBCursor | null;
        if (!cursor) return; // done
        const keyAny = cursor.key as any;
        const key = typeof keyAny === 'string' ? keyAny : String(keyAny);
        if (key.startsWith(prefix)) {
          try { store.delete(cursor.key); } catch {}
        }
        cursor.continue();
      };
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || new Error('tx error'));
      tx.onabort = () => reject(tx.error || new Error('tx abort'));
    });
  } catch {}
}

// Convenience for clearing all persisted upload state for a page across both
// IDB and localStorage. `username` should be the authenticated username or
// 'guest'. This function removes entries for the current v4 key and legacy v3.
export async function clearPageUploads(pageKey: string, username?: string | null) {
  const ns = (username && username.trim()) ? username.trim() : 'guest';
  // IDB: remove both namespaced and legacy
  await removeByPrefix(`${ns}::${pageKey}::`);
  await removeByPrefix(`${pageKey}::`); // legacy pre-namespacing
  // localStorage keys
  try {
    const v4 = `bl_uploadItems_${ns}_${pageKey}_v4`;
    const v3 = `bl_uploadItems_${pageKey}_v3`;
    localStorage.removeItem(v4);
    localStorage.removeItem(v3);
  } catch {}
}
