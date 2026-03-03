"""Report-related static constants.

This module centralises long strings used for report generation.
"""
from typing import Dict, List

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

DISCLAIMERS: List[str] = [
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
