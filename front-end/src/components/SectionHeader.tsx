import React, { useEffect, useRef, useState } from "react";
import "../pages/FileAnalysis.css";
import "./Sidebar.css"; // reuse item-menu styles
import ConfirmDialog from "./ConfirmDialog";
import IconPickerModal from "./IconPickerModal";
import { subscribe, getAuthState } from "../state/authStore";

interface Props {
  currentPage: string;
  onNavigate: (p: string) => void;
  lastFilePage?: string;
  title?: string;
  // Hide Documents/Reports tabs (e.g., on DB Viewer page)
  hideTabs?: boolean;
  onDeleteCurrent?: (key: string) => void;
  // Optional emoji/icon to show to the left of the title, kept in sync with the sidebar icon
  icon?: string;
  // Optional handler to change the icon (enables clicking the header icon)
  onChangeIcon?: (key: string, icon?: string) => void;
}

const SectionHeader: React.FC<Props> = ({ currentPage, onNavigate, lastFilePage, title, hideTabs, onDeleteCurrent, icon, onChangeIcon }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [iconPickerOpen, setIconPickerOpen] = useState(false);
  const initialPlan = getAuthState().user?.plan || null;
  const [plan, setPlan] = useState<string | null>(initialPlan);

  const activeKey = currentPage && currentPage.startsWith('file') ? currentPage : (lastFilePage || 'file1');

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, []);

  // Reactively reflect auth role changes (e.g., after login/signup)
  useEffect(() => {
    const unsub = subscribe((s) => setPlan(s.user?.plan || null));
    return () => { unsub(); };
  }, []);

  const requestDelete = () => {
    setMenuOpen(false);
    setConfirmOpen(true);
  };

  return (
    <div className="page-content">
      <div className="file-analysis-header">
        {plan && (
          <div className="role-badge" aria-label={`${plan} role`} title={plan}>
            {plan}
          </div>
        )}
        <div className="file-analysis-title">
          {(currentPage.startsWith('file') || currentPage === 'reports') && (
            <span
              className={`title-icon ${onChangeIcon ? 'clickable' : ''}`}
              aria-hidden
              title={onChangeIcon ? 'Change icon' : undefined}
              onClick={() => { if (onChangeIcon) setIconPickerOpen(true); }}
            >{icon || '📁'}</span>
          )}
          {title || 'Dashboard'}
        </div>
        {currentPage !== 'dashboard' && !hideTabs && (
          <div className="file-analysis-tabs">
            <div className={`file-analysis-tab ${currentPage && currentPage.startsWith('file') ? 'active' : ''}`} onClick={() => onNavigate(lastFilePage || 'file1')}>Documents</div>
            <div className={`file-analysis-tab ${currentPage === 'reports' ? 'active' : ''}`} onClick={() => onNavigate('reports')}>Reports</div>
            <div className="file-analysis-tab sidebar-actions-wrap" ref={menuRef}>
              <button
                className="header-more-btn"
                title="More"
                aria-label="More actions"
                onClick={() => setMenuOpen(o => !o)}
                aria-haspopup="menu"
              >…</button>
              {menuOpen && (
                <div className="item-menu" role="menu">
                  <button className="item-menu-btn danger" role="menuitem" onClick={requestDelete}>Delete</button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      <ConfirmDialog
        open={confirmOpen}
        title="Confirm deletion"
        message={`Delete "${title || 'this analysis'}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        danger
        onConfirm={() => { onDeleteCurrent && onDeleteCurrent(activeKey); setConfirmOpen(false); }}
        onCancel={() => setConfirmOpen(false)}
      />
      {onChangeIcon && (
        <IconPickerModal
          isOpen={iconPickerOpen}
          currentIcon={icon}
          onClose={() => setIconPickerOpen(false)}
          onSelect={(ic) => { onChangeIcon(activeKey, ic); setIconPickerOpen(false); }}
        />
      )}
    </div>
  );
};

export default SectionHeader;
