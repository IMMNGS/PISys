import { useState, useRef, useEffect } from "react";

export interface DropdownItem {
  id: number;
  label: string;
}

interface DropdownSelectProps {
  items: DropdownItem[];
  placeholder: string;
  selectedIds: Set<number>;
  onToggle: (id: number) => void;
  pageSize?: number;
}

export default function DropdownSelect({
  items,
  placeholder,
  selectedIds,
  onToggle,
  pageSize = 20,
}: DropdownSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [visible, setVisible] = useState(pageSize);
  const ref = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

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

  // focus search when opened
  useEffect(() => {
    if (open) searchRef.current?.focus();
  }, [open]);

  // reset visible count when items or search change
  useEffect(() => {
    setVisible(pageSize);
  }, [items.length, pageSize, search]);

  const filtered = search
    ? items.filter((item) =>
        item.label.toLowerCase().includes(search.toLowerCase()),
      )
    : items;
  const shownItems = filtered.slice(0, visible);
  const remaining = filtered.length - visible;

  return (
    <div className="dropdown-select" ref={ref}>
      <button
        type="button"
        className="dropdown-select-trigger"
        onClick={() => setOpen((o) => !o)}
      >
        <span>
          {selectedIds.size > 0 ? `${selectedIds.size} selected` : placeholder}
        </span>
        <span className="dropdown-arrow">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="dropdown-select-menu">
          <input
            ref={searchRef}
            type="text"
            className="dropdown-select-search"
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onClick={(e) => e.stopPropagation()}
          />
          <ul className="dropdown-select-list">
            {shownItems.length === 0 && (
              <li className="dropdown-select-empty">
                {search ? "No matches found" : "No items available"}
              </li>
            )}
            {shownItems.map((item) => (
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
          </ul>
          {remaining > 0 && (
            <button
              type="button"
              className="dropdown-select-load-more"
              onClick={(e) => {
                e.stopPropagation();
                setVisible((v) => v + pageSize);
              }}
            >
              Load more ({remaining} remaining)
            </button>
          )}
        </div>
      )}
    </div>
  );
}
