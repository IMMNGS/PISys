import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

export default function Navbar() {
  const { user, isAdmin, logout } = useAuth();

  return (
    <nav className="navbar">
      <div className="container">
        <NavLink to="/" className="navbar-brand">
          Patient Information System
        </NavLink>
        <ul className="nav-links">
          <li>
            <NavLink to="/" end>
              Home
            </NavLink>
          </li>
          <li>
            <NavLink to="/select">Patients</NavLink>
          </li>
          <li>
            <NavLink to="/upload">Upload</NavLink>
          </li>
          <li>
            <NavLink to="/qc">QC</NavLink>
          </li>
          <li>
            <NavLink to="/report">Report</NavLink>
          </li>
          <li>
            <NavLink to="/manage-hpo">Manage Disease Terms</NavLink>
          </li>
          <li>
            <NavLink to="/stats">Descriptive Stats</NavLink>
          </li>
          {isAdmin && (
            <li>
              <NavLink to="/admin">Admin</NavLink>
            </li>
          )}
        </ul>
        <div className="navbar-user-area">
          <span className="navbar-user-chip">
            {user?.full_name || user?.username || "Signed in"}
          </span>
          <button
            className="btn btn-outline-light btn-sm"
            type="button"
            onClick={() => void logout()}
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
