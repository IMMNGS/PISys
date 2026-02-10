import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="text-center" style={{ paddingTop: "3rem" }}>
      <h1>Patient Information System</h1>
      <p className="text-muted mt-1">
        Manage Human Phenotype Ontology terms, link them to patients, and select
        cohorts for downstream analysis.
      </p>
      <hr />
      <div className="row mt-2">
        <div className="col-2">
          <div className="card">
            <div className="card-body text-center">
              <h3 className="card-title">Patients</h3>
              <p className="text-muted">
                Filter and select patients, then export data for downstream
                analysis using Python, R, or REST.
              </p>
              <Link to="/select" className="btn btn-primary">
                View Patients
              </Link>
            </div>
          </div>
        </div>
        <div className="col-2">
          <div className="card">
            <div className="card-body text-center">
              <h3 className="card-title">Upload</h3>
              <p className="text-muted">
                Upload VCF files, singleton &amp; trio XLSX spreadsheets, and
                import patient lists.
              </p>
              <Link to="/upload" className="btn btn-outline">
                Upload Files
              </Link>
            </div>
          </div>
        </div>
        <div className="col-2">
          <div className="card">
            <div className="card-body text-center">
              <h3 className="card-title">Report</h3>
              <p className="text-muted">
                Generate clinical .docx reports by lab number with editable
                conclusion, process, and disclaimer.
              </p>
              <Link to="/report" className="btn btn-outline">
                Generate Report
              </Link>
            </div>
          </div>
        </div>
        <div className="col-2">
          <div className="card">
            <div className="card-body text-center">
              <h3 className="card-title">Manage HPO Terms</h3>
              <p className="text-muted">
                Search HPO terms and assign them to patients using side-by-side
                selectors.
              </p>
              <Link to="/manage-hpo" className="btn btn-outline">
                Manage Terms
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
