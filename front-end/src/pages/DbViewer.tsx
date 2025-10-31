import React, { useEffect, useState } from 'react';
import { getAuthState } from '../state/authStore';
import './DbViewer.css';

interface PublicUser {
  username: string;
  email: string;
  plan: string;
  created_at: number;
}

const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000';

const DbViewer: React.FC = () => {
  const [auth] = useState(getAuthState());
  const [users, setUsers] = useState<PublicUser[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [updatingUser, setUpdatingUser] = useState<string | null>(null);

  const fetchUsers = async () => {
    setLoading(true); setError(null);
    try {
      if (!auth.token) throw new Error('Please login to view database');
      const res = await fetch(`${API_BASE}/api/dev/users`, {
        headers: { Authorization: `Bearer ${auth.token}` }
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setUsers(Array.isArray(data.users) ? data.users : []);
    } catch (e: any) {
      setError(e.message || 'Failed to load users');
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchUsers(); }, []);

  const setUserPlan = async (username: string, plan: 'Admin' | 'Guest') => {
    if (!auth.token) { setError('Please login'); return; }
    setUpdatingUser(username);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/admin/users/${encodeURIComponent(username)}/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${auth.token}` },
        body: JSON.stringify({ plan }),
      });
      if (!res.ok) throw new Error(await res.text());
      // Refresh user list to reflect change
      await fetchUsers();
    } catch (e: any) {
      setError(e.message || 'Failed to update user');
    } finally {
      setUpdatingUser(null);
    }
  };

  return (
    <div className="dbv-wrap">
      <h2 className="dbv-title">Database Viewer</h2>
      <div className="dbv-sub">Read-only list of users from PostgreSQL. Requires login.</div>
      <div className="dbv-bar">
        <button onClick={fetchUsers} disabled={loading} className="dbv-btn">
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
        <div className="dbv-spacer" />
        {auth.user ? (
          <span>Signed in as <b>{auth.user.username}</b> ({auth.user.email})</span>
        ) : (
          <span>Please login to view</span>
        )}
      </div>
      {error && (
        <div className="dbv-error">{error}</div>
      )}
      <div className="dbv-table-wrap">
        <table className="dbv-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Username</th>
              <th>Email</th>
              <th>Plan</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users && users.length > 0 ? users.map((u: PublicUser, i: number) => (
              <tr key={u.username}>
                <td>{i + 1}</td>
                <td>{u.username}</td>
                <td>{u.email}</td>
                <td>{u.plan}</td>
                <td>{new Date(u.created_at * 1000).toLocaleString()}</td>
                <td>
                  {auth.user && u.username !== auth.user.username ? (
                    u.plan === 'Admin' ? (
                      <button
                        className="dbv-action-btn danger"
                        onClick={() => setUserPlan(u.username, 'Guest')}
                        disabled={!!updatingUser}
                        title="Demote to Guest"
                      >{updatingUser === u.username ? 'Updating…' : 'Demote'}</button>
                    ) : (
                      <button
                        className="dbv-action-btn"
                        onClick={() => setUserPlan(u.username, 'Admin')}
                        disabled={!!updatingUser}
                        title="Promote to Admin"
                      >{updatingUser === u.username ? 'Updating…' : 'Make Admin'}</button>
                    )
                  ) : (
                    <span className="dbv-muted">—</span>
                  )}
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan={6} className="dbv-empty">{loading ? 'Loading…' : 'No users found'}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DbViewer;
