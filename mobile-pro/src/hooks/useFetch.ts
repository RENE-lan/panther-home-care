import { useState, useEffect, useCallback } from 'react';
export function useFetch<T = any>(fn: () => Promise<T>, deps: any[] = []) {
  const [data, setData] = useState<T | null>(null); const [loading, setLoading] = useState(false);
  const load = useCallback(async () => { setLoading(true); try { setData(await fn()); } catch (e) {} setLoading(false); }, deps);
  useEffect(() => { load(); }, deps);
  return { data, loading, refresh: load };
}
