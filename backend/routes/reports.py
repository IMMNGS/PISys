"""Report generation routes — preview data and Word document download.

Ported from the legacy ``patient_info`` Flask app.  Functions such as
``create_word_document``, ``generate_table``, ``generate_table_qc``,
``get_test_description`` and ``get_summary_result`` live here.
"""

import io
import os
import tempfile
from datetime import datetime

from flask import Blueprint, abort, jsonify, request, send_file

from backend.models import db, Patient, Singleton, Trio
from backend.routes.helpers import _patient_to_dict

reports_bp = Blueprint("reports", __name__)

# ── Static text constants ────────────────────────────────────────────────

GENE_LIST = (
    "ACD, ACP5, ACTB*, ADA, ADA2, ADAM17, ADAMTS13, ADAR, AICDA#, AIRE#, AK2, ALPI, ALPK1, ANGPT1, "
    "ANKZF1, AP1S3, AP3B1, AP3D1, APOL1, ARHGEF1, ARPC1B, ARPC5, ATM, ATP6AP1#, B2M, BACH2, BCL10, "
    "BCL11B#, BLK, BLM, BLNK, BLOC1S6, BTK#, C1QA, C1QB, C1QC, C1R, C1S, C2*#, C2orf69#, C3#, C5, "
    "C6, C7, C8A, C8B, C8G, C9, CARD10#, CARD11, CARD14#, CARD8, CARD9, CARMIL2, CASP10, CASP8, CBLB, "
    "CCBE1#, CCDC103, CCDC39, CCDC40#, CCDC65, CCNO, CD19, CD247, CD27, CD28, CD3D, CD3E, CD3G, CD4, "
    "CD40, CD40LG#, CD46*, CD55, CD59, CD70, CD79A, CD79B, CD81, CD8A, CDC42, CDCA7, CEBPE, CFAP298, "
    "CFAP300, CFB, CFD#, CFH*, CFI#, CFP#, CFTR, CHD7, CHUK, CIB1, CIITA, CLEC7A, CLPB#, COL7A1#, "
    "COPA, COPG1, CORO1A*#, CR2, CRACR2A, CSF2RA, CSF2RB, CSF3R, CTC1#, CTLA4, CTNNBL1, CTPS1, CTSC, "
    "CXCR2, CXCR4, CYBA, CYBB#, CYBC1, DBR1, DCLRE1B, DCLRE1C*, DDX58, DEF6, DGKE, DIAPH1, DKC1, "
    "DNAAF11, DNAAF2, DNAAF3#, DNAAF4, DNAAF5, DNAAF6, DNAH1#, DNAH11*#, DNAH5, DNAH9, DNAI1, DNAI2, "
    "DNAJB13, DNAJC21, DNAL1, DNASE1, DNASE1L3, DNASE2#, DNMT3B, DOCK11#, DOCK2, DOCK8, DPP9, DSG1, "
    "DTNBP1#, EFL1#, ELANE, EPG5, ERBIN, ERCC2, ERCC3, ERCC6L2, EXTL3, F12, FAAP24, FADD, FANCA, "
    "FANCB, FANCE, FANCF, FANCI#, FANCL, FAS, FASLG, FAT4, FCGR3A#, FCHO1, FCN3, FERMT1, FERMT3, "
    "FGL2, FNIP1, FOXN1#, FOXP3#, FPR1, G6PC3, G6PD#, GAS8#, GATA1#, GATA2, GFI1, GIMAP6, GINS1, "
    "GTF2H5, HAVCR2, HAX1#, HCK, HELLS#, HMOX1, HPS1*, HPS3, HPS4, HPS5, HPS6, HS3ST6, HTRA2, "
    "HYOU1#, ICOS, ICOSLG#, IFIH1#, IFNAR1, IFNAR2, IFNG, IFNGR1, IFNGR2, IGHM, IGLL1, IKBKB, "
    "IKZF1, IKZF2, IKZF3, IL10, IL10RA, IL10RB#, IL12B, IL12RB1, IL12RB2, IL17F, IL17RA, IL17RC, "
    "IL18BP, IL1RN, IL21, IL21R, IL23R, IL2RA, IL2RB, IL2RG#, IL36RN, IL37, IL6R#, IL6ST, IL7, IL7R, "
    "INO80, IPO8, IRAK1#, IRAK4, IRF2BP2, IRF3, IRF4, IRF7, IRF8#, IRF9, ISG15, ITCH, ITGB2#, ITK, "
    "ITPKB, IVNS1ABP, JAGN1, JAK1, JAK3, KDM6A#, KMT2A, KMT2D#, KNG1, KRAS, LACC1, LAMTOR2, LCK, "
    "LCP2, LIG1, LIG4, LPIN2, LRBA, LRRC56, LRRC8A, LY96, LYN, LYST#, MAD2L2, MAGT1#, MALT1#, "
    "MAN2B2#, MAP3K14, MAPK8, MASP2, MCIDAS, MCM10#, MCM4, MEFV, MOGS, MPEG1, MRE11, MRTFA, MS4A1, "
    "MSH6, MSN*#, MTHFD1, MVK, MYD88, MYOF, MYSM1, NBAS, NBN, NCF2, NCF4, NCKAP1L, NCSTN, NFAT5, "
    "NFE2L2, NFKB1, NFKB2, NFKBIA, NHEJ1, NHP2, NLRC4, NLRP1, NLRP12#, NLRP3, NOD2, NOP10, NOS2#, "
    "NRAS, NSMCE3, OAS1, ODAD1#, ODAD3#, OFD1#, ORAI1, OTULIN, PARN*, PAX1, PAX5, PDCD1, PEPD, PGM3, "
    "PIK3CD*, PIK3CG, PIK3R1, PLCG2, PLG#, PLVAP, PMM2, PMS2*#, PNP, POLA1#, POLD1, POLD2, POLD3, "
    "POLE, POLE2, POLR3A, POLR3C, POLR3F, POMP, POU2AF1, PRF1, PRKCD, PRKDC#, PSENEN, PSMA3, PSMB10, "
    "PSMB4, PSMB8, PSMB9, PSMG2, PSTPIP1, PTEN*, PTPN2, PTPRC, RAB27A, RAC2, RAG1, RAG2, RANBP2, "
    "RASGRP1, RBCK1#, RC3H1, REL, RELA, RELB, RFWD3, RFX5, RFXANK, RFXAP, RGS10, RHBDF2, RHOH, "
    "RIPK1, RMRP, RNASEH2A, RNASEH2B, RNASEH2C, RNF113A, RNF168, RNF31, RNU4ATAC, RORC, RPGR#, "
    "RPSA#, RSPH1, RSPH3, RSPH4A, RSPH9, RTEL1, SAMD9, SAMD9L, SAMHD1, SASH3#, SBDS, SEC61A1, "
    "SEMA3E, SERPING1, SGPL1, SH2D1A#, SH3BP2, SKIV2L, SLC29A3#, SLC35C1, SLC37A4#, SLC39A7#, "
    "SLC46A1, SLC7A7, SLC9A3, SLX4#, SMARCAL1#, SMARCD2, SNORA31, SOCS1, SP110, SPAG1, SPI1, SPINK5, "
    "SPPL2A, SRP19, SRP54, SRP72*, SRPRA, STAT1, STAT2, STAT3, STAT4, STAT5B*#, STAT6, STIM1, STING1, "
    "STK4, STN1, STX11, STXBP2#, STXBP3, SYK, TAFAZZIN#, TAOK2#, TAP1, TAP2, TAPBP, TBCE, TBK1, "
    "TBX1, TBX21, TCF3, TCN2, TERC, TERT, TET2, TFRC#, TGFB1, TGFBR1, TGFBR2, THBD, TICAM1, TINF2, "
    "TIRAP, TLR3, TLR7#, TLR8, TMC6, TMC8, TNFAIP3#, TNFRSF13B, TNFRSF13C, TNFRSF1A, TNFRSF4, "
    "TNFRSF9, TNFSF12, TNFSF13, TOM1, TOP2B, TPP1, TPP2, TRAC, TRAF3, TRAF3IP2, TREX1, TRIM22, "
    "TRIM69, TRNT1, TTC37, TTC7A, TYK2#, UBA1#, UNC119, UNC13D, UNC93B1*#, UNG, USB1, VPS13B, VPS45, "
    "WAS#, WDR1, WIPF1, WRAP53#, XIAP*#, ZAP70, ZBTB24, ZCCHC8, ZMYND10, ZNF341*, ZNFX1"
)

PANEL_DESCRIPTION = (
    "This panel targets protein coding exons, exon-intron boundaries (\u00b1 30 bps). "
    "This panel should be used to detect single nucleotide variants and small insertions "
    "and deletions (INDELs). This panel should not be used for the detection of repeat "
    "expansion disorders or diseases caused by mitochondrial DNA (mtDNA) mutations. The "
    "test does not recognize copy number variant, balanced translocations or complex "
    "inversions, and it may not detect low-level mosaicism."
)

GENE_FOOTNOTE = (
    "*Some, or all, of the gene is duplicated in the genome. "
    "#The gene has suboptimal coverage when >90% of the gene\u2019s target nucleotides "
    "are not covered at >20x with mapping quality score (MQ>20) reads. "
    "The sensitivity to detect variants may be limited in genes marked with an "
    "asterisk (*) or number sign (#)."
)

METHODS_SECTIONS = {
    "laboratory_process": (
        "When required, the total genomic DNA was extracted from the biological sample "
        "using silica-membrane-based method. DNA quality and quantity were assessed using "
        "spectrophotometric and fluorometric method. After assessment of DNA quality, "
        "qualified genomic DNA sample was randomly fragmented by fragmentation enzymes. "
        "Sequencing library was prepared by ligating sequencing adapters to both ends of "
        "DNA fragments. Sequencing libraries were size-selected with bead-based method to "
        "ensure optimal template size and amplified by polymerase chain reaction (PCR). "
        "Regions of interest (36.5 Mb of human protein coding regions with additional "
        "clinically relevant non-coding pathogenic and likely pathogenic variants) were "
        "targeted using hybridization-based target capture method. The quality of the "
        "completed sequencing library was controlled by ensuring the correct template size "
        "and quantity and to eliminate the presence of leftover primers and adapter-adapter "
        "dimers. Ready sequencing libraries that passed the quality control were sequenced "
        "using the Illumina\u2019s sequencing by synthesis (SBS) XLEAP method using "
        "paired-end sequencing (150 by 150 bases). Primary data analysis converting images "
        "into base calls and associated quality scores was carried out by the sequencing "
        "instrument using Illumina\u2019s proprietary software, generating CBCL files as "
        "the output."
    ),
    "bioinformatics": (
        "Illumina DRAGEN Bio-IT Platform onboard (NextSeq2000) pipeline (DRAGEN Enrichment "
        "v4.2.7) was used for secondary analysis of NGS data, includes data decompressing, "
        "mapping, aligning, sorting, duplicate marking & removing, and variant calling. In "
        "brief, base called raw sequencing data was transformed into FASTQ format and "
        "sequence reads of each sample were mapped to the human reference genome (GRCh38). "
        "Read alignment, duplicate read marking, local realignment around indels, base "
        "quality score recalibration and variant calling were performed using DRAGEN DNA "
        "algorithms. Variant data (VCF output files) was annotated using Golden Helix VarSeq "
        "software v2.6.0 with a variety of public variant databases including but not limited "
        "to gnomAD 4.1, ClinVar, OMIM, and CADD score v1.7, and Mastermind"
        "(https://www.genomenon.com/mastermind). The median sequencing depth and coverage "
        "across the target regions for the tested sample were calculated based on MQ0 aligned "
        "reads. The sequencing run included in-process reference sample(s) for quality control, "
        "which passed our thresholds for sensitivity and specificity. The patient\u2019s sample "
        "was subjected to thorough quality control measures including assessments for "
        "contamination and sample mix-up."
    ),
    "interpretation": (
        "Laboratory immunologists/scientific officers assessed the pathogenicity of the "
        "identified variants by evaluating the information in the patient requisition, "
        "reviewing the relevant scientific literature and manually inspecting the sequencing "
        "data if needed. All available evidence of the identified variants was compared to "
        "2015 ACMG classification criteria. Reporting was carried out using HGNC-approved "
        "gene nomenclature and mutation nomenclature following the HGVS guidelines. Likely "
        "benign and benign variants were not reported. Moreover, variants in genes that is "
        "not related to the patient\u2019s clinical phenotype at the time of analysis or with "
        "low post test probability VUS may not be reported. For pathogenic/ likely pathogenic "
        "variant(s) within the gene panel that are unrelated to the request indication will be "
        "included in the appendix section as incidental findings. Interpretation of the test "
        "results is limited by the information that is currently available. Better interpretation "
        "should be possible in the future as more data and knowledge about human genetics and "
        "this specific disorder are accumulated. It is possible that the variant classification, "
        "or gene-disease association may change with time. The laboratory would not reinterpret "
        "or reissue reports automatically. However, a request for reinterpretation may be "
        "considered in the form of new request."
    ),
    "variant_classification": (
        "Our variant classification follows the ACMG guideline 2015, and the ClinGen SVI "
        "recommendations. ACGS 2020 Best Practice Guideline was also referenced for variant "
        "classification and interpretation."
    ),
    "databases": (
        "The pathogenicity potential of the identified variants were assessed by considering "
        "the predicted consequence of the change, the degree of evolutionary conservation as "
        "well as the number of reference population databases and mutation databases such as, "
        "but not limited to, the gnomAD v4.1, ClinVar, HGMD Professional and Alamut Visual "
        "v1.13."
    ),
    "confirmation": (
        "Sequence variants classified as pathogenic, likely pathogenic and variants of uncertain "
        "significance (VUS) were confirmed using bi-directional Sanger sequencing when they did "
        "not meet our stringent NGS quality metrics for a true positive call."
    ),
    "validation": (
        "The sensitivity of this panel is expected to be in the same range as the validated "
        "whole exome sequencing laboratory assay used to generate the panel data (sensitivity "
        "for SNVs 99.97%, indels 1-50 bps 98.26%, and specificity >99.9% for both SNVs and "
        "indels). It does not detect very low level mosaicism."
    ),
    "limitations": (
        "Please note that the overall coverage of each genes varies and each individual may "
        "have slightly different coverage yield. This test does not detect the following: copy "
        "number variation, complex inversions, gene conversions, balanced translocations, repeat "
        "expansion disorders unless specifically mentioned, non-coding variants deeper than \u00b130 "
        "base pairs from exon-intron boundary unless otherwise indicated. Additionally, this test "
        "may not reliably detect the following: low level mosaicism, stretches of mononucleotide "
        "repeats, indels larger than 50bp, single exon deletions or duplications, and variants "
        "within pseudogene regions/duplicated segments. The study does not cover assessment in "
        "repeat expansions, mutations involved in tri-allelic inheritance, mitochondrial genome "
        "variants, epigenetic effects, oligogenic. The current platform is for germline variant "
        "assessment, and that somatic variants may not be detected. Laboratory error is also "
        "possible."
    ),
}

DISCLAIMERS = [
    "The above results refer only to the sample received.",
    (
        "The design of the virtual gene panel is based on the reference gene list published "
        "by the International Union of Immunological Societies (IUSI) expert committee: "
        "Journal of clinical immunology vol. 40,1 (2020): 24-64, J Hum Immun 5 May 2025; "
        "1(1):e20250002, and the Panel App Australia "
        "(https://panelapp.agha.umccr.org/)"
    ),
    (
        "Do NOT copy this report without permission of the laboratory. Further information "
        "is available on request. This report must be read in its entirety."
    ),
    (
        "There are possible sources of error for any DNA studies. Errors can result from "
        "trace contamination, sample mix up, erroneous paternity identification, rare "
        "technical errors, clerical errors and rare genetic variants that interfere with "
        "analysis etc."
    ),
    (
        "A negative result does not rule out the possibility that the tested individual "
        "carries a rare unexamined variant/gene(s) or variant in the undetectable region. "
        "The clinical sensitivity of the test may vary widely depending on the clinical "
        "and family history. Please also refers to assay limitations for details"
    ),
    (
        "This laboratory-developed test has been independently validated by the Clinical "
        "Immunology Division (see Analytic validation). It has not been cleared or approved "
        "by the US Food and Drug Administration."
    ),
]


# ── Helper functions ─────────────────────────────────────────────────────

def _format_date(value):
    """Return a date string formatted as dd/mm/yyyy, or '' if unavailable."""
    if not value:
        return ""
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%d/%m/%Y")
        d = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(value)


def get_test_description(test_type):
    """Return the test description blurb."""
    base = (
        "In-house Immunological Disorders SuperPanel gene panel from WES was tested "
        "by next generation sequencing, and 554 genes were included in the panel test."
    )
    if test_type and test_type.lower() == "trio":
        return f"{base} Trio analysis was performed."
    return base


def get_summary_result(patient):
    """Generate summary result text based on the finding type and variant data.

    Args:
        patient: Patient model instance.

    Returns:
        A summary string suitable for inclusion in the report.
    """
    finding_type = (patient.type_of_findings or "").upper()

    if "C" in finding_type:
        # Look for confirmed variants in singletons and trios
        c_singletons = Singleton.query.filter_by(
            patient_id=patient.id, reportable_variant="C"
        ).all()
        c_trios = Trio.query.filter_by(
            patient_id=patient.id, reportable_variant="C"
        ).all()
        variants = c_singletons + c_trios
        if variants:
            gene_names = []
            for v in variants:
                if v.gene_names:
                    gene_names.append(v.gene_names)
            if len(gene_names) == 1:
                return (
                    f"One likely pathogenic variant was detected in the "
                    f"{gene_names[0]} gene."
                )
            elif len(gene_names) > 1:
                return (
                    f"Likely pathogenic variants were detected in the "
                    f"{', '.join(gene_names)} genes."
                )
        return "No reportable variants found for this patient."

    if "A" in finding_type:
        return (
            "No disease-causing variant detected to fully account for the "
            "patient\u2019s phenotype. However, details on some additional "
            "findings have been included for reference."
        )

    if "I" in finding_type or "N" in finding_type:
        return (
            "No disease-causing variant detected to fully account for the "
            "patient\u2019s phenotype."
        )

    return "No confirmed variants found."


def _build_variant_table(doc, variants, include_inherited_from=False):
    """Insert a variant results table into a python-docx Document.

    Args:
        doc: python-docx Document instance.
        variants: list of Singleton or Trio model instances.
        include_inherited_from: if True, add an "Inherited From" column (trio).
    """
    from docx.shared import Pt

    headers = [
        "Gene", "HGVS c.", "HGVS p.", "Exon", "Zygosity",
        "Inheritance", "Classification", "OMIM ID", "RSID",
    ]
    if include_inherited_from:
        headers.insert(6, "Inherited From")

    ncols = len(headers)
    table = doc.add_table(rows=1 + len(variants), cols=ncols)
    table.style = "Table Grid"

    # Header row
    for i, hdr in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = hdr
        for run in cell.paragraphs[0].runs:
            run.bold = True

    # Data rows
    for row_idx, v in enumerate(variants, start=1):
        vals = [
            v.gene_names or "",
            v.hgvs_c or "",
            v.hgvs_p or "",
            v.exon_number or "",
            v.zygosity or "",
            v.inheritance or "",
            v.classification or "",
            v.omim_id or "",
            v.rsid or "",
        ]
        if include_inherited_from:
            vals.insert(6, v.inherited_from or "")
        for col_idx, val in enumerate(vals):
            table.cell(row_idx, col_idx).text = str(val)

    # Font size
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)


def _build_qc_table(doc):
    """Insert the Sequencing Performance Metrics QC table."""
    from docx.shared import Pt, Inches

    heading = doc.add_paragraph()
    heading.add_run("SEQUENCING PERFORMANCE METRICS").bold = True

    table = doc.add_table(rows=2, cols=7)
    table.style = "Table Grid"

    headers = [
        "PANELS", "GENES", "EXONS/\nREGIONS", "BASES",
        "% of target\nregion >20X", "Uniformity\n(%)", "MEDIAN\nCOVERAGE",
    ]
    for i, hdr in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = hdr
        for run in cell.paragraphs[0].runs:
            run.bold = True

    row1_data = [
        "Immunological\nDisorders\nSuperPanel", "554", "15,798",
        "2,359,627", "", "", "",
    ]
    for i, val in enumerate(row1_data):
        table.cell(1, i).text = val

    doc.add_paragraph()


# ── Word document generation ─────────────────────────────────────────────

def create_word_document(patient, test_type="singleton"):
    """Generate a full Word (.docx) report for a patient.

    Args:
        patient: Patient model instance (with relationships loaded).
        test_type: ``'singleton'`` or ``'trio'``.

    Returns:
        A BytesIO buffer containing the .docx file.
    """
    from docx import Document
    from docx.shared import Pt, Inches

    doc = Document()

    # Page setup
    section = doc.sections[0]
    section.page_width = Inches(11)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(12)

    # Report date
    p = doc.add_paragraph()
    p.add_run("REPORT DATE: ").bold = True
    p.add_run(_format_date(patient.report_date)).bold = True

    # Patient info
    age_display = f"{patient.age or ''} {patient.age_unit or ''}".strip()
    info_pairs = [
        ("Lab. #", f"{patient.im_lab_number or ''}/{patient.lab_number}"),
        ("Name", patient.name or ""),
        ("HKID", patient.hkid or ""),
        ("Date of Birth", _format_date(patient.dob)),
        ("Sex", patient.sex or ""),
        ("Age", age_display),
        ("Ethnicity", patient.ethnicity or ""),
        ("Specimen Collected", _format_date(patient.specimen_collected)),
        ("Specimen Arrived", _format_date(patient.specimen_arrived)),
    ]
    for label, value in info_pairs:
        p = doc.add_paragraph()
        p.add_run(f"{label}: ").bold = True
        p.add_run(str(value))

    # Separator
    p = doc.add_paragraph()
    p.add_run("-" * 117)

    # Summary sections
    summary_sections = [
        ("SPECIMEN", "EDTA blood"),
        ("CLINICAL HISTORY", patient.case_history or ""),
        ("TYPE OF TESTING REQUESTED", patient.type_of_test or ""),
        ("TEST DESCRIPTION", get_test_description(test_type)),
        ("SUMMARY OF RESULT(S)", get_summary_result(patient)),
    ]
    for label, value in summary_sections:
        p = doc.add_paragraph()
        p.add_run(f"{label}:").bold = True
        p = doc.add_paragraph()
        p.add_run(str(value))

    # Variant table — confirmed (C) findings
    finding_type = (patient.type_of_findings or "").upper()
    is_trio = test_type.lower() == "trio"

    if is_trio:
        c_variants = Trio.query.filter_by(
            patient_id=patient.id, reportable_variant="C"
        ).all()
    else:
        c_variants = Singleton.query.filter_by(
            patient_id=patient.id, reportable_variant="C"
        ).all()

    if c_variants:
        doc.add_page_break()
        p = doc.add_paragraph()
        p.add_run("RESULTS:").bold = True
        _build_variant_table(doc, c_variants, include_inherited_from=is_trio)

    # Additional findings (A)
    if "A" in finding_type:
        if is_trio:
            a_variants = Trio.query.filter_by(
                patient_id=patient.id, reportable_variant="A"
            ).all()
        else:
            a_variants = Singleton.query.filter_by(
                patient_id=patient.id, reportable_variant="A"
            ).all()
        if a_variants:
            doc.add_page_break()
            p = doc.add_paragraph()
            p.add_run("Additional Findings:").bold = True
            _build_variant_table(doc, a_variants, include_inherited_from=is_trio)

    # Interpretation text based on finding type
    if "A" in finding_type:
        p = doc.add_paragraph()
        p.add_run("INTERPRETATION / RECOMMENDED ACTION:").bold = True
        p = doc.add_paragraph()
        p.add_run(
            "Sequence analysis in current study with the Immunology gene panel did not "
            "detect any known disease-causing variants that could fully account the "
            "patient\u2019s phenotype as described to the laboratory at the time of "
            "interpretation. Please note that negative results do not rule out the "
            "diagnosis of a genetic disorder since some of the DNA abnormalities may be "
            "undetectable by the current applied technology. Further investigations may "
            "be considered if clinically indicated."
        )

    # Comments and Variant classification (editable sections)
    doc.add_page_break()
    for section_title in ["COMMENTS:", "VARIANT CLASSIFICATION:"]:
        p = doc.add_paragraph()
        p.add_run(section_title).bold = True
        for _ in range(6):
            doc.add_paragraph()

    # Appendix marker
    p = doc.add_paragraph()
    run = p.add_run("APPENDIX")
    run.underline = True
    run.bold = True

    # Incidental findings (I)
    if "I" in finding_type and "A" not in finding_type:
        p = doc.add_paragraph()
        p.add_run("INTERPRETATION / RECOMMENDED ACTION:").bold = True
        p = doc.add_paragraph()
        p.add_run(
            "Sequencing analysis in the current study did not detect any disease-causing "
            "variants that could fully account the patient\u2019s phenotypes as described "
            "to the laboratory at the time of interpretation."
        )
        p.add_run(
            "Please note that negative results do not rule out the diagnosis of a genetic "
            "disorder since some of the DNA abnormalities may be undetectable by the "
            "current applied technology. Moreover, variants assessment and interpretations "
            "may change with time when additional information from the patient\u2019s "
            "assessment or in the literature is available in the future. Test results "
            "should always be interpreted with clinical context, family history and other "
            "relevant data. Further investigations, such as whole exome / genome "
            "sequencing, assays targeting somatic mutation, CNV etc. may be considered if "
            "clinically indicated."
        )

    if "I" in finding_type:
        if is_trio:
            i_variants = Trio.query.filter_by(
                patient_id=patient.id, reportable_variant="I"
            ).all()
        else:
            i_variants = Singleton.query.filter_by(
                patient_id=patient.id, reportable_variant="I"
            ).all()
        if i_variants:
            p = doc.add_paragraph()
            p.add_run(
                "SUMMARY LIST OF OTHER INCIDENTAL FINDINGS WITHIN THE PANEL:"
            ).bold = True
            _build_variant_table(doc, i_variants, include_inherited_from=is_trio)

    # QC table
    _build_qc_table(doc)

    # Target region and gene list page
    doc.add_page_break()

    p = doc.add_paragraph()
    p.add_run("TARGET REGION AND GENE LIST").bold = True
    doc.add_paragraph()

    p = doc.add_paragraph()
    run = p.add_run(GENE_LIST)
    run.font.size = Pt(9)

    doc.add_paragraph()
    p = doc.add_paragraph()
    run = p.add_run(GENE_FOOTNOTE)
    run.font.size = Pt(9)

    p = doc.add_paragraph()
    run = p.add_run(PANEL_DESCRIPTION)
    run.font.size = Pt(9)

    # Methods
    p = doc.add_paragraph()
    p.add_run("METHODS:").bold = True
    doc.add_paragraph()

    method_items = [
        ("Laboratory process:", METHODS_SECTIONS["laboratory_process"]),
        ("Bioinformatics and quality control:", METHODS_SECTIONS["bioinformatics"]),
        ("Interpretation:", METHODS_SECTIONS["interpretation"]),
        ("Variant classification:", METHODS_SECTIONS["variant_classification"]),
        ("Databases:", METHODS_SECTIONS["databases"]),
        ("Confirmation of sequence alterations:", METHODS_SECTIONS["confirmation"]),
        ("Analytic validation:", METHODS_SECTIONS["validation"]),
        ("Assay limitations:", METHODS_SECTIONS["limitations"]),
    ]
    for subtitle, text in method_items:
        p = doc.add_paragraph()
        run = p.add_run(subtitle)
        run.underline = True
        p.add_run(" " + text)

    doc.add_paragraph(
        "Further test details could be found at Division\u2019s webpage: "
        "https://hkwc.home/webapps/Dept/CIMM/CellFnMolecularImmLab.aspx"
    )

    # Disclaimers
    p = doc.add_paragraph()
    p.add_run("DISCLAIMERS:").bold = True
    for i, disclaimer in enumerate(DISCLAIMERS, 1):
        doc.add_paragraph(f"({i}) {disclaimer}")

    # Signatures
    doc.add_paragraph()
    doc.add_paragraph("Reported By:")
    doc.add_paragraph()
    doc.add_paragraph("Dr. Edmund Tung")
    doc.add_paragraph()
    doc.add_paragraph("Signed Out By:")
    doc.add_paragraph()
    doc.add_paragraph("Consultant Immunologist")
    doc.add_paragraph("Dr. Au Yuen Ling Elaine")
    doc.add_paragraph()
    doc.add_paragraph("********** End of report **********")

    # Write to buffer
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ── API routes ───────────────────────────────────────────────────────────

@reports_bp.route("/report/preview", methods=["POST"])
def report_preview():
    """Return data needed to preview a report in the frontend.

    Body: ``{ "lab_number": "...", "test_type": "singleton"|"trio" }``

    Returns patient data, variant list, and default text blocks that can be
    edited in the UI before final generation.
    """
    data = request.get_json()
    lab_number = (data.get("lab_number") or "").strip()
    test_type = (data.get("test_type") or "singleton").lower()

    if not lab_number:
        return jsonify({"error": "lab_number is required"}), 400

    patient = Patient.query.filter_by(lab_number=lab_number).first()
    if not patient:
        return jsonify({"error": f"No patient with lab_number '{lab_number}'"}), 404

    # Fetch variants for this patient
    if test_type == "trio":
        variants_q = Trio.query.filter_by(patient_id=patient.id)
    else:
        variants_q = Singleton.query.filter_by(patient_id=patient.id)
    variants = variants_q.order_by("id").all()

    return jsonify({
        "patient": _patient_to_dict(
            patient, include_hpo=True,
            include_singletons=True, include_trios=True,
            include_vcf_files=True,
        ),
        "variants": [v.to_dict() for v in variants],
        "defaults": {
            "test_process": get_test_description(test_type),
            "disclaimer": "\n".join(f"({i}) {d}" for i, d in enumerate(DISCLAIMERS, 1)),
            "references": (
                "IUSI expert committee: Journal of clinical immunology vol. 40,1 "
                "(2020): 24-64, J Hum Immun 5 May 2025; 1(1):e20250002"
            ),
        },
    })


@reports_bp.route("/report/generate", methods=["POST"])
def generate_report():
    """Generate and download a Word (.docx) report for a patient.

    Body: ``{ "lab_number": "...", "test_type": "singleton"|"trio",
              "conclusion": "...", "test_process": "...",
              "disclaimer": "...", "references": "..." }``

    Returns: the .docx file as an attachment.
    """
    data = request.get_json()
    lab_number = (data.get("lab_number") or "").strip()
    test_type = (data.get("test_type") or "singleton").lower()

    if not lab_number:
        return jsonify({"error": "lab_number is required"}), 400

    patient = Patient.query.filter_by(lab_number=lab_number).first()
    if not patient:
        return jsonify({"error": f"No patient with lab_number '{lab_number}'"}), 404

    try:
        buf = create_word_document(patient, test_type=test_type)
    except ImportError:
        return jsonify({
            "error": "python-docx is not installed. Run: pip install python-docx"
        }), 500
    except Exception as e:
        return jsonify({"error": f"Report generation failed: {str(e)}"}), 500

    filename = f"report_{patient.lab_number}_{patient.im_lab_number or 'NA'}.docx"

    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=filename,
    )
