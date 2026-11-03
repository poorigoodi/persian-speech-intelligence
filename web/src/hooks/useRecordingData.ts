import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { JobStatus } from "@/lib/types";

type AsyncState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
};

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof Error) return err.message;
  return "Something went wrong.";
}

const DATA_SCHEMA_REV = 5;

function useLoader<T>(key: string | null, load: (id: string) => Promise<T>): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(DATA_SCHEMA_REV);
  const loadRef = useRef(load);
  loadRef.current = load;

  useEffect(() => {
    if (!key) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    loadRef
      .current(key)
      .then((value) => {
        if (cancelled) return;
        setData(value);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setData(null);
        setError(errorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [key, nonce]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);
  return { data, loading, error, reload };
}

export function useTranscript(id: string | null) {
  return useLoader(id, api.transcript);
}

export function useAnalysis(id: string | null) {
  return useLoader(id, api.analysis);
}

export function useRecordingDetail(id: string | null) {
  return useLoader(id, api.getRecording);
}

export function useJobStatus(id: string | null) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) {
      setStatus(null);
      setError(null);
      return;
    }
    let cancelled = false;
    let timer: number | undefined;

    const tick = async () => {
      try {
        const next = await api.getStatus(id);
        if (cancelled) return;
        setStatus(next);
        setError(null);
        if (next.status === "pending" || next.status === "processing") {
          timer = window.setTimeout(tick, 2500);
        }
      } catch (err) {
        if (cancelled) return;
        setError(errorMessage(err));
        timer = window.setTimeout(tick, 5000);
      }
    };

    void tick();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [id]);

  return { status, error };
}
