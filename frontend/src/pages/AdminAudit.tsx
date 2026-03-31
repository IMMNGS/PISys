import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { createUser, fetchAuditLogs, fetchUsers } from "../api/client";
import type { AuditLogItem, AuthUser } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function AdminAudit() {
  const { user } = useAuth();
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [usernameFilter, setUsernameFilter] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [targetFilter, setTargetFilter] = useState("");
  const [userForm, setUserForm] = useState({
    username: "",
    full_name: "",
    password: "",
    role: "user" as "user" | "admin",
  });
  const [savingUser, setSavingUser] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [audit, userList] = await Promise.all([
        fetchAuditLogs({ limit: 200, username: usernameFilter, action: actionFilter, target: targetFilter }),
        fetchUsers(),
      ]);
      setLogs(audit.items);
      setUsers(userList.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  }, [actionFilter, targetFilter, usernameFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const summary = useMemo(() => {
    const uniqueUsers = new Set(logs.map((item) => item.username));
    return {
      events: logs.length,
      users: uniqueUsers.size,
      accounts: users.length,
    };
  }, [logs, users]);

  const handleCreateUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSavingUser(true);
    setError(null);
    try {
      await createUser(userForm);
      setUserForm({ username: "", full_name: "", password: "", role: "user" });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setSavingUser(false);
    }
  };

  return (
    <div className="admin-page">
      <div className="flex-between admin-header">
        <div>
          <h2>Administrator Dashboard</h2>
          <p className="text-muted">
            Monitor data access, login activity, and account creation.
          </p>
        </div>
        <div className="admin-user-badge">
          Signed in as {user?.full_name || user?.username || "admin"}
        </div>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <div className="row admin-stats">
        <div className="card admin-stat-card">
          <div className="card-body">
            <strong>{summary.events}</strong>
            <span>Audit events</span>
          </div>
        </div>
        <div className="card admin-stat-card">
          <div className="card-body">
            <strong>{summary.users}</strong>
            <span>Users in logs</span>
          </div>
        </div>
        <div className="card admin-stat-card">
          <div className="card-body">
            <strong>{summary.accounts}</strong>
            <span>Active accounts</span>
          </div>
        </div>
      </div>

      <div className="card mb-2">
        <div className="card-body">
          <h3 className="mb-1">Create user</h3>
          <form className="admin-form" onSubmit={handleCreateUser}>
            <input
              className="form-control"
              placeholder="Username"
              value={userForm.username}
              onChange={(e) => setUserForm((prev) => ({ ...prev, username: e.target.value }))}
              required
            />
            <input
              className="form-control"
              placeholder="Full name"
              value={userForm.full_name}
              onChange={(e) => setUserForm((prev) => ({ ...prev, full_name: e.target.value }))}
            />
            <input
              className="form-control"
              type="password"
              placeholder="Temporary password"
              value={userForm.password}
              onChange={(e) => setUserForm((prev) => ({ ...prev, password: e.target.value }))}
              required
            />
            <select
              className="form-control"
              value={userForm.role}
              onChange={(e) => setUserForm((prev) => ({ ...prev, role: e.target.value as "user" | "admin" }))}
            >
              <option value="user">User</option>
              <option value="admin">Administrator</option>
            </select>
            <button className="btn btn-primary" type="submit" disabled={savingUser}>
              {savingUser ? "Creating…" : "Create user"}
            </button>
          </form>
        </div>
      </div>

      <div className="card mb-2">
        <div className="card-body">
          <div className="admin-filters">
            <input className="form-control" placeholder="Filter by username" value={usernameFilter} onChange={(e) => setUsernameFilter(e.target.value)} />
            <input className="form-control" placeholder="Filter by action" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} />
            <input className="form-control" placeholder="Filter by target" value={targetFilter} onChange={(e) => setTargetFilter(e.target.value)} />
            <button className="btn btn-outline" onClick={loadData} type="button">
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="card mb-2">
        <div className="card-body">
          <h3 className="mb-1">Access log</h3>
          {loading ? (
            <p className="text-muted">Loading audit events…</p>
          ) : logs.length === 0 ? (
            <p className="text-muted">No audit events recorded yet.</p>
          ) : (
            <div className="table-wrap admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Target</th>
                    <th>Method</th>
                    <th>Status</th>
                    <th>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((item) => (
                    <tr key={item.id}>
                      <td>{item.created_at ? new Date(item.created_at).toLocaleString() : "—"}</td>
                      <td>{item.username}</td>
                      <td>{item.action}</td>
                      <td>{item.target}</td>
                      <td>{item.method}</td>
                      <td>{item.status_code}</td>
                      <td>{item.remote_addr ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-body">
          <h3 className="mb-1">Accounts</h3>
          <div className="table-wrap admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Full name</th>
                  <th>Role</th>
                  <th>Active</th>
                  <th>Last login</th>
                </tr>
              </thead>
              <tbody>
                {users.map((account) => (
                  <tr key={account.id}>
                    <td>{account.username}</td>
                    <td>{account.full_name ?? "—"}</td>
                    <td>{account.role}</td>
                    <td>{account.is_active ? "Yes" : "No"}</td>
                    <td>{account.last_login_at ? new Date(account.last_login_at).toLocaleString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
