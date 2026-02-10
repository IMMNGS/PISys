import { useState, useRef, useEffect, useCallback } from "react";

interface SearchableSelectProps {
  value: string;
  onChange: (value: string) => void;
  fetchOptions: (search: string) => Promise<string[]>;
  placeholder?: string;
  debounceMs?: number;
}

export default function SearchableSelect({
  value,
  onChange,
  fetchOptions,
  placeholder = "Search…",
  debounceMs = 250,
}: SearchableSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [options, setOptions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoaded, setInitialLoaded] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

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
    if (open) inputRef.current?.focus();
  }, [open]);

  // fetch options (immediate for initial load, debounced for typing)
  const loadOptions = useCallback(
    (q: string, immediate = false) => {
      clearTimeout(timerRef.current);
      const doFetch = async () => {
        setLoading(true);
        try {
          const result = await fetchOptions(q);
          setOptions(result);
        } catch {
          setOptions([]);
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
    [fetchOptions, debounceMs],
  );

  // load initial options once when first opened
  useEffect(() => {
    if (open && !initialLoaded) {
      loadOptions("", true);
      setInitialLoaded(true);
    }
  }, [open, initialLoaded, loadOptions]);

  // reset initial load flag when closed
  useEffect(() => {
    if (!open) setInitialLoaded(false);
  }, [open]);

  const handleSearchChange = (val: string) => {
    setSearch(val);
    loadOptions(val);
  };

  const handleSelect = (opt: string) => {
    onChange(opt);
    setSearch("");
    setOpen(false);
  };

  const handleClear = () => {
    onChange("");
    setSearch("");
    setOptions([]);
  };

  const handleTriggerClick = () => {
    if (open) {
      setOpen(false);
    } else {
      setSearch("");
      setOpen(true);
    }
  };

  return (
    <div className="searchable-select" ref={ref}>
      <div
        className="searchable-select-box"
        onClick={handleTriggerClick}
      >
        {open ? (
          <input
            ref={inputRef}
            type="text"
            className="searchable-select-input"
            placeholder={value || placeholder}
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className={value ? "" : "text-muted"}>
            {value || placeholder}
          </span>
        )}
        <span style={{ display: "flex", alignItems: "center", gap: "0.35rem", flexShrink: 0 }}>
          {value && !open && (
            <span
              className="searchable-select-clear"
              onClick={(e) => { e.stopPropagation(); handleClear(); }}
              title="Clear"
            >
              ×
            </span>
          )}
          <span className="dropdown-arrow">{open ? "▲" : "▼"}</span>
        </span>
      </div>

      {open && (
        <div className="dropdown-select-menu">
          <ul className="dropdown-select-list">
            {loading && (
              <li className="dropdown-select-empty">Loading…</li>
            )}
            {!loading && options.length === 0 && (
              <li className="dropdown-select-empty">
                {search ? "No matches found" : "No lab numbers available"}
              </li>
            )}
            {!loading &&
              options.map((opt) => (
                <li
                  key={opt}
                  className={`dropdown-select-item${opt === value ? " selected" : ""}`}
                  onClick={() => handleSelect(opt)}
                >
                  <span>{opt}</span>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}
