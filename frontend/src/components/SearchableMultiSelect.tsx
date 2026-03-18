import { useState, useRef, useEffect, useCallback } from "react";

export interface MultiSelectItem {
  id: number;
  label: string;
}

export interface MultiSelectFetchResult {
  items: MultiSelectItem[];
  total: number;
}

interface SearchableMultiSelectProps {
  selectedIds: Set<number>;
  onToggle: (id: number) => void;
  /** Server-side paginated fetch: returns items for the given search, limit, offset */
  fetchOptions: (
    search: string,
    limit: number,
    offset: number,
  ) => Promise<MultiSelectFetchResult>;
  placeholder?: string;
  debounceMs?: number;
  /** Label used in the "Load more …" button, e.g. "HPO terms" or "patients" */
  itemLabel?: string;
  /** How many items to fetch initially (default 20) */
  pageSize?: number;
  /** How many more items to fetch per "Load more" click (default 100) */
  loadMoreSize?: number;
  /** Optional action to create/select a new entry from current search text */
  onCreateFromSearch?: (text: string) => Promise<MultiSelectItem | null>;
  createLabelPrefix?: string;
}

export default function SearchableMultiSelect({
  selectedIds,
  onToggle,
  fetchOptions,
  placeholder = "Search…",
  debounceMs = 250,
  itemLabel = "items",
  pageSize = 20,
  loadMoreSize = 100,
  onCreateFromSearch,
  createLabelPrefix = "Add",
}: SearchableMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [options, setOptions] = useState<MultiSelectItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [creating, setCreating] = useState(false);
  const [initialLoaded, setInitialLoaded] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const [menuPos, setMenuPos] = useState<{
    top: number;
    left: number;
    width: number;
  }>({
    top: 0,
    left: 0,
    width: 260,
  });

  const remaining = total - options.length;

  // close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  // focus input when opened
  useEffect(() => {
    if (open) {
      if (triggerRef.current) {
        const rect = triggerRef.current.getBoundingClientRect();
        setMenuPos({
          top: rect.bottom + 2,
          left: rect.left,
          width: Math.max(260, rect.width),
        });
      }
      inputRef.current?.focus();
    }
  }, [open]);

  // fetch first page (immediate or debounced)
  const loadOptions = useCallback(
    (q: string, immediate = false) => {
      clearTimeout(timerRef.current);
      const doFetch = async () => {
        setLoading(true);
        try {
          const result = await fetchOptions(q, pageSize, 0);
          setOptions(result.items);
          setTotal(result.total);
        } catch {
          setOptions([]);
          setTotal(0);
        } finally {
          setLoading(false);
        }
      };
      if (immediate) {
        doFetch();
      } else {
        timerRef.current = setTimeout(doFetch, debounceMs);
      }
    },
    [fetchOptions, debounceMs, pageSize],
  );

  // load more from server
  const handleLoadMore = useCallback(async () => {
    setLoadingMore(true);
    try {
      const result = await fetchOptions(search, loadMoreSize, options.length);
      setOptions((prev) => [...prev, ...result.items]);
      setTotal(result.total);
    } catch {
      // keep what we have
    } finally {
      setLoadingMore(false);
    }
  }, [fetchOptions, search, loadMoreSize, options.length]);

  // load initial options once when first opened
  useEffect(() => {
    if (open && !initialLoaded) {
      loadOptions("", true);
      setInitialLoaded(true);
    }
  }, [open, initialLoaded, loadOptions]);

  // reset when closed
  useEffect(() => {
    if (!open) setInitialLoaded(false);
  }, [open]);

  const handleSearchChange = (val: string) => {
    setSearch(val);
    loadOptions(val);
  };

  const handleTriggerClick = () => {
    if (open) {
      setOpen(false);
    } else {
      setSearch("");
      setOpen(true);
    }
  };

  const canCreate = !!onCreateFromSearch && search.trim().length > 0;

  const handleCreate = async () => {
    if (!onCreateFromSearch) return;
    const text = search.trim();
    if (!text) return;
    setCreating(true);
    try {
      const item = await onCreateFromSearch(text);
      if (!item) return;
      setOptions((prev) => {
        if (prev.some((p) => p.id === item.id)) return prev;
        return [item, ...prev];
      });
      setTotal((prev) => prev + 1);
      onToggle(item.id);
      setSearch("");
      loadOptions("", true);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="searchable-select" ref={ref}>
      <div
        ref={triggerRef}
        className="searchable-select-box"
        onClick={handleTriggerClick}
      >
        {open ? (
          <input
            ref={inputRef}
            type="text"
            className="searchable-select-input"
            placeholder={
              selectedIds.size > 0
                ? `${selectedIds.size} selected — type to search`
                : placeholder
            }
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className={selectedIds.size > 0 ? "" : "text-muted"}>
            {selectedIds.size > 0
              ? `${selectedIds.size} selected`
              : placeholder}
          </span>
        )}
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.35rem",
            flexShrink: 0,
          }}
        >
          <span className="dropdown-arrow">{open ? "▲" : "▼"}</span>
        </span>
      </div>

      {open && (
        <div
          className="dropdown-select-menu"
          style={{
            position: "fixed",
            top: menuPos.top,
            left: menuPos.left,
            width: menuPos.width,
          }}
        >
          <ul className="dropdown-select-list">
            {loading && <li className="dropdown-select-empty">Loading…</li>}
            {!loading && options.length === 0 && (
              <li className="dropdown-select-empty">
                {search ? "No matches found" : `No ${itemLabel} available`}
              </li>
            )}
            {!loading &&
              options.map((item) => (
                <li
                  key={item.id}
                  className={`dropdown-select-item${selectedIds.has(item.id) ? " selected" : ""}`}
                  onClick={() => onToggle(item.id)}
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.has(item.id)}
                    readOnly
                    tabIndex={-1}
                  />
                  <span>{item.label}</span>
                </li>
              ))}
            {!loading && canCreate && (
              <li
                className="dropdown-select-item"
                onClick={handleCreate}
                style={{ fontStyle: "italic" }}
              >
                <span>
                  {creating
                    ? "Creating…"
                    : `${createLabelPrefix}: "${search.trim()}"`}
                </span>
              </li>
            )}
          </ul>
          {!loading && remaining > 0 && (
            <button
              type="button"
              className="dropdown-select-load-more"
              disabled={loadingMore}
              onClick={(e) => {
                e.stopPropagation();
                handleLoadMore();
              }}
            >
              {loadingMore
                ? "Loading…"
                : `Load more ${itemLabel} (${remaining} remaining)`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
