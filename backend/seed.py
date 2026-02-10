"""
Seed the database with HPO terms from all_hpo_terms.csv, mock patients,
and mock singleton findings.

Usage:
    python -m backend.seed
"""

import csv
import os
import random
from datetime import date, timedelta

from backend.app import create_app
from backend.models import db, HPOTerm, Patient, Singleton

# ── Mock patient data ────────────────────────────────────────────────────

MOCK_PATIENTS = [
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

# ── Mock singleton (variant) data — linked to patients by index ──────────

MOCK_SINGLETONS = [
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


def random_date(start_year=2024, end_year=2025):
    """Generate a random date in the given range."""
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def random_dob(age, age_unit):
    """Generate a plausible DOB from age/age_unit."""
    today = date.today()
    if age_unit == "Months":
        return today - timedelta(days=age * 30)
    return today - timedelta(days=age * 365)


def seed_hpo_terms(csv_path: str):
    """Load HPO terms from CSV into the database (skip existing)."""
    existing = {t.hpo_id for t in HPOTerm.query.with_entities(HPOTerm.hpo_id).all()}

    terms_to_add = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hpo_id = row["hpo_id"].strip()
            if hpo_id in existing:
                continue
            terms_to_add.append(HPOTerm(
                hpo_id=hpo_id,
                term_name=row["term_name"].strip(),
                definition=row.get("definition", "").strip() or None,
                synonyms=row.get("synonyms", "").strip() or None,
            ))

    if terms_to_add:
        db.session.bulk_save_objects(terms_to_add)
        db.session.commit()
        print(f"  ✓ Inserted {len(terms_to_add)} HPO terms.")
    else:
        print("  • HPO terms already loaded — skipping.")


def seed_patients():
    """Create mock patients and their singleton findings."""
    existing = {p.lab_number for p in Patient.query.with_entities(Patient.lab_number).all()}

    # Grab a pool of HPO term IDs to assign
    all_term_ids = [t.id for t in HPOTerm.query.with_entities(HPOTerm.id).limit(200).all()]

    # Build a lookup of lab_number → patient for singleton linking
    lab_to_patient = {}

    patients_to_add = []
    for p in MOCK_PATIENTS:
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

    if patients_to_add:
        db.session.add_all(patients_to_add)
        db.session.commit()

        # Create singleton findings for each patient
        singletons_to_add = []
        for s in MOCK_SINGLETONS:
            patient = lab_to_patient.get(s["_lab"])
            if not patient:
                continue
            singleton = Singleton(
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
            )
            singletons_to_add.append(singleton)

        if singletons_to_add:
            db.session.add_all(singletons_to_add)
            db.session.commit()

        # Assign 1-4 random HPO terms per patient (via relationship)
        if all_term_ids:
            all_terms_map = {t.id: t for t in HPOTerm.query.filter(HPOTerm.id.in_(all_term_ids)).all()}
            for patient in patients_to_add:
                chosen_ids = random.sample(all_term_ids, k=min(random.randint(1, 4), len(all_term_ids)))
                for tid in chosen_ids:
                    if tid in all_terms_map:
                        patient.hpo_terms.append(all_terms_map[tid])
            db.session.commit()

        print(f"  ✓ Inserted {len(patients_to_add)} mock patients with {len(singletons_to_add)} singleton findings.")
    else:
        print("  • Mock patients already loaded — skipping.")


def main():
    app = create_app()
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "all_hpo_terms.csv")

    with app.app_context():
        print("Seeding database …")
        seed_hpo_terms(csv_path)
        seed_patients()
        print("Done.")


if __name__ == "__main__":
    main()
