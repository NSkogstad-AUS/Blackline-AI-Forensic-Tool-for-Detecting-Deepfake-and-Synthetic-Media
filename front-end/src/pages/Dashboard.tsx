import React from "react";
import "./PageStyles.css";
import "./Reports.css"; // reuse card styles for page-level cards
import { getAnalysesForPage } from '../state/analysisStore';

type PageEntry = { key: string; label: string; icon?: string };

const Dashboard: React.FC<{ pages: PageEntry[] }> = ({ pages }) => {
  const filePages = pages.filter(p => p.key !== 'dashboard');
  return (
    <div className="page-content">
      {/* File analysis page cards - appear on Dashboard for quick navigation */}
      <div className="dashboard-page-cards">
        <div className="file-analysis-pages">
          {filePages.map(p => {
            const list = getAnalysesForPage(p.key);
            const count = list.length;
            const latest = count ? new Date(Math.max(...list.map(a => a.analyzedAt))) : null;
            const latestName = count ? list.reduce((acc, a) => acc.analyzedAt > a.analyzedAt ? acc : a).fileName : '';
            const avgLikelihood = (() => {
              const vals = list
                .map(a => a.summary?.deepfake_likelihood)
                .filter((v): v is number => typeof v === 'number' && !isNaN(v));
              if (!vals.length) return null;
              const avg = vals.reduce((s, v) => s + v, 0) / vals.length;
              return Math.round(avg * 100); // percent 0..100
            })();
            return (
              <div
                key={p.key}
                className="file-page-card"
                onClick={() => { try { window.dispatchEvent(new CustomEvent('bl:navigate', { detail: { page: p.key } })); } catch {} }}
                role="button"
                tabIndex={0}
              >
                <div className="file-page-card-title">{p.label}</div>
                <div className="file-page-meta">
                  <div className="meta-row"><span className="pill">{count}</span> analyses</div>
                  <div className="meta-row">
                    {avgLikelihood === null ? <span className="muted">No likelihood yet</span> : <>
                      Avg likelihood <span className={`pill ${avgLikelihood >= 70 ? 'alert' : ''}`}>{avgLikelihood}%</span>
                    </>}
                  </div>
                  <div className="meta-row">
                    {latest ? <>
                      Last run <span className="pill">{latest.toLocaleDateString()}</span>
                    </> : <span className="muted">No runs yet</span>}
                  </div>
                  {latest && latestName && (
                    <div className="meta-row truncated" title={latestName}>Recent file: {latestName}</div>
                  )}
                </div>
                <div className="file-page-card-body">
                  <div className="file-page-count">{count} analyses</div>
                  <div className="file-page-cta">Open</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
