import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="text-center" style={{ paddingTop: "3rem" }}>
      <h1 style={{ fontFamily: "'Playfair Display', Georgia, serif", fontSize: "2.5rem", fontWeight: 800, color: "#312e81" }}>
        Patient Information System
      </h1>
      <p className="text-muted mt-1" style={{ maxWidth: "540px", margin: "0.5rem auto 0", textWrap: "balance" as any }}>
        Manage disease terms, link them to patients, and select cohorts for
        downstream analysis.
      </p>
      <hr />
      <div className="row" style={{ marginTop: "2rem", justifyContent: "center" }}>
        <div style={{ flex: "1 1 260px", maxWidth: "280px" }}>
          <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <div className="card-body text-center" style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
              <h3 className="card-title">Patients</h3>
              <p className="text-muted" style={{ flex: 1 }}>
                Filter and select patients, then export data for analysis using Python, R, or REST.
              </p>
              <Link to="/select" className="btn btn-primary" style={{ marginTop: "auto" }}>
                View Patients
              </Link>
            </div>
          </div>
        </div>
        <div style={{ flex: "1 1 260px", maxWidth: "280px" }}>
          <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <div className="card-body text-center" style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
              <h3 className="card-title">Upload</h3>
              <p className="text-muted" style={{ flex: 1 }}>
                Upload VCF files, singleton &amp; trio XLSX spreadsheets, and import patient lists.
              </p>
              <Link to="/upload" className="btn btn-outline" style={{ marginTop: "auto" }}>
                Upload Files
              </Link>
            </div>
          </div>
        </div>
        <div style={{ flex: "1 1 260px", maxWidth: "280px" }}>
          <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <div className="card-body text-center" style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
              <h3 className="card-title">Report</h3>
              <p className="text-muted" style={{ flex: 1 }}>
                Generate clinical .docx reports with editable conclusion, process, and disclaimer.
              </p>
              <Link to="/report" className="btn btn-outline" style={{ marginTop: "auto" }}>
                Generate Report
              </Link>
            </div>
          </div>
        </div>
        <div style={{ flex: "1 1 260px", maxWidth: "280px" }}>
          <div className="card" style={{ height: "100%", display: "flex", flexDirection: "column" }}>
            <div className="card-body text-center" style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
              <h3 className="card-title">Manage Disease Terms</h3>
              <p className="text-muted" style={{ flex: 1 }}>
                Search disease terms and assign
                them to patients.
              </p>
              <Link to="/manage-hpo" className="btn btn-outline" style={{ marginTop: "auto" }}>
                Manage Terms
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
