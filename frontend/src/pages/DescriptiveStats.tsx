import { useEffect, useState } from "react";
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
        Local summary of current dataset with chart-based views for demographic
        mix, VCF file metadata, and variant-level patterns.
      </p>

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
