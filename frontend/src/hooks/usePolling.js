import { useEffect, useRef } from "react";

export const POLLING_INTERVAL_MS = 30_000;

export default function usePolling(callback, interval = POLLING_INTERVAL_MS) {
  const callbackRef = useRef(callback);
  const inFlightRef = useRef(false);

  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const poll = async () => {
      if (document.visibilityState !== "visible" || inFlightRef.current) return;
      inFlightRef.current = true;
      try {
        await callbackRef.current();
      } catch {
        // Polling is best-effort; the page owns user-facing error handling.
      } finally {
        inFlightRef.current = false;
      }
    };

    const timer = window.setInterval(poll, interval);
    return () => window.clearInterval(timer);
  }, [interval]);
}
