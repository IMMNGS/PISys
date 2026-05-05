import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import Navbar from "./components/Navbar";
import { AuthProvider } from "./auth/authContext";
import { useAuth } from "./auth/useAuth";
import Home from "./pages/Home";
import PatientDetail from "./pages/PatientDetail";
import SelectPatients from "./pages/SelectPatients";
import ManageHpo from "./pages/ManageHpo";
import Upload from "./pages/Upload";
import Report from "./pages/Report";
import DescriptiveStats from "./pages/DescriptiveStats";
import Login from "./pages/Login";
import QcOverview from "./pages/QcOverview";
import AdminAudit from "./pages/AdminAudit";

function AuthGate() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="container auth-loading">Loading…</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

function AdminGate() {
  const { isAdmin } = useAuth();
  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}

function AppChrome() {
  return (
    <>
      <Navbar />
      <main className="container">
        <Outlet />
      </main>
      <footer>
        <small>Patient Information System © 2026</small>
      </footer>
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<AuthGate />}>
            <Route element={<AppChrome />}>
              <Route path="/" element={<Home />} />
              <Route path="/patients/:id" element={<PatientDetail />} />
              <Route path="/select" element={<SelectPatients />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/report" element={<Report />} />
              <Route path="/manage-hpo" element={<ManageHpo />} />
              <Route path="/qc" element={<QcOverview />} />
              <Route path="/stats" element={<DescriptiveStats />} />
              <Route element={<AdminGate />}>
                <Route path="/admin" element={<AdminAudit />} />
              </Route>
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
