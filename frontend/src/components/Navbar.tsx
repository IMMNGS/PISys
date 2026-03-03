import { NavLink } from "react-router-dom";

export default function Navbar() {
  return (
    <nav className="navbar">
      <div className="container">
        <NavLink to="/" className="navbar-brand">Patient Information System</NavLink>
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
            <NavLink to="/report">Report</NavLink>
          </li>
          <li>
            <NavLink to="/manage-hpo">Manage Disease Terms</NavLink>
          </li>
        </ul>
      </div>
    </nav>
  );
}
