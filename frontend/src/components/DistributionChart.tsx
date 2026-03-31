type DistributionItem = {
  label: string;
  count: number;
};

type DistributionChartProps = {
  title: string;
  description?: string;
  items: DistributionItem[];
  emptyMessage?: string;
  maxItems?: number;
  valueFormatter?: (value: number) => string;
};

function formatCount(value: number) {
  return new Intl.NumberFormat().format(value);
}

export default function DistributionChart({
  title,
  description,
  items,
  emptyMessage = "No data available.",
  maxItems = 10,
  valueFormatter = formatCount,
}: DistributionChartProps) {
  const visibleItems = items.slice(0, maxItems);
  const maxValue = Math.max(...visibleItems.map((item) => item.count), 0);

  return (
    <div className="chart-card">
      <div className="chart-card-header">
        <div>
          <h4 className="chart-card-title">{title}</h4>
          {description && (
            <p className="chart-card-description">{description}</p>
          )}
        </div>
      </div>

      {visibleItems.length === 0 ? (
        <p className="text-muted chart-empty">{emptyMessage}</p>
      ) : (
        <div className="chart-bars" role="list" aria-label={title}>
          {visibleItems.map((item) => {
            const width = maxValue > 0 ? (item.count / maxValue) * 100 : 0;
            return (
              <div className="chart-bar-row" key={item.label} role="listitem">
                <div className="chart-bar-label" title={item.label}>
                  {item.label}
                </div>
                <div className="chart-bar-track" aria-hidden="true">
                  <div
                    className="chart-bar-fill"
                    style={{ width: `${width}%` }}
                  />
                </div>
                <div className="chart-bar-value">
                  {valueFormatter(item.count)}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
