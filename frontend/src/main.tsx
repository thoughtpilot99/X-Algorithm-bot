import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api";
import "./index.css";
import AccountPage from "./pages/AccountPage";
import AlgorithmPage from "./pages/AlgorithmPage";
import ComparePage from "./pages/ComparePage";

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 5 * 60_000, retry: 1 } } });

function Shell() {
  const accounts = useQuery({ queryKey: ["accounts"], queryFn: api.accounts });
  const reports = useQuery({ queryKey: ["reports"], queryFn: api.reports });
  const link = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900" : "hover:bg-slate-200 dark:hover:bg-slate-800"}`;
  const first = accounts.data?.[0]?.handle;
  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-2 px-4 py-2">
          <span className="mr-3 text-sm font-semibold">X Audit</span>
          {accounts.data?.map((a) => (
            <NavLink key={a.handle} to={`/a/${a.handle}/overview`} className={link}>{a.name}</NavLink>
          ))}
          <NavLink to="/compare" className={link}>Compare</NavLink>
          <NavLink to="/algorithm" className={link}>Algorithm research</NavLink>
          <details className="relative ml-auto text-sm">
            <summary className="btn cursor-pointer list-none">Reports ▾</summary>
            <div className="absolute right-0 mt-1 max-h-96 w-80 overflow-y-auto rounded-lg border border-slate-200 bg-white p-2 text-xs shadow-lg dark:border-slate-700 dark:bg-slate-900">
              {reports.data?.filter((r) => /\.(pdf|html)$/.test(r.name)).map((r) => (
                <a key={r.url} className="block rounded px-2 py-1 hover:bg-slate-100 dark:hover:bg-slate-800" href={r.url} target="_blank" rel="noreferrer">{r.name}</a>
              ))}
              <div className="mt-1 border-t border-slate-200 pt-1 muted dark:border-slate-700">CSV</div>
              {reports.data?.filter((r) => r.name.endsWith(".csv")).map((r) => (
                <a key={r.url} className="block rounded px-2 py-1 hover:bg-slate-100 dark:hover:bg-slate-800" href={r.url}>{r.name}</a>
              ))}
            </div>
          </details>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-5">
        <Routes>
          <Route path="/" element={first ? <Navigate to={`/a/${first}/overview`} replace /> : <div className="muted text-sm">Loading…</div>} />
          <Route path="/a/:handle" element={<Navigate to="overview" replace />} />
          <Route path="/a/:handle/:section" element={<AccountPage />} />
          <Route path="/compare" element={<ComparePage />} />
          <Route path="/algorithm" element={<AlgorithmPage />} />
        </Routes>
      </main>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
