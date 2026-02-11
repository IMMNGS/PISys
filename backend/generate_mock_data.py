"""
Generate ALL mock / demo data for the Patient Information System.

This is the single source of mock data — seed.py does NOT contain any
patient data and is reserved for production reference data (HPO terms).

Modes
─────
  --predefined   Insert only the 20 hand-crafted demo patients (LAB-001 … LAB-020)
  --bulk         Insert only the 1,000 randomly generated patients (LAB-0100 … LAB-1099)
  --all          Insert both predefined + bulk  (default)

Usage:
    python -m backend.generate_mock_data                 # predefined + bulk
    python -m backend.generate_mock_data --predefined    # 20 demo patients only
    python -m backend.generate_mock_data --bulk          # 1,000 random patients only
"""

import argparse
import os
import random
from datetime import date, timedelta

from backend.app import create_app
from backend.models import db, HPOTerm, Patient, Singleton, Trio

from backend.app import create_app
from backend.models import db, HPOTerm, Patient, Singleton, Trio

# ══════════════════════════════════════════════════════════════════════════
#  Predefined demo patients (LAB-001 … LAB-020) — hand-crafted entries
# ══════════════════════════════════════════════════════════════════════════

PREDEFINED_PATIENTS = [
    {"lab_number": "LAB-001", "im_lab_number": "IM-001", "name": "Alice Johnson", "hkid": "A1234567", "sex": "Female", "age": 34, "age_unit": "Years", "ethnicity": "Chinese", "case_history": "Recurrent respiratory infections since childhood", "type_of_test": "WES", "type_of_findings": "Positive", "findings_summary": "Pathogenic variant identified in CFTR gene", "ngs_batch": "NGS-2025-01", "ngs_tat": "14 days", "ngs_tat_final": "21 days", "request_dr": "Dr. Wong", "remark": "Family screening recommended"},
    {"lab_number": "LAB-002", "im_lab_number": "IM-002", "name": "Bob Smith", "hkid": "B2345678", "sex": "Male", "age": 2, "age_unit": "Years", "ethnicity": "European", "case_history": "Bilateral sensorineural hearing loss", "type_of_test": "Targeted Panel", "type_of_findings": "Positive", "findings_summary": "Homozygous GJB2 variant confirmed", "ngs_batch": "NGS-2025-01", "ngs_tat": "10 days", "ngs_tat_final": "18 days", "request_dr": "Dr. Chan", "remark": None},
    {"lab_number": "LAB-003", "im_lab_number": "IM-003", "name": "Clara Williams", "hkid": "C3456789", "sex": "Female", "age": 1, "age_unit": "Years", "ethnicity": "Chinese", "case_history": "Short stature, rhizomelic shortening", "type_of_test": "WES", "type_of_findings": "Positive", "findings_summary": "De novo FGFR3 pathogenic variant", "ngs_batch": "NGS-2025-02", "ngs_tat": "12 days", "ngs_tat_final": "20 days", "request_dr": "Dr. Li", "remark": "Parents tested - de novo confirmed"},
    {"lab_number": "LAB-004", "im_lab_number": "IM-004", "name": "David Brown", "hkid": "D4567890", "sex": "Male", "age": 45, "age_unit": "Years", "ethnicity": "European", "case_history": "Family history of breast/ovarian cancer", "type_of_test": "BRCA Panel", "type_of_findings": "VUS", "findings_summary": "VUS identified in BRCA2", "ngs_batch": "NGS-2025-02", "ngs_tat": "14 days", "ngs_tat_final": "25 days", "request_dr": "Dr. Lee", "remark": "Genetic counseling recommended"},
    {"lab_number": "LAB-005", "im_lab_number": "IM-005", "name": "Eva Davis", "hkid": "E5678901", "sex": "Female", "age": 38, "age_unit": "Years", "ethnicity": "Chinese", "case_history": "Triple-negative breast cancer at age 35", "type_of_test": "BRCA Panel", "type_of_findings": "VUS", "findings_summary": "Intronic BRCA1 VUS with possible splice effect", "ngs_batch": "NGS-2025-03", "ngs_tat": "11 days", "ngs_tat_final": "19 days", "request_dr": "Dr. Ng", "remark": None},
    {"lab_number": "LAB-006", "im_lab_number": "IM-006", "name": "Frank Miller", "hkid": "F6789012", "sex": "Male", "age": 62, "age_unit": "Years", "ethnicity": "European", "case_history": "Metastatic melanoma", "type_of_test": "Somatic Panel", "type_of_findings": "Positive", "findings_summary": "BRAF V600E somatic mutation identified", "ngs_batch": "NGS-2025-03", "ngs_tat": "7 days", "ngs_tat_final": "14 days", "request_dr": "Dr. Ho", "remark": "Eligible for targeted therapy"},
    {"lab_number": "LAB-007", "im_lab_number": "IM-007", "name": "Grace Wilson", "hkid": "G7890123", "sex": "Female", "age": 5, "age_unit": "Months", "ethnicity": "Chinese", "case_history": "Characteristic facial features, pulmonary stenosis", "type_of_test": "WES", "type_of_findings": "Positive", "findings_summary": "PTPN11 pathogenic variant - Noonan syndrome", "ngs_batch": "NGS-2025-04", "ngs_tat": "15 days", "ngs_tat_final": "22 days", "request_dr": "Dr. Lam", "remark": "Cardiac follow-up arranged"},
    {"lab_number": "LAB-008", "im_lab_number": "IM-008", "name": "Henry Moore", "hkid": "H8901234", "sex": "Male", "age": 8, "age_unit": "Years", "ethnicity": "African", "case_history": "Sickle cell crisis presentation", "type_of_test": "Targeted", "type_of_findings": "Positive", "findings_summary": "HBB sickle cell variant confirmed", "ngs_batch": "NGS-2025-04", "ngs_tat": "5 days", "ngs_tat_final": "10 days", "request_dr": "Dr. Yip", "remark": None},
    {"lab_number": "LAB-009", "im_lab_number": "IM-009", "name": "Iris Taylor", "hkid": "I9012345", "sex": "Female", "age": 55, "age_unit": "Years", "ethnicity": "Chinese", "case_history": "Multiple primary cancers", "type_of_test": "Cancer Panel", "type_of_findings": "Positive", "findings_summary": "TP53 likely pathogenic variant - Li-Fraumeni", "ngs_batch": "NGS-2025-05", "ngs_tat": "13 days", "ngs_tat_final": "21 days", "request_dr": "Dr. Wong", "remark": "Cascade screening for family"},
    {"lab_number": "LAB-010", "im_lab_number": "IM-010", "name": "James Anderson", "hkid": "J0123456", "sex": "Male", "age": 42, "age_unit": "Years", "ethnicity": "European", "case_history": "Early-onset colorectal cancer", "type_of_test": "Lynch Panel", "type_of_findings": "VUS", "findings_summary": "MLH1 VUS identified", "ngs_batch": "NGS-2025-05", "ngs_tat": "14 days", "ngs_tat_final": "22 days", "request_dr": "Dr. Chan", "remark": "IHC and MSI testing recommended"},
    {"lab_number": "LAB-011", "im_lab_number": "IM-011", "name": "Karen Thomas", "hkid": "K1234560", "sex": "Female", "age": 6, "age_unit": "Years", "ethnicity": "Chinese", "case_history": "Progressive muscle weakness, elevated CK", "type_of_test": "WES", "type_of_findings": "Positive", "findings_summary": "DMD nonsense variant - carrier of Duchenne", "ngs_batch": "NGS-2025-06", "ngs_tat": "16 days", "ngs_tat_final": "24 days", "request_dr": "Dr. Li", "remark": "Brother affected, prenatal testing discussed"},
    {"lab_number": "LAB-012", "im_lab_number": "IM-012", "name": "Leo Jackson", "hkid": "L2345601", "sex": "Male", "age": 30, "age_unit": "Years", "ethnicity": "European", "case_history": "Elevated homocysteine levels", "type_of_test": "Targeted", "type_of_findings": "Negative", "findings_summary": "Common MTHFR polymorphism - benign", "ngs_batch": "NGS-2025-06", "ngs_tat": "5 days", "ngs_tat_final": "12 days", "request_dr": "Dr. Ng", "remark": None},
    {"lab_number": "LAB-013", "im_lab_number": "IM-013", "name": "Mia White", "hkid": "M3456012", "sex": "Female", "age": 35, "age_unit": "Years", "ethnicity": "Chinese", "case_history": "Endometrial cancer at young age", "type_of_test": "Lynch Panel", "type_of_findings": "Positive", "findings_summary": "MSH2 likely pathogenic variant - Lynch syndrome", "ngs_batch": "NGS-2025-07", "ngs_tat": "14 days", "ngs_tat_final": "20 days", "request_dr": "Dr. Ho", "remark": "Surveillance protocol initiated"},
    {"lab_number": "LAB-014", "im_lab_number": "IM-014", "name": "Nathan Harris", "hkid": "N4560123", "sex": "Male", "age": 18, "age_unit": "Years", "ethnicity": "European", "case_history": "Multiple colonic polyps", "type_of_test": "FAP Panel", "type_of_findings": "Positive", "findings_summary": "APC truncating variant - FAP confirmed", "ngs_batch": "NGS-2025-07", "ngs_tat": "10 days", "ngs_tat_final": "18 days", "request_dr": "Dr. Lam", "remark": "Surgical intervention planned"},
    {"lab_number": "LAB-015", "im_lab_number": "IM-015", "name": "Olivia Martin", "hkid": "O5601234", "sex": "Female", "age": 28, "age_unit": "Years", "ethnicity": "Chinese", "case_history": "Macrocephaly, thyroid nodules", "type_of_test": "WES", "type_of_findings": "Positive", "findings_summary": "PTEN pathogenic variant - Cowden syndrome", "ngs_batch": "NGS-2025-08", "ngs_tat": "15 days", "ngs_tat_final": "23 days", "request_dr": "Dr. Yip", "remark": "Multi-organ surveillance plan"},
    {"lab_number": "LAB-016", "im_lab_number": "IM-016", "name": "Paul Garcia", "hkid": "P6012345", "sex": "Male", "age": 50, "age_unit": "Years", "ethnicity": "South Asian", "case_history": "Family history of breast cancer", "type_of_test": "Cancer Panel", "type_of_findings": "VUS", "findings_summary": "CHEK2 VUS - uncertain significance", "ngs_batch": "NGS-2025-08", "ngs_tat": "14 days", "ngs_tat_final": "22 days", "request_dr": "Dr. Wong", "remark": None},
    {"lab_number": "LAB-017", "im_lab_number": "IM-017", "name": "Quinn Martinez", "hkid": "Q7123450", "sex": "Female", "age": 41, "age_unit": "Years", "ethnicity": "European", "case_history": "Premature coronary artery disease, high LDL", "type_of_test": "FH Panel", "type_of_findings": "Positive", "findings_summary": "LDLR pathogenic variant - familial hypercholesterolemia", "ngs_batch": "NGS-2025-09", "ngs_tat": "8 days", "ngs_tat_final": "15 days", "request_dr": "Dr. Chan", "remark": "Statin therapy initiated"},
    {"lab_number": "LAB-018", "im_lab_number": "IM-018", "name": "Ryan Robinson", "hkid": "R8234501", "sex": "Male", "age": 3, "age_unit": "Years", "ethnicity": "Chinese", "case_history": "Seizures, hypopigmented macules", "type_of_test": "WES", "type_of_findings": "Positive", "findings_summary": "TSC2 pathogenic variant - tuberous sclerosis", "ngs_batch": "NGS-2025-09", "ngs_tat": "15 days", "ngs_tat_final": "23 days", "request_dr": "Dr. Li", "remark": "MRI brain and renal USS arranged"},
    {"lab_number": "LAB-019", "im_lab_number": "IM-019", "name": "Sophia Clark", "hkid": "S9345012", "sex": "Female", "age": 22, "age_unit": "Years", "ethnicity": "European", "case_history": "Progressive external ophthalmoplegia", "type_of_test": "Mito Panel", "type_of_findings": "Positive", "findings_summary": "POLG likely pathogenic variant - mitochondrial disease", "ngs_batch": "NGS-2025-10", "ngs_tat": "16 days", "ngs_tat_final": "25 days", "request_dr": "Dr. Ng", "remark": "Muscle biopsy pending"},
    {"lab_number": "LAB-020", "im_lab_number": "IM-020", "name": "Thomas Lewis", "hkid": "T0456123", "sex": "Male", "age": 58, "age_unit": "Years", "ethnicity": "Chinese", "case_history": "Dilated cardiomyopathy", "type_of_test": "Cardio Panel", "type_of_findings": "VUS", "findings_summary": "TTN missense VUS - uncertain significance", "ngs_batch": "NGS-2025-10", "ngs_tat": "14 days", "ngs_tat_final": "22 days", "request_dr": "Dr. Ho", "remark": "Family segregation study planned"},
]

PREDEFINED_SINGLETONS = [
    {"_lab": "LAB-001", "reportable_variant": "c.1521_1523delCTT", "chr_pos": "7:117559590", "ref_alt": "ATCT/A", "igv_review": True, "second_review_comment": "Confirmed pathogenic", "gene_names": "CFTR", "hgvs_c": "c.1521_1523delCTT", "hgvs_p": "p.Phe508del", "exon_number": "11", "zygosity": "Heterozygous", "inheritance": "Autosomal Recessive", "inherited_from": "Mother", "classification": "Pathogenic", "omim_id": "219700", "rsid": "rs113993960", "title": "Cystic Fibrosis", "omimid": "602421", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-002", "reportable_variant": "c.35delG", "chr_pos": "13:20763686", "ref_alt": "CG/C", "igv_review": True, "second_review_comment": "Homozygous confirmed", "gene_names": "GJB2", "hgvs_c": "c.35delG", "hgvs_p": "p.Gly12Valfs*2", "exon_number": "2", "zygosity": "Homozygous", "inheritance": "Autosomal Recessive", "inherited_from": "Both", "classification": "Pathogenic", "omim_id": "220290", "rsid": "rs80338939", "title": "Deafness, Autosomal Recessive 1A", "omimid": "121011", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-003", "reportable_variant": "c.1138G>A", "chr_pos": "4:1801559", "ref_alt": "G/A", "igv_review": True, "second_review_comment": "Review pending", "gene_names": "FGFR3", "hgvs_c": "c.1138G>A", "hgvs_p": "p.Gly380Arg", "exon_number": "10", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "De novo", "classification": "Pathogenic", "omim_id": "100800", "rsid": "rs28931614", "title": "Achondroplasia", "omimid": "134934", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-004", "reportable_variant": "c.5882G>A", "chr_pos": "13:32914438", "ref_alt": "G/A", "igv_review": False, "second_review_comment": None, "gene_names": "BRCA2", "hgvs_c": "c.5882G>A", "hgvs_p": "p.Cys1961Tyr", "exon_number": "11", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "Father", "classification": "VUS", "omim_id": "612555", "rsid": "rs28897727", "title": "Breast-Ovarian Cancer, Familial 2", "omimid": "600185", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-005", "reportable_variant": "c.3140-26A>G", "chr_pos": "17:41245090", "ref_alt": "A/G", "igv_review": True, "second_review_comment": "Splice-site effect suspected", "gene_names": "BRCA1", "hgvs_c": "c.3140-26A>G", "hgvs_p": None, "exon_number": "Intron 10", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "Mother", "classification": "VUS", "omim_id": "604370", "rsid": "rs80358065", "title": "Breast-Ovarian Cancer, Familial 1", "omimid": "113705", "gene_region_combined": "Intronic"},
    {"_lab": "LAB-006", "reportable_variant": "c.1799T>A", "chr_pos": "7:140453136", "ref_alt": "T/A", "igv_review": True, "second_review_comment": "Known oncogenic variant", "gene_names": "BRAF", "hgvs_c": "c.1799T>A", "hgvs_p": "p.Val600Glu", "exon_number": "15", "zygosity": "Heterozygous", "inheritance": "Somatic", "inherited_from": None, "classification": "Pathogenic", "omim_id": "164757", "rsid": "rs113488022", "title": "Melanoma", "omimid": "164757", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-007", "reportable_variant": "c.922A>G", "chr_pos": "12:112888163", "ref_alt": "G/A", "igv_review": True, "second_review_comment": "Confirmed pathogenic", "gene_names": "PTPN11", "hgvs_c": "c.922A>G", "hgvs_p": "p.Asn308Asp", "exon_number": "8", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "De novo", "classification": "Pathogenic", "omim_id": "163950", "rsid": "rs28933386", "title": "Noonan Syndrome 1", "omimid": "176876", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-008", "reportable_variant": "c.20A>T", "chr_pos": "11:5248232", "ref_alt": "A/G", "igv_review": False, "second_review_comment": "Requires further analysis", "gene_names": "HBB", "hgvs_c": "c.20A>T", "hgvs_p": "p.Glu7Val", "exon_number": "1", "zygosity": "Heterozygous", "inheritance": "Autosomal Recessive", "inherited_from": "Father", "classification": "Pathogenic", "omim_id": "603903", "rsid": "rs334", "title": "Sickle Cell Disease", "omimid": "141900", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-009", "reportable_variant": "c.1624G>T", "chr_pos": "17:7578406", "ref_alt": "C/A", "igv_review": True, "second_review_comment": "Somatic mutation confirmed", "gene_names": "TP53", "hgvs_c": "c.1624G>T", "hgvs_p": "p.Val215Leu", "exon_number": "6", "zygosity": "Heterozygous", "inheritance": "Somatic", "inherited_from": None, "classification": "Likely Pathogenic", "omim_id": "151623", "rsid": "rs28934575", "title": "Li-Fraumeni Syndrome", "omimid": "191170", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-010", "reportable_variant": "c.1517T>C", "chr_pos": "3:37089131", "ref_alt": "T/C", "igv_review": True, "second_review_comment": None, "gene_names": "MLH1", "hgvs_c": "c.1517T>C", "hgvs_p": "p.Ile506Thr", "exon_number": "13", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "Mother", "classification": "VUS", "omim_id": "120435", "rsid": "rs63750449", "title": "Lynch Syndrome", "omimid": "120436", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-011", "reportable_variant": "c.3846G>A", "chr_pos": "X:31137345", "ref_alt": "G/A", "igv_review": True, "second_review_comment": "Confirmed pathogenic nonsense", "gene_names": "DMD", "hgvs_c": "c.3846G>A", "hgvs_p": "p.Trp1282*", "exon_number": "27", "zygosity": "Hemizygous", "inheritance": "X-Linked Recessive", "inherited_from": "Mother", "classification": "Pathogenic", "omim_id": "310200", "rsid": None, "title": "Duchenne Muscular Dystrophy", "omimid": "300377", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-012", "reportable_variant": "c.665C>T", "chr_pos": "1:11856378", "ref_alt": "C/T", "igv_review": False, "second_review_comment": None, "gene_names": "MTHFR", "hgvs_c": "c.665C>T", "hgvs_p": "p.Ala222Val", "exon_number": "5", "zygosity": "Homozygous", "inheritance": "Autosomal Recessive", "inherited_from": "Both", "classification": "Benign", "omim_id": "607093", "rsid": "rs1801133", "title": "Homocysteinemia", "omimid": "607093", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-013", "reportable_variant": "c.4082G>A", "chr_pos": "2:48033880", "ref_alt": "C/T", "igv_review": True, "second_review_comment": "Segregation data supports pathogenicity", "gene_names": "MSH2", "hgvs_c": "c.4082G>A", "hgvs_p": "p.Arg1361His", "exon_number": "13", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "Father", "classification": "Likely Pathogenic", "omim_id": "120435", "rsid": "rs63749867", "title": "Lynch Syndrome", "omimid": "609309", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-014", "reportable_variant": "c.1483C>T", "chr_pos": "5:112175770", "ref_alt": "C/T", "igv_review": True, "second_review_comment": None, "gene_names": "APC", "hgvs_c": "c.1483C>T", "hgvs_p": "p.Arg495*", "exon_number": "11", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "De novo", "classification": "Pathogenic", "omim_id": "175100", "rsid": "rs137854568", "title": "Familial Adenomatous Polyposis", "omimid": "611731", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-015", "reportable_variant": "c.592C>T", "chr_pos": "10:89720805", "ref_alt": "G/A", "igv_review": True, "second_review_comment": "Confirmed loss-of-function", "gene_names": "PTEN", "hgvs_c": "c.592C>T", "hgvs_p": "p.Arg198*", "exon_number": "7", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "Mother", "classification": "Pathogenic", "omim_id": "158350", "rsid": "rs121909229", "title": "Cowden Syndrome", "omimid": "601728", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-016", "reportable_variant": "c.2176G>C", "chr_pos": "22:29091840", "ref_alt": "G/C", "igv_review": False, "second_review_comment": "Uncertain significance, recurrent", "gene_names": "CHEK2", "hgvs_c": "c.2176G>C", "hgvs_p": "p.Ala726Pro", "exon_number": "14", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "Father", "classification": "VUS", "omim_id": "604373", "rsid": None, "title": "Hereditary Cancer Predisposition", "omimid": "604373", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-017", "reportable_variant": "c.509G>A", "chr_pos": "19:11200093", "ref_alt": "C/T", "igv_review": True, "second_review_comment": "Common pharmacogenomic variant", "gene_names": "LDLR", "hgvs_c": "c.509G>A", "hgvs_p": "p.Arg170His", "exon_number": "4", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "Father", "classification": "Pathogenic", "omim_id": "143890", "rsid": "rs28942078", "title": "Familial Hypercholesterolemia", "omimid": "606945", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-018", "reportable_variant": "c.1444C>T", "chr_pos": "16:2103394", "ref_alt": "C/T", "igv_review": True, "second_review_comment": None, "gene_names": "TSC2", "hgvs_c": "c.1444C>T", "hgvs_p": "p.Arg482*", "exon_number": "14", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "De novo", "classification": "Pathogenic", "omim_id": "191100", "rsid": None, "title": "Tuberous Sclerosis Complex 2", "omimid": "191092", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-019", "reportable_variant": "c.818G>A", "chr_pos": "15:89878502", "ref_alt": "C/T", "igv_review": False, "second_review_comment": None, "gene_names": "POLG", "hgvs_c": "c.818G>A", "hgvs_p": "p.Arg273Gln", "exon_number": "3", "zygosity": "Compound Heterozygous", "inheritance": "Autosomal Recessive", "inherited_from": "Mother", "classification": "Likely Pathogenic", "omim_id": "174763", "rsid": "rs113994097", "title": "Mitochondrial DNA Depletion Syndrome", "omimid": "174763", "gene_region_combined": "Exonic"},
    {"_lab": "LAB-020", "reportable_variant": "c.4150G>A", "chr_pos": "2:179443560", "ref_alt": "G/A", "igv_review": True, "second_review_comment": "Confirmed gain-of-function", "gene_names": "TTN", "hgvs_c": "c.4150G>A", "hgvs_p": "p.Asp1384Asn", "exon_number": "18", "zygosity": "Heterozygous", "inheritance": "Autosomal Dominant", "inherited_from": "Father", "classification": "VUS", "omim_id": "604145", "rsid": None, "title": "Dilated Cardiomyopathy", "omimid": "188840", "gene_region_combined": "Exonic"},
]

# ── Name pools ──────────────────────────────────────────────────────────

FIRST_NAMES_M = [
    "Aaron", "Adam", "Adrian", "Alan", "Albert", "Alex", "Alfred", "Andrew",
    "Anthony", "Arthur", "Austin", "Barry", "Ben", "Bernard", "Billy", "Bobby",
    "Brad", "Brandon", "Brian", "Bruce", "Bryan", "Calvin", "Cameron", "Carl",
    "Carlos", "Charles", "Chester", "Chris", "Clarence", "Claude", "Clayton",
    "Colin", "Craig", "Curtis", "Dale", "Daniel", "Darren", "David", "Dean",
    "Dennis", "Derek", "Donald", "Douglas", "Duncan", "Dustin", "Dylan", "Earl",
    "Eddie", "Edward", "Edwin", "Eli", "Elliott", "Eric", "Ernest", "Eugene",
    "Evan", "Felix", "Fernando", "Floyd", "Francis", "Frank", "Frederick",
    "Gabriel", "Gary", "George", "Gerald", "Gilbert", "Glen", "Gordon", "Grant",
    "Gregory", "Harold", "Harry", "Harvey", "Hector", "Henry", "Herbert",
    "Herman", "Howard", "Hugo", "Ian", "Isaac", "Ivan", "Jack", "Jacob",
    "James", "Jason", "Jeffrey", "Jerome", "Jesse", "Jimmy", "Joel", "John",
    "Jonathan", "Jordan", "Joseph", "Joshua", "Julian", "Justin", "Keith",
    "Kenneth", "Kevin", "Kyle", "Lance", "Larry", "Lawrence", "Leonard", "Leo",
    "Leslie", "Lewis", "Liam", "Lincoln", "Lloyd", "Logan", "Louis", "Lucas",
    "Luke", "Malcolm", "Marcus", "Mark", "Martin", "Mason", "Matthew", "Max",
    "Michael", "Miles", "Mitchell", "Nathan", "Neil", "Nicholas", "Noah",
    "Norman", "Oliver", "Oscar", "Owen", "Patrick", "Paul", "Peter", "Philip",
    "Ralph", "Randy", "Raymond", "Reginald", "Richard", "Robert", "Roger",
    "Roland", "Ronald", "Roy", "Russell", "Ryan", "Samuel", "Scott", "Sean",
    "Sebastian", "Shane", "Simon", "Stanley", "Stephen", "Steven", "Stuart",
    "Theodore", "Thomas", "Timothy", "Todd", "Tony", "Travis", "Trevor",
    "Tyler", "Vernon", "Victor", "Vincent", "Walter", "Warren", "Wayne",
    "Wesley", "William", "Zachary",
]

FIRST_NAMES_F = [
    "Abigail", "Adelaide", "Agnes", "Aileen", "Alice", "Alison", "Amanda",
    "Amber", "Amy", "Andrea", "Angela", "Anita", "Anna", "Annie", "April",
    "Ashley", "Audrey", "Barbara", "Beatrice", "Becky", "Belinda", "Beth",
    "Betty", "Beverly", "Bianca", "Bonnie", "Brenda", "Bridget", "Brooke",
    "Camilla", "Candice", "Carla", "Carmen", "Carol", "Caroline", "Catherine",
    "Charlotte", "Chelsea", "Cheryl", "Christina", "Christine", "Clara",
    "Claudia", "Colleen", "Constance", "Cynthia", "Daisy", "Dana", "Danielle",
    "Daphne", "Dawn", "Deborah", "Denise", "Diana", "Diane", "Dolores",
    "Donna", "Doris", "Dorothy", "Edith", "Eileen", "Elaine", "Eleanor",
    "Elena", "Elizabeth", "Ella", "Ellen", "Emily", "Emma", "Erica", "Esther",
    "Eva", "Evelyn", "Faith", "Felicia", "Fiona", "Florence", "Frances",
    "Georgia", "Gertrude", "Gina", "Gladys", "Gloria", "Grace", "Hannah",
    "Harriet", "Hazel", "Heather", "Helen", "Holly", "Irene", "Iris", "Isabel",
    "Ivy", "Jacqueline", "Jane", "Janet", "Janice", "Jean", "Jennifer",
    "Jessica", "Jill", "Joan", "Joanne", "Josephine", "Joy", "Judith", "Julia",
    "Julie", "June", "Karen", "Katherine", "Kathleen", "Katrina", "Kay",
    "Kelly", "Kim", "Kimberly", "Laura", "Lauren", "Leah", "Leslie", "Lillian",
    "Linda", "Lisa", "Lorraine", "Louise", "Lucy", "Lydia", "Lynn", "Mabel",
    "Madeleine", "Margaret", "Maria", "Marilyn", "Martha", "Mary", "Megan",
    "Melissa", "Mia", "Michelle", "Miriam", "Monica", "Nancy", "Naomi",
    "Natalie", "Nicole", "Nora", "Norma", "Olivia", "Pamela", "Patricia",
    "Paula", "Pauline", "Peggy", "Penelope", "Phyllis", "Rachel", "Rebecca",
    "Regina", "Rita", "Robin", "Rosa", "Rose", "Rosemary", "Ruby", "Ruth",
    "Sally", "Samantha", "Sandra", "Sarah", "Sharon", "Sheila", "Shirley",
    "Sophia", "Stacy", "Stephanie", "Susan", "Sylvia", "Tammy", "Teresa",
    "Thelma", "Theresa", "Tiffany", "Tracy", "Valerie", "Vanessa", "Vera",
    "Veronica", "Victoria", "Viola", "Virginia", "Vivian", "Wendy", "Yvonne",
]

LAST_NAMES = [
    "Adams", "Allen", "Anderson", "Andrews", "Armstrong", "Arnold", "Bailey",
    "Baker", "Barnes", "Barrett", "Bell", "Bennett", "Black", "Blake", "Bond",
    "Bradley", "Brooks", "Brown", "Bryant", "Burns", "Burton", "Butler",
    "Campbell", "Carr", "Carter", "Chan", "Chang", "Chapman", "Chen", "Cheung",
    "Choi", "Chow", "Chung", "Clark", "Cole", "Collins", "Cook", "Cooper",
    "Cox", "Crawford", "Cross", "Cunningham", "Curtis", "Daniels", "Davidson",
    "Davies", "Davis", "Dawson", "Dean", "Dixon", "Douglas", "Drake", "Duncan",
    "Edwards", "Ellis", "Evans", "Ferguson", "Fisher", "Fleming", "Fletcher",
    "Ford", "Foster", "Fox", "Francis", "Freeman", "Fung", "Garcia", "Gibson",
    "Gordon", "Graham", "Grant", "Gray", "Green", "Griffin", "Hall", "Hamilton",
    "Hansen", "Harper", "Harris", "Harrison", "Hart", "Harvey", "Hawkins",
    "Hayes", "Henderson", "Hill", "Ho", "Holmes", "Howard", "Hughes", "Hunt",
    "Hunter", "Ip", "Jackson", "James", "Jenkins", "Johnson", "Johnston",
    "Jones", "Jordan", "Kelly", "Kennedy", "King", "Knight", "Kong", "Kwok",
    "Lam", "Lane", "Lau", "Law", "Lawrence", "Lee", "Leung", "Lewis", "Li",
    "Lin", "Liu", "Lloyd", "Lo", "Long", "Lui", "Ma", "MacDonald", "Mak",
    "Marshall", "Martin", "Mason", "Matthews", "McCarthy", "McDonald", "Miller",
    "Mills", "Mitchell", "Moore", "Morgan", "Morris", "Murphy", "Murray",
    "Nelson", "Ng", "Nichols", "O'Brien", "Oliver", "Owen", "Palmer",
    "Parker", "Patel", "Patterson", "Pearson", "Perry", "Peterson", "Phillips",
    "Porter", "Powell", "Price", "Quinn", "Reed", "Reid", "Reynolds",
    "Richards", "Richardson", "Riley", "Roberts", "Robertson", "Robinson",
    "Rogers", "Rose", "Ross", "Russell", "Ryan", "Sanders", "Scott", "Shaw",
    "Simpson", "Singh", "Smith", "Spencer", "Stevens", "Stewart", "Stone",
    "Sullivan", "Tam", "Tang", "Taylor", "Thomas", "Thompson", "Tong",
    "Torres", "Tucker", "Turner", "Walker", "Wallace", "Walsh", "Wang",
    "Ward", "Watson", "Webb", "Wells", "West", "White", "Williams", "Wilson",
    "Wong", "Wood", "Wright", "Wu", "Yam", "Yang", "Yeung", "Yip", "Young",
    "Yu", "Zhang",
]

ETHNICITIES = [
    "Chinese", "Chinese", "Chinese", "Chinese", "Chinese",   # weighted
    "European", "European",
    "South Asian", "Southeast Asian", "African", "Japanese",
    "Korean", "Filipino", "Mixed",
]

DOCTORS = [
    "Dr. Wong", "Dr. Chan", "Dr. Li", "Dr. Ng", "Dr. Ho", "Dr. Lam",
    "Dr. Yip", "Dr. Lee", "Dr. Cheung", "Dr. Leung", "Dr. Kwok", "Dr. Tang",
    "Dr. Chow", "Dr. Fung", "Dr. Tam", "Dr. Patel", "Dr. Chen", "Dr. Liu",
    "Dr. Smith", "Dr. Johnson",
]

TEST_TYPES = [
    "WES", "WES", "WES",  # weighted
    "Targeted Panel", "Targeted Panel",
    "BRCA Panel", "Somatic Panel", "Cancer Panel", "Lynch Panel",
    "FAP Panel", "FH Panel", "Mito Panel", "Cardio Panel",
    "Epilepsy Panel", "WGS", "Carrier Screening",
]

FINDINGS_TYPES = ["Positive", "Positive", "VUS", "VUS", "Negative", "Inconclusive"]

NGS_BATCHES = [f"NGS-2025-{i:02d}" for i in range(1, 25)] + \
              [f"NGS-2026-{i:02d}" for i in range(1, 13)]

CASE_HISTORIES = [
    "Recurrent respiratory infections since childhood",
    "Bilateral sensorineural hearing loss",
    "Short stature, rhizomelic shortening",
    "Family history of breast/ovarian cancer",
    "Triple-negative breast cancer at age 35",
    "Metastatic melanoma",
    "Characteristic facial features, pulmonary stenosis",
    "Sickle cell crisis presentation",
    "Multiple primary cancers",
    "Early-onset colorectal cancer",
    "Progressive muscle weakness, elevated CK",
    "Elevated homocysteine levels",
    "Endometrial cancer at young age",
    "Multiple colonic polyps",
    "Macrocephaly, thyroid nodules",
    "Family history of breast cancer",
    "Premature coronary artery disease, high LDL",
    "Seizures, hypopigmented macules",
    "Progressive external ophthalmoplegia",
    "Dilated cardiomyopathy",
    "Developmental delay, seizures",
    "Retinitis pigmentosa, progressive vision loss",
    "Neonatal hypotonia, feeding difficulties",
    "Marfanoid habitus, lens subluxation",
    "Chronic liver disease of unknown cause",
    "Recurrent miscarriages",
    "Congenital heart defect, coarctation of aorta",
    "Neonatal jaundice, conjugated hyperbilirubinemia",
    "Intellectual disability, dysmorphic features",
    "Unexplained cardiomyopathy at young age",
    "Progressive ataxia, onset in childhood",
    "Bilateral renal cysts detected on prenatal scan",
    "Pancytopenia, short stature",
    "Severe combined immunodeficiency",
    "Recurrent fractures with minimal trauma",
    "Congenital adrenal hyperplasia",
    "Persistent hyperinsulinemic hypoglycemia",
    "Early-onset parkinsonism",
    "Hereditary spherocytosis",
    "Neonatal diabetes mellitus",
]

# ─── Variant data pools ─────────────────────────────────────────────────

GENE_VARIANTS = [
    {"gene": "BRCA1", "hgvs_c": "c.68_69delAG", "hgvs_p": "p.Glu23Valfs*17", "exon": "2", "chr_pos": "17:43124027", "ref_alt": "TAG/T", "inheritance": "Autosomal Dominant", "omim_id": "604370", "title": "Breast-Ovarian Cancer, Familial 1", "omimid": "113705"},
    {"gene": "BRCA2", "hgvs_c": "c.5946delT", "hgvs_p": "p.Ser1982Argfs*22", "exon": "11", "chr_pos": "13:32914437", "ref_alt": "AT/A", "inheritance": "Autosomal Dominant", "omim_id": "612555", "title": "Breast-Ovarian Cancer, Familial 2", "omimid": "600185"},
    {"gene": "CFTR", "hgvs_c": "c.1521_1523delCTT", "hgvs_p": "p.Phe508del", "exon": "11", "chr_pos": "7:117559590", "ref_alt": "ATCT/A", "inheritance": "Autosomal Recessive", "omim_id": "219700", "title": "Cystic Fibrosis", "omimid": "602421"},
    {"gene": "CFTR", "hgvs_c": "c.1652G>A", "hgvs_p": "p.Gly551Asp", "exon": "12", "chr_pos": "7:117587811", "ref_alt": "G/A", "inheritance": "Autosomal Recessive", "omim_id": "219700", "title": "Cystic Fibrosis", "omimid": "602421"},
    {"gene": "GJB2", "hgvs_c": "c.35delG", "hgvs_p": "p.Gly12Valfs*2", "exon": "2", "chr_pos": "13:20763686", "ref_alt": "CG/C", "inheritance": "Autosomal Recessive", "omim_id": "220290", "title": "Deafness, Autosomal Recessive 1A", "omimid": "121011"},
    {"gene": "GJB2", "hgvs_c": "c.109G>A", "hgvs_p": "p.Val37Ile", "exon": "2", "chr_pos": "13:20763760", "ref_alt": "G/A", "inheritance": "Autosomal Recessive", "omim_id": "220290", "title": "Deafness, Autosomal Recessive 1A", "omimid": "121011"},
    {"gene": "FGFR3", "hgvs_c": "c.1138G>A", "hgvs_p": "p.Gly380Arg", "exon": "10", "chr_pos": "4:1801559", "ref_alt": "G/A", "inheritance": "Autosomal Dominant", "omim_id": "100800", "title": "Achondroplasia", "omimid": "134934"},
    {"gene": "TP53", "hgvs_c": "c.817C>T", "hgvs_p": "p.Arg273Cys", "exon": "8", "chr_pos": "17:7577120", "ref_alt": "G/A", "inheritance": "Autosomal Dominant", "omim_id": "151623", "title": "Li-Fraumeni Syndrome", "omimid": "191170"},
    {"gene": "TP53", "hgvs_c": "c.742C>T", "hgvs_p": "p.Arg248Trp", "exon": "7", "chr_pos": "17:7577538", "ref_alt": "G/A", "inheritance": "Autosomal Dominant", "omim_id": "151623", "title": "Li-Fraumeni Syndrome", "omimid": "191170"},
    {"gene": "MLH1", "hgvs_c": "c.350C>T", "hgvs_p": "p.Thr117Met", "exon": "4", "chr_pos": "3:37053568", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "120435", "title": "Lynch Syndrome", "omimid": "120436"},
    {"gene": "MSH2", "hgvs_c": "c.942+3A>T", "hgvs_p": None, "exon": "Intron 5", "chr_pos": "2:47656948", "ref_alt": "A/T", "inheritance": "Autosomal Dominant", "omim_id": "120435", "title": "Lynch Syndrome", "omimid": "609309"},
    {"gene": "APC", "hgvs_c": "c.3927_3931delAAAGA", "hgvs_p": "p.Glu1309Aspfs*4", "exon": "15", "chr_pos": "5:112175211", "ref_alt": "GAAAGA/G", "inheritance": "Autosomal Dominant", "omim_id": "175100", "title": "Familial Adenomatous Polyposis", "omimid": "611731"},
    {"gene": "PTPN11", "hgvs_c": "c.922A>G", "hgvs_p": "p.Asn308Asp", "exon": "8", "chr_pos": "12:112888163", "ref_alt": "A/G", "inheritance": "Autosomal Dominant", "omim_id": "163950", "title": "Noonan Syndrome 1", "omimid": "176876"},
    {"gene": "HBB", "hgvs_c": "c.20A>T", "hgvs_p": "p.Glu7Val", "exon": "1", "chr_pos": "11:5248232", "ref_alt": "A/T", "inheritance": "Autosomal Recessive", "omim_id": "603903", "title": "Sickle Cell Disease", "omimid": "141900"},
    {"gene": "HBB", "hgvs_c": "c.118C>T", "hgvs_p": "p.Gln40*", "exon": "2", "chr_pos": "11:5248155", "ref_alt": "C/T", "inheritance": "Autosomal Recessive", "omim_id": "613985", "title": "Beta-Thalassemia", "omimid": "141900"},
    {"gene": "DMD", "hgvs_c": "c.4174C>T", "hgvs_p": "p.Gln1392*", "exon": "30", "chr_pos": "X:31496362", "ref_alt": "C/T", "inheritance": "X-Linked Recessive", "omim_id": "310200", "title": "Duchenne Muscular Dystrophy", "omimid": "300377"},
    {"gene": "PTEN", "hgvs_c": "c.388C>T", "hgvs_p": "p.Arg130*", "exon": "5", "chr_pos": "10:89692905", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "158350", "title": "Cowden Syndrome", "omimid": "601728"},
    {"gene": "LDLR", "hgvs_c": "c.681C>G", "hgvs_p": "p.Asp227Glu", "exon": "4", "chr_pos": "19:11216561", "ref_alt": "C/G", "inheritance": "Autosomal Dominant", "omim_id": "143890", "title": "Familial Hypercholesterolemia", "omimid": "606945"},
    {"gene": "TSC1", "hgvs_c": "c.1525C>T", "hgvs_p": "p.Arg509*", "exon": "15", "chr_pos": "9:135786854", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "191100", "title": "Tuberous Sclerosis Complex 1", "omimid": "605284"},
    {"gene": "TSC2", "hgvs_c": "c.1444C>T", "hgvs_p": "p.Arg482*", "exon": "14", "chr_pos": "16:2103394", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "191100", "title": "Tuberous Sclerosis Complex 2", "omimid": "191092"},
    {"gene": "POLG", "hgvs_c": "c.1399G>A", "hgvs_p": "p.Ala467Thr", "exon": "7", "chr_pos": "15:89862739", "ref_alt": "G/A", "inheritance": "Autosomal Recessive", "omim_id": "174763", "title": "Mitochondrial DNA Depletion Syndrome", "omimid": "174763"},
    {"gene": "TTN", "hgvs_c": "c.70642C>T", "hgvs_p": "p.Arg23548*", "exon": "326", "chr_pos": "2:179410141", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "604145", "title": "Dilated Cardiomyopathy", "omimid": "188840"},
    {"gene": "BRAF", "hgvs_c": "c.1799T>A", "hgvs_p": "p.Val600Glu", "exon": "15", "chr_pos": "7:140453136", "ref_alt": "T/A", "inheritance": "Somatic", "omim_id": "164757", "title": "Melanoma", "omimid": "164757"},
    {"gene": "CHEK2", "hgvs_c": "c.1100delC", "hgvs_p": "p.Thr367Metfs*15", "exon": "10", "chr_pos": "22:29091857", "ref_alt": "AC/A", "inheritance": "Autosomal Dominant", "omim_id": "604373", "title": "Hereditary Cancer Predisposition", "omimid": "604373"},
    {"gene": "RB1", "hgvs_c": "c.958C>T", "hgvs_p": "p.Arg320*", "exon": "10", "chr_pos": "13:48941648", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "180200", "title": "Retinoblastoma", "omimid": "614041"},
    {"gene": "FBN1", "hgvs_c": "c.4955T>C", "hgvs_p": "p.Ile1652Thr", "exon": "40", "chr_pos": "15:48760588", "ref_alt": "T/C", "inheritance": "Autosomal Dominant", "omim_id": "154700", "title": "Marfan Syndrome", "omimid": "134797"},
    {"gene": "SCN1A", "hgvs_c": "c.5536T>C", "hgvs_p": "p.Phe1846Leu", "exon": "26", "chr_pos": "2:166231020", "ref_alt": "T/C", "inheritance": "Autosomal Dominant", "omim_id": "607208", "title": "Dravet Syndrome", "omimid": "182389"},
    {"gene": "PKD1", "hgvs_c": "c.11017C>T", "hgvs_p": "p.Gln3673*", "exon": "38", "chr_pos": "16:2157586", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "173900", "title": "Polycystic Kidney Disease 1", "omimid": "601313"},
    {"gene": "HEXA", "hgvs_c": "c.1278insTATC", "hgvs_p": "p.Tyr427Ilefs*5", "exon": "11", "chr_pos": "15:72638892", "ref_alt": "T/TTATC", "inheritance": "Autosomal Recessive", "omim_id": "272800", "title": "Tay-Sachs Disease", "omimid": "606869"},
    {"gene": "PAH", "hgvs_c": "c.1222C>T", "hgvs_p": "p.Arg408Trp", "exon": "12", "chr_pos": "12:103234266", "ref_alt": "C/T", "inheritance": "Autosomal Recessive", "omim_id": "261600", "title": "Phenylketonuria", "omimid": "612349"},
    {"gene": "GALN", "hgvs_c": "c.901G>T", "hgvs_p": "p.Asp301Tyr", "exon": "7", "chr_pos": "16:88907553", "ref_alt": "G/T", "inheritance": "Autosomal Recessive", "omim_id": "253000", "title": "Morquio Syndrome A", "omimid": "612222"},
    {"gene": "MECP2", "hgvs_c": "c.916C>T", "hgvs_p": "p.Arg306Cys", "exon": "4", "chr_pos": "X:153296777", "ref_alt": "C/T", "inheritance": "X-Linked Dominant", "omim_id": "312750", "title": "Rett Syndrome", "omimid": "300005"},
    {"gene": "NF1", "hgvs_c": "c.2041C>T", "hgvs_p": "p.Arg681*", "exon": "18", "chr_pos": "17:31224016", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "162200", "title": "Neurofibromatosis Type 1", "omimid": "613113"},
    {"gene": "COL1A1", "hgvs_c": "c.769G>A", "hgvs_p": "p.Gly257Arg", "exon": "12", "chr_pos": "17:48268287", "ref_alt": "G/A", "inheritance": "Autosomal Dominant", "omim_id": "166200", "title": "Osteogenesis Imperfecta", "omimid": "120150"},
    {"gene": "SMAD4", "hgvs_c": "c.1081C>T", "hgvs_p": "p.Arg361Cys", "exon": "9", "chr_pos": "18:51065510", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "175050", "title": "Juvenile Polyposis Syndrome", "omimid": "600993"},
    {"gene": "RET", "hgvs_c": "c.2753T>C", "hgvs_p": "p.Met918Thr", "exon": "16", "chr_pos": "10:43617416", "ref_alt": "T/C", "inheritance": "Autosomal Dominant", "omim_id": "171400", "title": "Multiple Endocrine Neoplasia 2B", "omimid": "164761"},
    {"gene": "KCNQ1", "hgvs_c": "c.817C>T", "hgvs_p": "p.Arg273Cys", "exon": "6", "chr_pos": "11:2575785", "ref_alt": "C/T", "inheritance": "Autosomal Dominant", "omim_id": "192500", "title": "Long QT Syndrome 1", "omimid": "607542"},
    {"gene": "MYH7", "hgvs_c": "c.1208G>A", "hgvs_p": "p.Arg403Gln", "exon": "13", "chr_pos": "14:23894966", "ref_alt": "G/A", "inheritance": "Autosomal Dominant", "omim_id": "115195", "title": "Hypertrophic Cardiomyopathy", "omimid": "160760"},
    {"gene": "GBA", "hgvs_c": "c.1226A>G", "hgvs_p": "p.Asn409Ser", "exon": "9", "chr_pos": "1:155237048", "ref_alt": "A/G", "inheritance": "Autosomal Recessive", "omim_id": "230800", "title": "Gaucher Disease", "omimid": "606463"},
    {"gene": "SERPINA1", "hgvs_c": "c.1096G>A", "hgvs_p": "p.Glu366Lys", "exon": "5", "chr_pos": "14:94847262", "ref_alt": "G/A", "inheritance": "Autosomal Recessive", "omim_id": "613490", "title": "Alpha-1 Antitrypsin Deficiency", "omimid": "107400"},
]

RSIDS = [
    "rs113993960", "rs80338939", "rs28931614", "rs121909229", "rs28942078",
    "rs113488022", "rs28933386", "rs334", "rs28934575", "rs63750449",
    "rs63749867", "rs137854568", "rs113994097", "rs80358065", "rs1801133",
    "rs1799966", "rs80357914", "rs786201005", "rs121434569", "rs121908134",
    None, None, None, None,  # some variants without rsIDs
]

CLASSIFICATIONS = [
    "Pathogenic", "Pathogenic", "Pathogenic",  # weighted
    "Likely Pathogenic", "Likely Pathogenic",
    "VUS", "VUS", "VUS",
    "Likely Benign",
    "Benign",
]

ZYGOSITIES = [
    "Heterozygous", "Heterozygous", "Heterozygous",  # weighted
    "Homozygous",
    "Compound Heterozygous",
    "Hemizygous",
]

INHERITED_FROM_OPTIONS = [
    "Mother", "Father", "De novo", "De novo", "Both", None,
]


# ─── Helpers ─────────────────────────────────────────────────────────────

def random_date(start_year=2024, end_year=2026):
    start = date(start_year, 1, 1)
    end = date(end_year, 1, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_dob(age, age_unit):
    today = date.today()
    if age_unit == "Months":
        return today - timedelta(days=age * 30)
    if age_unit == "Days":
        return today - timedelta(days=age)
    return today - timedelta(days=age * 365 + random.randint(0, 180))


def random_hkid():
    letter = random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
    digits = "".join(str(random.randint(0, 9)) for _ in range(7))
    check = random.choice("0123456789A")
    return f"{letter}{digits}({check})"


def generate_patient(idx: int) -> dict:
    sex = random.choice(["Male", "Female"])
    first = random.choice(FIRST_NAMES_M if sex == "Male" else FIRST_NAMES_F)
    last = random.choice(LAST_NAMES)

    age_unit = random.choices(["Years", "Months", "Days"], weights=[85, 10, 5])[0]
    if age_unit == "Years":
        age = random.randint(0, 90)
    elif age_unit == "Months":
        age = random.randint(1, 36)
    else:
        age = random.randint(1, 365)

    report_dt = random_date()
    specimen_collected = report_dt - timedelta(days=random.randint(15, 45))
    specimen_arrived = specimen_collected + timedelta(days=random.randint(1, 5))
    tat_days = random.randint(5, 21)

    findings_type = random.choice(FINDINGS_TYPES)
    test_type = random.choice(TEST_TYPES)

    return {
        "lab_number": f"LAB-{idx:04d}",
        "im_lab_number": f"IM-{idx:04d}",
        "name": f"{first} {last}",
        "hkid": random_hkid(),
        "sex": sex,
        "age": age,
        "age_unit": age_unit,
        "dob": random_dob(age, age_unit),
        "ethnicity": random.choice(ETHNICITIES),
        "report_date": report_dt,
        "specimen_collected": specimen_collected,
        "specimen_arrived": specimen_arrived,
        "case_history": random.choice(CASE_HISTORIES),
        "type_of_test": test_type,
        "type_of_findings": findings_type,
        "findings_summary": f"{findings_type} finding in {test_type} analysis",
        "ngs_batch": random.choice(NGS_BATCHES),
        "ngs_tat": f"{tat_days} days",
        "ngs_tat_final": f"{tat_days + random.randint(3, 10)} days",
        "request_dr": random.choice(DOCTORS),
        "remark": random.choice([None, None, "Follow-up recommended",
                                  "Family screening advised",
                                  "Genetic counseling recommended",
                                  "Reanalysis in 12 months"]),
    }


def generate_variant(patient_id: int) -> dict:
    v = random.choice(GENE_VARIANTS)
    classification = random.choice(CLASSIFICATIONS)
    zygosity = random.choice(ZYGOSITIES)
    if v["inheritance"] == "X-Linked Recessive":
        zygosity = "Hemizygous"
    elif v["inheritance"] == "Autosomal Recessive":
        zygosity = random.choice(["Homozygous", "Compound Heterozygous", "Heterozygous"])

    return {
        "patient_id": patient_id,
        "reportable_variant": v["hgvs_c"],
        "chr_pos": v["chr_pos"],
        "ref_alt": v["ref_alt"],
        "igv_review": random.choice([True, True, False]),
        "second_review_comment": random.choice([
            None, None, "Confirmed pathogenic", "Requires further analysis",
            "Segregation data supports pathogenicity",
            "Variant of uncertain significance",
        ]),
        "gene_names": v["gene"],
        "hgvs_c": v["hgvs_c"],
        "hgvs_p": v.get("hgvs_p"),
        "exon_number": v["exon"],
        "zygosity": zygosity,
        "inheritance": v["inheritance"],
        "inherited_from": random.choice(INHERITED_FROM_OPTIONS),
        "classification": classification,
        "omim_id": v["omim_id"],
        "rsid": random.choice(RSIDS),
        "title": v["title"],
        "omimid": v["omimid"],
        "gene_region_combined": random.choice(["Exonic", "Exonic", "Intronic", "Splice site"]),
    }


# ─── Main ────────────────────────────────────────────────────────────────

BULK_TOTAL = 1000
BULK_START = 100  # LAB-0100 … LAB-1099  (avoids LAB-001 … LAB-020)
BATCH_SIZE = 100


def seed_predefined_patients():
    """Insert the 20 hand-crafted demo patients with their singleton findings."""
    existing = {p.lab_number for p in Patient.query.with_entities(Patient.lab_number).all()}

    all_term_ids = [t.id for t in HPOTerm.query.with_entities(HPOTerm.id).limit(200).all()]

    lab_to_patient = {}
    patients_to_add = []
    for p in PREDEFINED_PATIENTS:
        if p["lab_number"] in existing:
            continue
        report_dt = random_date()
        specimen_collected = report_dt - timedelta(days=random.randint(20, 40))
        specimen_arrived = specimen_collected + timedelta(days=random.randint(1, 3))
        patient = Patient(
            report_date=report_dt,
            lab_number=p["lab_number"],
            im_lab_number=p.get("im_lab_number"),
            name=p.get("name"),
            hkid=p.get("hkid"),
            dob=random_dob(p.get("age", 30), p.get("age_unit", "Years")),
            sex=p.get("sex"),
            age=p.get("age"),
            age_unit=p.get("age_unit"),
            ethnicity=p.get("ethnicity"),
            specimen_collected=specimen_collected,
            specimen_arrived=specimen_arrived,
            case_history=p.get("case_history"),
            type_of_test=p.get("type_of_test"),
            type_of_findings=p.get("type_of_findings"),
            findings_summary=p.get("findings_summary"),
            ngs_batch=p.get("ngs_batch"),
            ngs_tat=p.get("ngs_tat"),
            ngs_tat_final=p.get("ngs_tat_final"),
            request_dr=p.get("request_dr"),
            remark=p.get("remark"),
        )
        patients_to_add.append(patient)
        lab_to_patient[p["lab_number"]] = patient

    if not patients_to_add:
        print("  • Predefined patients already loaded — skipping.")
        return

    db.session.add_all(patients_to_add)
    db.session.commit()

    # Create singleton findings
    singletons_to_add = []
    for s in PREDEFINED_SINGLETONS:
        patient = lab_to_patient.get(s["_lab"])
        if not patient:
            continue
        singletons_to_add.append(Singleton(
            patient_id=patient.id,
            reportable_variant=s.get("reportable_variant"),
            chr_pos=s.get("chr_pos"),
            ref_alt=s.get("ref_alt"),
            igv_review=s.get("igv_review", False),
            second_review_comment=s.get("second_review_comment"),
            gene_names=s.get("gene_names"),
            hgvs_c=s.get("hgvs_c"),
            hgvs_p=s.get("hgvs_p"),
            exon_number=s.get("exon_number"),
            zygosity=s.get("zygosity"),
            inheritance=s.get("inheritance"),
            inherited_from=s.get("inherited_from"),
            classification=s.get("classification"),
            omim_id=s.get("omim_id"),
            rsid=s.get("rsid"),
            title=s.get("title"),
            omimid=s.get("omimid"),
            gene_region_combined=s.get("gene_region_combined"),
        ))

    if singletons_to_add:
        db.session.add_all(singletons_to_add)
        db.session.commit()

    # Assign 1-4 random HPO terms per patient
    if all_term_ids:
        all_terms_map = {t.id: t for t in HPOTerm.query.filter(HPOTerm.id.in_(all_term_ids)).all()}
        for patient in patients_to_add:
            chosen_ids = random.sample(all_term_ids, k=min(random.randint(1, 4), len(all_term_ids)))
            for tid in chosen_ids:
                if tid in all_terms_map:
                    patient.hpo_terms.append(all_terms_map[tid])
        db.session.commit()

    print(f"  ✓ Inserted {len(patients_to_add)} predefined patients "
          f"with {len(singletons_to_add)} singleton findings.")


def generate_bulk_patients():
    """Insert 1,000 randomly generated patients (LAB-0100 … LAB-1099)."""
    existing = {p.lab_number for p in Patient.query.with_entities(Patient.lab_number).all()}

    all_term_ids = [t.id for t in HPOTerm.query.with_entities(HPOTerm.id).all()]
    all_terms_map = {}
    if all_term_ids:
        all_terms_map = {t.id: t for t in HPOTerm.query.filter(HPOTerm.id.in_(all_term_ids)).all()}

    created = 0
    singleton_count = 0
    trio_count = 0
    hpo_count = 0

    for batch_start in range(BULK_START, BULK_START + BULK_TOTAL, BATCH_SIZE):
        patients_batch = []
        for idx in range(batch_start, min(batch_start + BATCH_SIZE, BULK_START + BULK_TOTAL)):
            pdata = generate_patient(idx)
            if pdata["lab_number"] in existing:
                continue
            patient = Patient(
                report_date=pdata["report_date"],
                lab_number=pdata["lab_number"],
                im_lab_number=pdata["im_lab_number"],
                name=pdata["name"],
                hkid=pdata["hkid"],
                dob=pdata["dob"],
                sex=pdata["sex"],
                age=pdata["age"],
                age_unit=pdata["age_unit"],
                ethnicity=pdata["ethnicity"],
                specimen_collected=pdata["specimen_collected"],
                specimen_arrived=pdata["specimen_arrived"],
                case_history=pdata["case_history"],
                type_of_test=pdata["type_of_test"],
                type_of_findings=pdata["type_of_findings"],
                findings_summary=pdata["findings_summary"],
                ngs_batch=pdata["ngs_batch"],
                ngs_tat=pdata["ngs_tat"],
                ngs_tat_final=pdata["ngs_tat_final"],
                request_dr=pdata["request_dr"],
                remark=pdata["remark"],
            )
            patients_batch.append(patient)
            existing.add(pdata["lab_number"])

        if not patients_batch:
            continue

        db.session.add_all(patients_batch)
        db.session.flush()

        # 1-3 singleton variants per patient
        singletons_batch = []
        for patient in patients_batch:
            for _ in range(random.randint(1, 3)):
                singletons_batch.append(Singleton(**generate_variant(patient.id)))
        if singletons_batch:
            db.session.add_all(singletons_batch)
            singleton_count += len(singletons_batch)

        # 0-2 trio variants for ~40 % of patients
        trios_batch = []
        for patient in patients_batch:
            if random.random() < 0.4:
                for _ in range(random.randint(1, 2)):
                    trios_batch.append(Trio(**generate_variant(patient.id)))
        if trios_batch:
            db.session.add_all(trios_batch)
            trio_count += len(trios_batch)

        # 1-5 HPO terms per patient
        if all_term_ids:
            for patient in patients_batch:
                k = min(random.randint(1, 5), len(all_term_ids))
                for tid in random.sample(all_term_ids, k):
                    if tid in all_terms_map:
                        patient.hpo_terms.append(all_terms_map[tid])
                hpo_count += k

        db.session.commit()
        created += len(patients_batch)
        print(f"  ✓ Batch committed: {created}/{BULK_TOTAL} patients")

    print(f"\n  Done! Created {created} patients, "
          f"{singleton_count} singleton variants, "
          f"{trio_count} trio variants, "
          f"{hpo_count} HPO assignments.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate mock patient data for the Patient Information System.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--predefined", action="store_true",
                       help="Insert only the 20 hand-crafted demo patients (LAB-001 … LAB-020)")
    group.add_argument("--bulk", action="store_true",
                       help="Insert only the 1,000 randomly generated patients (LAB-0100 … LAB-1099)")
    group.add_argument("--all", action="store_true", default=True,
                       help="Insert both predefined + bulk patients (default)")
    args = parser.parse_args()

    env = os.environ.get("FLASK_ENV", "development")
    app = create_app(env)

    with app.app_context():
        if args.predefined:
            print("Generating predefined demo patients …")
            seed_predefined_patients()
        elif args.bulk:
            print("Generating bulk random patients …")
            generate_bulk_patients()
        else:
            print("Generating all mock patients …")
            seed_predefined_patients()
            generate_bulk_patients()
        print("Done.")


if __name__ == "__main__":
    main()
