"""
Fetch the latest HPO terms from the pyhpo library and write them to CSV.

Can be run standalone:
    python -m backend.hpo_terms

Or called programmatically via refresh_hpo_terms_to_csv().
"""

import os

from pyhpo import Ontology
import pandas as pd


def refresh_hpo_terms_to_csv(output_dir: str | None = None) -> str:
    """Pull every HPO term from pyhpo and save to all_hpo_terms.csv.

    Args:
        output_dir: Directory to write the CSV into.
                    Defaults to ``<project_root>/data``.

    Returns:
        The full path of the written CSV file.
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    os.makedirs(output_dir, exist_ok=True)

    _ = Ontology()

    all_terms = []
    for term in Ontology:
        all_terms.append({
            "hpo_id": term.id,
            "term_name": term.name,
            "definition": term.definition,
            "synonyms": ", ".join(term.synonym) if term.synonym else "",
        })

    df = pd.DataFrame(all_terms)
    csv_path = os.path.join(output_dir, "all_hpo_terms.csv")
    df.to_csv(csv_path, index=False)
    print(f"Retrieved {len(df)} terms → {csv_path}")
    return csv_path


if __name__ == "__main__":
    refresh_hpo_terms_to_csv()



