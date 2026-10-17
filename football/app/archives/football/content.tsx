"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Dashboard, { type InitialPayloads } from "./dashboard";
import { loadFootballSnapshot } from "./snapshot.mjs";
import { loadFootballPayloads } from "./server";

export default function FootballArchive() {
  const [payloads, setPayloads] = useState<InitialPayloads | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState(false);
  const request = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setRefreshing(true);
    const timeout = window.setTimeout(() => controller.abort(), 20000);
    try {
      const data = await loadFootballPayloads();
      if (!["laliga", "premier", "bundesliga", "ligue1"].every((key) => Array.isArray(data[key as keyof InitialPayloads]?.scorePayload?.events))) throw new Error("Incomplete data");
      if (!controller.signal.aborted) {
        setPayloads(data);
        setRefreshError(false);
      }
    } catch {
      if (request.current === controller) setRefreshError(true);
    } finally {
      window.clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setRefreshing(false);
      }
    }
  }, []);

  useEffect(() => {
    let disposed = false;
    void loadFootballSnapshot().then((data: InitialPayloads) => {
      if (!disposed) {
        setPayloads(data);
        void refresh();
      }
    }).catch(() => {
      if (!disposed) {
        setRefreshError(true);
        void refresh();
      }
    });
    const timer = window.setInterval(() => { if (document.visibilityState === "visible") void refresh(); }, 5 * 60 * 1000);
    return () => {
      disposed = true;
      window.clearInterval(timer);
      request.current?.abort();
      request.current = null;
    };
  }, [refresh]);

  if (!payloads) return <div className="archive-loading" role="status">{refreshError ? <button type="button" onClick={refresh} disabled={refreshing}>{refreshing ? "確認中…" : "読み込めませんでした。もう一度読み込む"}</button> : "サッカー情報を読み込み中…"}</div>;

  return <Dashboard initialPayloads={payloads} onRefresh={refresh} refreshing={refreshing} refreshError={refreshError} />;
}
