"""
Generate 1,000 mock patients with singleton & trio variants, and HPO term
assignments.  Runs independently of the existing seed — safe to run multiple
times (lab numbers are unique, duplicates are skipped).

Usage:
    python -m backend.generate_mock_data
"""

import random
from datetime import date, timedelta

from backend.app import create_app
from backend.models import db, HPOTerm, Patient, Singleton, Trio

# ─── Name pools ──────────────────────────────────────────────────────────

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

TOTAL_PATIENTS = 1000
START_INDEX = 100  # start at LAB-0100 to avoid conflicts with existing LAB-001..020


def main():
    app = create_app()

    with app.app_context():
        # Check which lab numbers already exist
        existing = {p.lab_number for p in
                     Patient.query.with_entities(Patient.lab_number).all()}

        # Pool of HPO term IDs
        all_term_ids = [t.id for t in
                        HPOTerm.query.with_entities(HPOTerm.id).all()]
        all_terms_map = {}
        if all_term_ids:
            from backend.models import HPOTerm as HT
            all_terms_map = {t.id: t for t in
                             HT.query.filter(HT.id.in_(all_term_ids)).all()}

        created = 0
        singleton_count = 0
        trio_count = 0
        hpo_count = 0
        batch_size = 100

        for batch_start in range(START_INDEX, START_INDEX + TOTAL_PATIENTS, batch_size):
            patients_batch = []
            for idx in range(batch_start, min(batch_start + batch_size,
                                               START_INDEX + TOTAL_PATIENTS)):
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
            db.session.flush()  # get IDs assigned

            # Create 1-3 singleton variants per patient
            singletons_batch = []
            for patient in patients_batch:
                num_variants = random.randint(1, 3)
                for _ in range(num_variants):
                    vdata = generate_variant(patient.id)
                    singletons_batch.append(Singleton(**vdata))

            if singletons_batch:
                db.session.add_all(singletons_batch)
                singleton_count += len(singletons_batch)

            # Create 0-2 trio variants for ~40% of patients
            trios_batch = []
            for patient in patients_batch:
                if random.random() < 0.4:
                    num_trio = random.randint(1, 2)
                    for _ in range(num_trio):
                        vdata = generate_variant(patient.id)
                        trios_batch.append(Trio(**vdata))

            if trios_batch:
                db.session.add_all(trios_batch)
                trio_count += len(trios_batch)

            # Assign 1-5 random HPO terms per patient
            if all_term_ids:
                for patient in patients_batch:
                    k = min(random.randint(1, 5), len(all_term_ids))
                    chosen = random.sample(all_term_ids, k)
                    for tid in chosen:
                        if tid in all_terms_map:
                            patient.hpo_terms.append(all_terms_map[tid])
                    hpo_count += k

            db.session.commit()
            created += len(patients_batch)
            print(f"  ✓ Batch committed: {created}/{TOTAL_PATIENTS} patients")

        print(f"\nDone! Created {created} patients, "
              f"{singleton_count} singleton variants, "
              f"{trio_count} trio variants, "
              f"{hpo_count} HPO assignments.")


if __name__ == "__main__":
    main()
