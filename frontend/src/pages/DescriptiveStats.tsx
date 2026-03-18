import { useEffect, useState } from "react";
import {
  fetchInsightSummary,
  type InsightSummaryResponse,
} from "../api/client";

export default function DescriptiveStats() {
  const [data, setData] = useState<InsightSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // TODO(analytics-filters): Add UI controls for date range and type_of_test,
    // then pass query params to /api/insights/summary.
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchInsightSummary();
        setData(result);
      } catch (e: unknown) {
        setError(
          e instanceof Error ? e.message : "Failed to load descriptive stats",
        );
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <>
      <h2>Descriptive Statistics</h2>
      <p className="text-muted mb-2">
        Local summary of current dataset: variant frequencies, chromosome
        distribution, top genes, and keyword trends from variant annotations.
      </p>

      {loading && <p>Loading statistics…</p>}
      {error && <div className="alert alert-danger">{error}</div>}

      {data && (
        <>
          {/* TODO(charts): Replace/augment tables with local chart components
              (bar charts for chromosomes/genes/keywords). */}
          <div className="card mb-2">
            <div className="card-header primary">Dataset Summary</div>
            <div className="card-body">
              <div className="row mb-1">
                <div className="col-2">
                  <strong>Patients:</strong> {data.counts.patients}
                </div>
                <div className="col-2">
                  <strong>Total variants:</strong> {data.counts.total_variants}
                </div>
              </div>
              <div className="row mb-1">
                <div className="col-2">
                  <strong>Singleton variants:</strong>{" "}
                  {data.counts.singleton_variants}
                </div>
                <div className="col-2">
                  <strong>Trio variants:</strong> {data.counts.trio_variants}
                </div>
              </div>
              <div className="row">
                <div className="col-2">
                  <strong>VCF files:</strong> {data.counts.vcf_files}
                </div>
              </div>
            </div>
          </div>

          <div className="card mb-2">
            <div className="card-header primary">Chromosome Distribution</div>
            <div className="card-body table-wrap table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Chromosome</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {data.chromosome_distribution.map((row) => (
                    <tr key={row.chromosome}>
                      <td>{row.chromosome}</td>
                      <td>{row.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="row mb-2">
            <div className="col-2">
              <div className="card">
                <div className="card-header primary">Top Genes</div>
                <div className="card-body table-wrap table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Gene</th>
                        <th>Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_genes.slice(0, 15).map((row) => (
                        <tr key={row.gene}>
                          <td>{row.gene}</td>
                          <td>{row.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <div className="col-2">
              <div className="card">
                <div className="card-header primary">Top Keywords</div>
                <div className="card-body table-wrap table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Keyword</th>
                        <th>Count</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.top_keywords.slice(0, 15).map((row) => (
                        <tr key={row.keyword}>
                          <td>{row.keyword}</td>
                          <td>{row.count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header primary">Top Variant Entries</div>
            <div className="card-body table-wrap table-scroll">
              {/* TODO(export): Add CSV/JSON export button for current summary payload. */}
              <table>
                <thead>
                  <tr>
                    <th>Variant</th>
                    <th>Count</th>
                  </tr>
                </thead>
                <tbody>
                  {data.top_variants.slice(0, 20).map((row) => (
                    <tr key={row.variant}>
                      <td>{row.variant}</td>
                      <td>{row.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </>
  );
}
