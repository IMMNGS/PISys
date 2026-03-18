import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import PatientDetail from "./pages/PatientDetail";
import SelectPatients from "./pages/SelectPatients";
import ManageHpo from "./pages/ManageHpo";
import Upload from "./pages/Upload";
import Report from "./pages/Report";
import DescriptiveStats from "./pages/DescriptiveStats";
import ExplainTerms from "./pages/ExplainTerms";

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/patients/:id" element={<PatientDetail />} />
          <Route path="/select" element={<SelectPatients />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/report" element={<Report />} />
          <Route path="/manage-hpo" element={<ManageHpo />} />
          <Route path="/stats" element={<DescriptiveStats />} />
          <Route path="/explain" element={<ExplainTerms />} />
        </Routes>
      </main>
      <footer>
        <small>Patient Information System © 2026</small>
      </footer>
    </BrowserRouter>
  );
}
