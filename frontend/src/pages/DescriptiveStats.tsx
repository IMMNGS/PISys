import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchInsightSummary,
  type InsightSummaryResponse,
} from "../api/client";
import DistributionChart from "../components/DistributionChart";

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric-card">
      <div className="metric-card-label">{label}</div>
      <div className="metric-card-value">
        {new Intl.NumberFormat().format(value)}
      </div>
    </div>
  );
}

export default function DescriptiveStats() {
  const [data, setData] = useState<InsightSummaryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [testType, setTestType] = useState("");

  const filters = useMemo(
    () => ({
      start_date: startDate,
      end_date: endDate,
      test_type: testType,
    }),
    [endDate, startDate, testType],
  );

  const load = useCallback(async (nextFilters: typeof filters) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchInsightSummary(nextFilters);
      setData(result);
    } catch (e: unknown) {
      setError(
        e instanceof Error ? e.message : "Failed to load descriptive stats",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load({ start_date: "", end_date: "", test_type: "" });
  }, [load]);

  const exportJson = () => {
    if (!data) return;
    const payload = JSON.stringify(data, null, 2);
    const blob = new Blob([payload], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `descriptive_stats${startDate || endDate || testType ? "_filtered" : ""}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportCsv = () => {
    if (!data) return;
    const rows: string[] = ["section,label,count"];
    const pushRows = (
      section: string,
      items: Array<{ label: string; count: number }>,
    ) => {
      items.forEach((item) => {
        const label = String(item.label ?? "").replace(/"/g, '""');
        rows.push(
          `${JSON.stringify(section)},${JSON.stringify(label)},${item.count}`,
        );
      });
    };

    pushRows("sex", data.demographic_distribution.sex);
    pushRows("age", data.demographic_distribution.age);
    pushRows("ethnicity", data.demographic_distribution.ethnicity);
    pushRows("test_type", data.demographic_distribution.test_type);
    pushRows("vcf_file_size", data.vcf_distribution.file_size);
    pushRows(
      "vcf_chromosome",
      data.vcf_content_distribution.chromosome.map((row) => ({
        label: row.chromosome,
        count: row.count,
      })),
    );
    pushRows("vcf_variant_type", data.vcf_content_distribution.variant_type);
    pushRows(
      "vcf_by_patient",
      data.vcf_content_distribution.by_patient.map((row) => ({
        label: row.lab_number,
        count: row.variant_count,
      })),
    );
    pushRows(
      "chromosome",
      data.chromosome_distribution.map((row) => ({
        label: row.chromosome,
        count: row.count,
      })),
    );
    pushRows(
      "gene",
      data.top_genes.map((row) => ({ label: row.gene, count: row.count })),
    );
    pushRows(
      "keyword",
      data.top_keywords.map((row) => ({
        label: row.keyword,
        count: row.count,
      })),
    );
    pushRows(
      "variant",
      data.top_variants.map((row) => ({
        label: row.variant,
        count: row.count,
      })),
    );

    const blob = new Blob([rows.join("\n")], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `descriptive_stats${startDate || endDate || testType ? "_filtered" : ""}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <h2>Descriptive Statistics</h2>
      <p className="text-muted mb-2">
        Local summary of current dataset with chart-based views for demographic
        mix, VCF file metadata, and variant-level patterns.
      </p>

      <div className="card mb-2">
        <div className="card-body">
          <div className="admin-filters">
            <input
              className="form-control"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              aria-label="Start date"
            />
            <input
              className="form-control"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              aria-label="End date"
            />
            <input
              className="form-control"
              placeholder="Test type filter"
              value={testType}
              onChange={(e) => setTestType(e.target.value)}
            />
            <button
              className="btn btn-primary"
              onClick={() => void load(filters)}
              type="button"
            >
              Apply filters
            </button>
            <button
              className="btn btn-outline"
              onClick={() => {
                setStartDate("");
                setEndDate("");
                setTestType("");
                void load({ start_date: "", end_date: "", test_type: "" });
              }}
              type="button"
            >
              Reset
            </button>
            <button
              className="btn btn-outline"
              onClick={exportCsv}
              type="button"
              disabled={!data}
            >
              Export CSV
            </button>
            <button
              className="btn btn-outline"
              onClick={exportJson}
              type="button"
              disabled={!data}
            >
              Export JSON
            </button>
          </div>
          <p className="text-muted mt-1 mb-0">
            Filters apply to patient report dates and recorded test type.
          </p>
        </div>
      </div>

      {loading && <p>Loading statistics…</p>}
      {error && <div className="alert alert-danger">{error}</div>}

      {data && (
        <>
          <div className="metric-grid mb-2">
            <MetricCard label="Patients" value={data.counts.patients} />
            <MetricCard
              label="Total variants"
              value={data.counts.total_variants}
            />
            <MetricCard
              label="Singleton variants"
              value={data.counts.singleton_variants}
            />
            <MetricCard
              label="Trio variants"
              value={data.counts.trio_variants}
            />
            <MetricCard label="VCF files" value={data.counts.vcf_files} />
            <MetricCard
              label="Parsed VCF variants"
              value={data.counts.vcf_content_variants}
            />
            <MetricCard
              label="Readable VCF files"
              value={data.counts.vcf_files_readable}
            />
            <MetricCard
              label="Skipped VCF files"
              value={data.counts.vcf_files_skipped}
            />
          </div>

          <div className="analytics-grid mb-2">
            <DistributionChart
              title="Sex distribution"
              description="Patients grouped by recorded sex in the local database."
              items={data.demographic_distribution.sex}
              maxItems={6}
            />
            <DistributionChart
              title="Age bands"
              description="Age values normalized to years and grouped into broad bands."
              items={data.demographic_distribution.age}
              maxItems={8}
            />
            <DistributionChart
              title="Type of test"
              description="Recorded testing requests across the current patient set."
              items={data.demographic_distribution.test_type}
              maxItems={8}
            />
            <DistributionChart
              title="Ethnicity"
              description="Stored ethnicity values, grouped by the most common labels."
              items={data.demographic_distribution.ethnicity}
              maxItems={8}
            />
          </div>

          <div className="analytics-grid analytics-grid--wide mb-2">
            <DistributionChart
              title="VCF file sizes"
              description="Uploaded VCF metadata grouped into size buckets."
              items={data.vcf_distribution.file_size}
              maxItems={6}
            />
            <DistributionChart
              title="VCF chromosome distribution"
              description="Variant counts extracted directly from uploaded VCF records."
              items={data.vcf_content_distribution.chromosome.map((row) => ({
                label: row.chromosome,
                count: row.count,
              }))}
              maxItems={24}
            />
            <DistributionChart
              title="VCF variant types"
              description="Simple VCF alleles grouped by SNV, insertion, deletion, and related classes."
              items={data.vcf_content_distribution.variant_type}
              maxItems={10}
            />
            <DistributionChart
              title="VCF variants by patient"
              description="Total parsed VCF variants grouped by patient lab number."
              items={data.vcf_content_distribution.by_patient.map((row) => ({
                label: row.lab_number,
                count: row.variant_count,
              }))}
              maxItems={12}
            />
            <DistributionChart
              title="Chromosome distribution"
              description="Variant counts summarized by chromosome from singleton and trio findings."
              items={data.chromosome_distribution.map((row) => ({
                label: row.chromosome,
                count: row.count,
              }))}
              maxItems={24}
            />
            <DistributionChart
              title="Top genes"
              description="Most frequently referenced genes in the current dataset."
              items={data.top_genes.map((row) => ({
                label: row.gene,
                count: row.count,
              }))}
              maxItems={15}
            />
            <DistributionChart
              title="Top keywords"
              description="Common terms extracted from titles, classifications, and review comments."
              items={data.top_keywords.map((row) => ({
                label: row.keyword,
                count: row.count,
              }))}
              maxItems={15}
            />
            <DistributionChart
              title="Top variant entries"
              description="Repeated chr:pos and ref/alt combinations in the local variant set."
              items={data.top_variants.map((row) => ({
                label: row.variant,
                count: row.count,
              }))}
              maxItems={12}
            />
          </div>
        </>
      )}
    </>
  );
}
