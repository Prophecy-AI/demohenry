import pandas as pd
import json
import ast
import numpy as np
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import defaultdict, Counter
import warnings
import math
from functools import lru_cache
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
warnings.filterwarnings('ignore')

class PlanExecutor:
    def __init__(self, csv_path: str = "data/providers.csv", claims_csv_path: str = "data/Mounjaro Claim Sample.csv"):
        """Initialize executor with comprehensive HCP and Claims data processing and semantic search capabilities"""
        self.hcp_df = pd.read_csv(csv_path)
        self.claims_df = pd.read_csv(claims_csv_path)
        self._preprocess_data()
        self.drug_mappings = self._load_comprehensive_drug_mappings()
        self.specialty_mappings = self._load_comprehensive_specialty_mappings()
        self.state_mappings = self._load_comprehensive_state_mappings()
        self.condition_mappings = self._load_comprehensive_condition_mappings()
        self.payer_mappings = self._load_comprehensive_payer_mappings()
        self.hospital_mappings = self._load_comprehensive_hospital_mappings()
        self._create_search_indices()
        self._initialize_semantic_search()
        self._create_analytics_cache()
    
    def _preprocess_data(self):
        self.hcp_df['name'] = self.hcp_df['first_name'] + ' ' + self.hcp_df['last_name']
        self.hcp_df['npi'] = self.hcp_df['type_1_npi'].astype(str)
        
        array_columns = ['specialties', 'states', 'hospital_names', 'system_names']
        for col in array_columns:
            if col in self.hcp_df.columns:
                self.hcp_df[col] = self.hcp_df[col].apply(self._parse_array_string)
        
        if not self.claims_df.empty:
            date_columns = ['SERVICE_DATE_DD', 'DATE_PRESCRIPTION_WRITTEN_DD']
            for col in date_columns:
                if col in self.claims_df.columns:
                    self.claims_df[col] = pd.to_datetime(self.claims_df[col], errors='coerce')
            
            if 'NDC_GENERIC_NM' in self.claims_df.columns:
                self.claims_df['generic_name_normalized'] = self.claims_df['NDC_GENERIC_NM'].str.lower().str.strip()
            if 'NDC_PREFERRED_BRAND_NM' in self.claims_df.columns:
                self.claims_df['brand_name_normalized'] = self.claims_df['NDC_PREFERRED_BRAND_NM'].str.lower().str.strip()
            
            drug_fields = []
            for col in ['generic_name_normalized', 'brand_name_normalized']:
                if col in self.claims_df.columns:
                    drug_fields.append(self.claims_df[col].fillna(''))
            
            if drug_fields:
                self.claims_df['all_drug_names'] = drug_fields[0]
                for field in drug_fields[1:]:
                    self.claims_df['all_drug_names'] += ' ' + field
            
            if 'PRESCRIBER_NPI_NBR' in self.claims_df.columns:
                self.claims_df['PRESCRIBER_NPI_NBR'] = self.claims_df['PRESCRIBER_NPI_NBR'].astype(str)
    
    def _load_comprehensive_drug_mappings(self) -> Dict[str, List[str]]:
        """Load comprehensive drug name mappings with all brand/generic variants and drug classes"""
        return {
            # Immunology drugs (Abbvie focus)
            "adalimumab": ["adalimumab", "humira", "amjevita", "cyltezo", "hadlima", "hyrimoz", "idacio", "yuflyma"],
            "humira": ["adalimumab", "humira", "amjevita", "cyltezo", "hadlima", "hyrimoz", "idacio", "yuflyma"],
            "upadacitinib": ["upadacitinib", "rinvoq"],
            "rinvoq": ["upadacitinib", "rinvoq"],
            "risankizumab": ["risankizumab", "skyrizi"],
            "skyrizi": ["risankizumab", "skyrizi"],
            # TNF inhibitors
            "infliximab": ["infliximab", "remicade", "inflectra", "renflexis", "avsola", "ixifi"],
            "remicade": ["infliximab", "remicade", "inflectra", "renflexis", "avsola", "ixifi"],
            "etanercept": ["etanercept", "enbrel", "erelzi", "eticovo"],
            "enbrel": ["etanercept", "enbrel", "erelzi", "eticovo"],
            "certolizumab": ["certolizumab", "cimzia"],
            "cimzia": ["certolizumab", "cimzia"],
            "golimumab": ["golimumab", "simponi"],
            "simponi": ["golimumab", "simponi"],
            # JAK inhibitors
            "tofacitinib": ["tofacitinib", "xeljanz"],
            "xeljanz": ["tofacitinib", "xeljanz"],
            "baricitinib": ["baricitinib", "olumiant"],
            "olumiant": ["baricitinib", "olumiant"],
            # IL-17 inhibitors
            "secukinumab": ["secukinumab", "cosentyx"],
            "cosentyx": ["secukinumab", "cosentyx"],
            "ixekizumab": ["ixekizumab", "taltz"],
            "taltz": ["ixekizumab", "taltz"],
            # IL-23 inhibitors
            "guselkumab": ["guselkumab", "tremfya"],
            "tremfya": ["guselkumab", "tremfya"],
            "tildrakizumab": ["tildrakizumab", "ilumya"],
            "ilumya": ["tildrakizumab", "ilumya"],
            # Diabetes drugs
            "tirzepatide": ["tirzepatide", "mounjaro", "zepbound"],
            "mounjaro": ["tirzepatide", "mounjaro", "zepbound"],
            "semaglutide": ["semaglutide", "ozempic", "wegovy", "rybelsus"],
            "ozempic": ["semaglutide", "ozempic", "wegovy", "rybelsus"],
            "wegovy": ["semaglutide", "ozempic", "wegovy", "rybelsus"],
            "dulaglutide": ["dulaglutide", "trulicity"],
            "trulicity": ["dulaglutide", "trulicity"],
            "liraglutide": ["liraglutide", "victoza", "saxenda"],
            "victoza": ["liraglutide", "victoza", "saxenda"],
            "exenatide": ["exenatide", "byetta", "bydureon"],
            "byetta": ["exenatide", "byetta", "bydureon"],
            "metformin": ["metformin", "glucophage", "fortamet", "glumetza"],
            "insulin": ["insulin", "humalog", "novolog", "lantus", "levemir", "tresiba", "basaglar", "toujeo"],
            # Oncology drugs
            "rituximab": ["rituximab", "rituxan", "truxima", "ruxience"],
            "rituxan": ["rituximab", "rituxan", "truxima", "ruxience"],
            "pembrolizumab": ["pembrolizumab", "keytruda"],
            "keytruda": ["pembrolizumab", "keytruda"],
            "nivolumab": ["nivolumab", "opdivo"],
            "opdivo": ["nivolumab", "opdivo"],
            # Drug classes for broader searches
            "tnf inhibitors": ["adalimumab", "humira", "infliximab", "remicade", "etanercept", "enbrel", "certolizumab", "cimzia", "golimumab", "simponi"],
            "jak inhibitors": ["tofacitinib", "xeljanz", "baricitinib", "olumiant", "upadacitinib", "rinvoq"],
            "glp1 agonists": ["semaglutide", "ozempic", "wegovy", "tirzepatide", "mounjaro", "dulaglutide", "trulicity", "liraglutide", "victoza"],
            "biologics": ["adalimumab", "humira", "infliximab", "remicade", "etanercept", "enbrel", "rituximab", "rituxan", "pembrolizumab", "keytruda"],
            "checkpoint inhibitors": ["pembrolizumab", "keytruda", "nivolumab", "opdivo", "ipilimumab", "yervoy"],
            "immunosuppressants": ["methotrexate", "sulfasalazine", "hydroxychloroquine", "leflunomide", "azathioprine"]
        }
    
    def _load_comprehensive_specialty_mappings(self) -> Dict[str, List[str]]:
        """Load comprehensive specialty mappings with all variants and subspecialties"""
        return {
            # Primary care
            'family medicine': ['family medicine', 'family practice', 'family physician', 'fp'],
            'internal medicine': ['internal medicine', 'internal med', 'internist', 'im'],
            'general practice': ['general practice', 'general practitioner', 'gp'],
            # Neurology
            'neurologist': ['neurology', 'neurological', 'neurological surgery', 'neurosurgery', 'brain surgery'],
            'neurology': ['neurology', 'neurological', 'neurologist', 'brain specialist'],
            'neurosurgery': ['neurosurgery', 'neurological surgery', 'brain surgery', 'spine surgery'],
            # Rheumatology
            'rheumatologist': ['rheumatology', 'rheumatic', 'arthritis specialist', 'joint specialist'],
            'rheumatology': ['rheumatology', 'rheumatic', 'arthritis', 'autoimmune'],
            # Dermatology
            'dermatologist': ['dermatology', 'dermatologic', 'skin specialist', 'skin doctor'],
            'dermatology': ['dermatology', 'dermatologic', 'skin'],
            # Endocrinology
            'endocrinologist': ['endocrinology', 'endocrine', 'diabetes specialist', 'hormone specialist'],
            'endocrinology': ['endocrinology', 'endocrine', 'diabetes', 'hormone', 'metabolic'],
            # Cardiology
            'cardiologist': ['cardiology', 'cardiac', 'cardiovascular', 'heart specialist'],
            'cardiology': ['cardiology', 'cardiac', 'cardiovascular', 'heart'],
            # Oncology
            'oncologist': ['oncology', 'hematology', 'medical oncology', 'cancer specialist'],
            'oncology': ['oncology', 'hematology', 'medical oncology', 'cancer', 'tumor'],
            'hematology': ['hematology', 'hematologist', 'blood specialist', 'blood cancer'],
            # Gastroenterology
            'gastroenterologist': ['gastroenterology', 'gi', 'digestive', 'stomach specialist'],
            'gastroenterology': ['gastroenterology', 'gi', 'digestive', 'gastrointestinal'],
            # Pulmonology
            'pulmonologist': ['pulmonology', 'pulmonary', 'lung specialist', 'respiratory'],
            'pulmonology': ['pulmonology', 'pulmonary', 'lung', 'respiratory'],
            # Nephrology
            'nephrologist': ['nephrology', 'kidney specialist', 'renal'],
            'nephrology': ['nephrology', 'kidney', 'renal'],
            # Infectious Disease
            'infectious disease': ['infectious disease', 'id', 'infectious diseases', 'infection specialist'],
            # Immunology
            'immunologist': ['immunology', 'allergy', 'immunology and allergy', 'immune system'],
            'immunology': ['immunology', 'allergy', 'immune', 'autoimmune'],
            # Pain Medicine
            'pain medicine': ['pain medicine', 'pain management', 'pain specialist', 'chronic pain'],
            'pain management': ['pain management', 'pain medicine', 'pain specialist'],
            # Physical Medicine
            'physical medicine': ['physical medicine', 'rehabilitation', 'pm&r', 'physiatry'],
            'rehabilitation': ['rehabilitation', 'physical medicine', 'pm&r', 'physiatry'],
            # Psychiatry
            'psychiatrist': ['psychiatry', 'mental health', 'psychiatric'],
            'psychiatry': ['psychiatry', 'mental health', 'psychiatric'],
            # Emergency Medicine
            'emergency medicine': ['emergency medicine', 'emergency', 'er', 'emergency room'],
            # Anesthesiology
            'anesthesiologist': ['anesthesiology', 'anesthesia', 'anesthetist'],
            'anesthesiology': ['anesthesiology', 'anesthesia'],
            # Surgery specialties
            'surgeon': ['surgery', 'surgical', 'general surgery'],
            'surgery': ['surgery', 'surgical', 'general surgery'],
            'orthopedic': ['orthopedic', 'orthopedics', 'orthopedic surgery', 'bone', 'joint'],
            'plastic surgery': ['plastic surgery', 'cosmetic surgery', 'reconstructive'],
            # Pediatrics
            'pediatrician': ['pediatrics', 'pediatric', 'child specialist', 'children'],
            'pediatrics': ['pediatrics', 'pediatric', 'child', 'children'],
            # Obstetrics/Gynecology
            'obgyn': ['obstetrics', 'gynecology', 'ob/gyn', 'women health'],
            'gynecology': ['gynecology', 'gynecologist', 'women health'],
            'obstetrics': ['obstetrics', 'obstetrician', 'pregnancy'],
            # Radiology
            'radiologist': ['radiology', 'imaging', 'diagnostic radiology'],
            'radiology': ['radiology', 'imaging', 'diagnostic imaging'],
            # Pathology
            'pathologist': ['pathology', 'laboratory medicine', 'lab medicine'],
            'pathology': ['pathology', 'laboratory', 'lab'],
            # Ophthalmology
            'ophthalmologist': ['ophthalmology', 'eye specialist', 'eye doctor'],
            'ophthalmology': ['ophthalmology', 'eye', 'vision'],
            # ENT
            'ent': ['otolaryngology', 'ent', 'ear nose throat', 'head and neck'],
            'otolaryngology': ['otolaryngology', 'ent', 'ear nose throat'],
            # Urology
            'urologist': ['urology', 'urological', 'kidney', 'bladder'],
            'urology': ['urology', 'urological', 'genitourinary']
        }
    
    def _load_comprehensive_state_mappings(self) -> Dict[str, List[str]]:
        """Load comprehensive state mappings with all US states, territories, and common variations"""
        return {
            'AL': ['Alabama', 'AL', 'Ala'], 'AK': ['Alaska', 'AK'], 'AZ': ['Arizona', 'AZ', 'Ariz'],
            'AR': ['Arkansas', 'AR', 'Ark'], 'CA': ['California', 'CA', 'Calif', 'Cal'],
            'CO': ['Colorado', 'CO', 'Colo'], 'CT': ['Connecticut', 'CT', 'Conn'],
            'DE': ['Delaware', 'DE', 'Del'], 'FL': ['Florida', 'FL', 'Fla'],
            'GA': ['Georgia', 'GA'], 'HI': ['Hawaii', 'HI'], 'ID': ['Idaho', 'ID'],
            'IL': ['Illinois', 'IL', 'Ill'], 'IN': ['Indiana', 'IN', 'Ind'],
            'IA': ['Iowa', 'IA'], 'KS': ['Kansas', 'KS', 'Kan', 'Kans'],
            'KY': ['Kentucky', 'KY', 'Ky'], 'LA': ['Louisiana', 'LA', 'La'],
            'ME': ['Maine', 'ME'], 'MD': ['Maryland', 'MD', 'Md'],
            'MA': ['Massachusetts', 'MA', 'Mass'], 'MI': ['Michigan', 'MI', 'Mich'],
            'MN': ['Minnesota', 'MN', 'Minn'], 'MS': ['Mississippi', 'MS', 'Miss'],
            'MO': ['Missouri', 'MO', 'Mo'], 'MT': ['Montana', 'MT', 'Mont'],
            'NE': ['Nebraska', 'NE', 'Neb', 'Nebr'], 'NV': ['Nevada', 'NV', 'Nev'],
            'NH': ['New Hampshire', 'NH', 'N.H.'], 'NJ': ['New Jersey', 'NJ', 'N.J.'],
            'NM': ['New Mexico', 'NM', 'N.M.', 'N. Mex'], 'NY': ['New York', 'NY', 'N.Y.'],
            'NC': ['North Carolina', 'NC', 'N.C.'], 'ND': ['North Dakota', 'ND', 'N.D.', 'N. Dak'],
            'OH': ['Ohio', 'OH'], 'OK': ['Oklahoma', 'OK', 'Okla'], 'OR': ['Oregon', 'OR', 'Ore'],
            'PA': ['Pennsylvania', 'PA', 'Pa', 'Penn'], 'RI': ['Rhode Island', 'RI', 'R.I.'],
            'SC': ['South Carolina', 'SC', 'S.C.'], 'SD': ['South Dakota', 'SD', 'S.D.', 'S. Dak'],
            'TN': ['Tennessee', 'TN', 'Tenn'], 'TX': ['Texas', 'TX', 'Tex'],
            'UT': ['Utah', 'UT'], 'VT': ['Vermont', 'VT', 'Vt'],
            'VA': ['Virginia', 'VA', 'Va'], 'WA': ['Washington', 'WA', 'Wash'],
            'WV': ['West Virginia', 'WV', 'W.V.', 'W. Va'], 'WI': ['Wisconsin', 'WI', 'Wis', 'Wisc'],
            'WY': ['Wyoming', 'WY', 'Wyo'],
            'DC': ['District of Columbia', 'DC', 'D.C.', 'Washington DC', 'Washington D.C.'],
            'PR': ['Puerto Rico', 'PR'], 'VI': ['Virgin Islands', 'VI', 'U.S. Virgin Islands'],
            'GU': ['Guam', 'GU'], 'AS': ['American Samoa', 'AS'],
            'MP': ['Northern Mariana Islands', 'MP', 'CNMI']
        }
    
    def _load_comprehensive_condition_mappings(self) -> Dict[str, List[str]]:
        """Load comprehensive medical condition mappings with all variants and related terms"""
        return {
            # Autoimmune/Rheumatologic
            'rheumatoid arthritis': ['rheumatoid arthritis', 'ra', 'inflammatory arthritis'],
            'psoriatic arthritis': ['psoriatic arthritis', 'psa', 'psoriatic joint disease'],
            'ankylosing spondylitis': ['ankylosing spondylitis', 'as', 'axial spondyloarthritis'],
            'systemic lupus erythematosus': ['systemic lupus erythematosus', 'sle', 'lupus'],
            'inflammatory bowel disease': ['inflammatory bowel disease', 'ibd', 'crohns disease', 'ulcerative colitis'],
            'crohns disease': ['crohns disease', 'crohn disease', 'regional enteritis'],
            'ulcerative colitis': ['ulcerative colitis', 'uc', 'chronic ulcerative colitis'],
            'psoriasis': ['psoriasis', 'plaque psoriasis', 'psoriatic skin disease'],
            'multiple sclerosis': ['multiple sclerosis', 'ms', 'demyelinating disease'],
            'fibromyalgia': ['fibromyalgia', 'chronic pain syndrome', 'fibromyalgia syndrome'],
            # Diabetes/Endocrine
            'diabetes': ['diabetes', 'diabetes mellitus', 'diabetic', 'dm'],
            'type 1 diabetes': ['type 1 diabetes', 't1dm', 'insulin dependent diabetes'],
            'type 2 diabetes': ['type 2 diabetes', 't2dm', 'non-insulin dependent diabetes'],
            'obesity': ['obesity', 'overweight', 'weight management', 'bariatric'],
            'thyroid disease': ['thyroid disease', 'hypothyroidism', 'hyperthyroidism'],
            # Cardiovascular
            'heart disease': ['heart disease', 'cardiac disease', 'cardiovascular disease', 'cvd'],
            'hypertension': ['hypertension', 'high blood pressure', 'htn'],
            'heart failure': ['heart failure', 'congestive heart failure', 'chf'],
            'atrial fibrillation': ['atrial fibrillation', 'afib', 'a-fib'],
            'coronary artery disease': ['coronary artery disease', 'cad', 'coronary heart disease'],
            # Neurological
            'alzheimers': ['alzheimers disease', 'alzheimer disease', 'dementia', 'alzheimers dementia'],
            'parkinsons': ['parkinsons disease', 'parkinson disease', 'pd'],
            'epilepsy': ['epilepsy', 'seizure disorder', 'seizures'],
            'migraine': ['migraine', 'migraine headache', 'chronic migraine'],
            'stroke': ['stroke', 'cerebrovascular accident', 'cva'],
            'neuropathy': ['neuropathy', 'peripheral neuropathy', 'diabetic neuropathy'],
            # Oncology
            'cancer': ['cancer', 'carcinoma', 'tumor', 'malignancy', 'neoplasm'],
            'breast cancer': ['breast cancer', 'mammary carcinoma'],
            'lung cancer': ['lung cancer', 'pulmonary carcinoma', 'bronchogenic carcinoma'],
            'colon cancer': ['colon cancer', 'colorectal cancer', 'bowel cancer'],
            'prostate cancer': ['prostate cancer', 'prostatic carcinoma'],
            'lymphoma': ['lymphoma', 'hodgkin lymphoma', 'non-hodgkin lymphoma'],
            'leukemia': ['leukemia', 'blood cancer', 'hematologic malignancy'],
            # Respiratory
            'asthma': ['asthma', 'bronchial asthma', 'allergic asthma'],
            'copd': ['copd', 'chronic obstructive pulmonary disease', 'emphysema', 'chronic bronchitis'],
            'pneumonia': ['pneumonia', 'lung infection', 'pulmonary infection'],
            # Gastrointestinal
            'gerd': ['gerd', 'gastroesophageal reflux disease', 'acid reflux'],
            'peptic ulcer': ['peptic ulcer', 'gastric ulcer', 'duodenal ulcer'],
            'hepatitis': ['hepatitis', 'liver inflammation', 'viral hepatitis'],
            'cirrhosis': ['cirrhosis', 'liver cirrhosis', 'hepatic cirrhosis'],
            # Mental Health
            'depression': ['depression', 'major depressive disorder', 'mdd'],
            'anxiety': ['anxiety', 'anxiety disorder', 'generalized anxiety'],
            'bipolar': ['bipolar disorder', 'manic depression', 'bipolar disease'],
            'schizophrenia': ['schizophrenia', 'psychotic disorder'],
            # Infectious Disease
            'hiv': ['hiv', 'human immunodeficiency virus', 'aids'],
            'hepatitis b': ['hepatitis b', 'hbv', 'chronic hepatitis b'],
            'hepatitis c': ['hepatitis c', 'hcv', 'chronic hepatitis c'],
            'tuberculosis': ['tuberculosis', 'tb', 'pulmonary tuberculosis'],
            # Pain/Musculoskeletal
            'chronic pain': ['chronic pain', 'persistent pain', 'pain syndrome'],
            'back pain': ['back pain', 'lower back pain', 'lumbar pain'],
            'arthritis': ['arthritis', 'joint inflammation', 'arthritic'],
            'osteoarthritis': ['osteoarthritis', 'oa', 'degenerative joint disease'],
            'osteoporosis': ['osteoporosis', 'bone loss', 'osteopenia'],
            # Kidney/Renal
            'chronic kidney disease': ['chronic kidney disease', 'ckd', 'renal disease'],
            'kidney failure': ['kidney failure', 'renal failure', 'end stage renal disease'],
            # Eye/Vision
            'glaucoma': ['glaucoma', 'increased intraocular pressure'],
            'macular degeneration': ['macular degeneration', 'amd', 'age-related macular degeneration'],
            'diabetic retinopathy': ['diabetic retinopathy', 'diabetic eye disease'],
            # Skin
            'eczema': ['eczema', 'atopic dermatitis', 'dermatitis'],
            'acne': ['acne', 'acne vulgaris', 'comedonal acne'],
            # Research areas
            'immunotherapy': ['immunotherapy', 'immune checkpoint inhibitors', 'car-t'],
            'gene therapy': ['gene therapy', 'genetic therapy', 'genomic medicine'],
            'precision medicine': ['precision medicine', 'personalized medicine', 'targeted therapy']
        }
    
    def _load_comprehensive_payer_mappings(self) -> Dict[str, List[str]]:
        """Load comprehensive payer/insurance mappings with all major payers and plan types"""
        return {
            # Government programs
            'medicare': ['medicare', 'medicare part d', 'cms', 'medicare advantage', 'medicare part c'],
            'medicaid': ['medicaid', 'state medicaid', 'managed medicaid', 'medicaid mco'],
            'tricare': ['tricare', 'military insurance', 'dod'],
            'va': ['va', 'veterans affairs', 'veterans administration'],
            # Commercial payers
            'commercial': ['commercial', 'private insurance', 'employer insurance'],
            'aetna': ['aetna', 'cvs health', 'cvs aetna'],
            'anthem': ['anthem', 'wellpoint', 'blue cross blue shield'],
            'cigna': ['cigna', 'cigna healthcare'],
            'humana': ['humana', 'humana inc'],
            'unitedhealth': ['unitedhealth', 'united healthcare', 'uhc', 'optum'],
            'kaiser': ['kaiser', 'kaiser permanente', 'kp'],
            'bcbs': ['blue cross blue shield', 'bcbs', 'anthem', 'blue cross', 'blue shield'],
            # Plan types
            'hmo': ['hmo', 'health maintenance organization'],
            'ppo': ['ppo', 'preferred provider organization'],
            'pos': ['pos', 'point of service'],
            'epo': ['epo', 'exclusive provider organization'],
            'hdhp': ['hdhp', 'high deductible health plan', 'consumer directed'],
            # Payment methods
            'cash': ['cash', 'self pay', 'uninsured', 'out of pocket'],
            'charity': ['charity care', 'financial assistance', 'indigent care'],
            # Specialty payers
            'workers comp': ['workers compensation', 'workers comp', 'work comp'],
            'auto insurance': ['auto insurance', 'motor vehicle', 'pip'],
            'liability': ['liability insurance', 'third party liability']
        }
    
    def _load_comprehensive_hospital_mappings(self) -> Dict[str, List[str]]:
        """Load comprehensive hospital and health system mappings"""
        return {
            # Major health systems
            'mayo clinic': ['mayo clinic', 'mayo', 'mayo health system'],
            'cleveland clinic': ['cleveland clinic', 'ccf', 'cleveland clinic foundation'],
            'johns hopkins': ['johns hopkins', 'jhm', 'johns hopkins medicine'],
            'mass general': ['massachusetts general hospital', 'mass general', 'mgh'],
            'brigham': ['brigham and womens hospital', 'brigham', 'bwh'],
            'mount sinai': ['mount sinai', 'mount sinai health system', 'sinai'],
            'nyu': ['nyu langone', 'new york university', 'nyu medical center'],
            'ucla': ['ucla', 'university of california los angeles', 'ucla health'],
            'ucsf': ['ucsf', 'university of california san francisco', 'ucsf health'],
            'stanford': ['stanford', 'stanford health care', 'stanford medicine'],
            'duke': ['duke', 'duke university hospital', 'duke health'],
            'emory': ['emory', 'emory healthcare', 'emory university hospital'],
            'vanderbilt': ['vanderbilt', 'vanderbilt university medical center', 'vumc'],
            'university of michigan': ['university of michigan', 'michigan medicine', 'u of m'],
            'northwestern': ['northwestern', 'northwestern medicine', 'nm'],
            'university of chicago': ['university of chicago', 'uchicago medicine'],
            'washington university': ['washington university', 'wustl', 'barnes jewish'],
            'university of pennsylvania': ['university of pennsylvania', 'penn medicine', 'upenn'],
            'jefferson': ['jefferson', 'thomas jefferson university', 'jefferson health'],
            'temple': ['temple', 'temple university hospital', 'temple health'],
            'houston methodist': ['houston methodist', 'methodist hospital', 'methodist'],
            'md anderson': ['md anderson', 'university of texas md anderson', 'mdacc'],
            'memorial sloan kettering': ['memorial sloan kettering', 'msk', 'sloan kettering'],
            'dana farber': ['dana farber', 'dfci', 'dana farber cancer institute'],
            # Hospital types
            'academic': ['university', 'medical school', 'teaching hospital', 'academic medical center'],
            'community': ['community hospital', 'regional medical center', 'local hospital'],
            'safety net': ['safety net', 'public hospital', 'county hospital'],
            'specialty': ['specialty hospital', 'rehabilitation', 'psychiatric', 'childrens'],
            'critical access': ['critical access hospital', 'rural hospital', 'cah']
        }
    
    def _create_search_indices(self):
        """Create comprehensive search indices and caches for fast lookups"""
        self.npi_to_hcp = dict(zip(self.hcp_df['npi'], self.hcp_df.index))
        
        # Create specialty index
        self.specialty_index = defaultdict(set)
        for idx, row in self.hcp_df.iterrows():
            if isinstance(row['specialties'], list):
                for specialty in row['specialties']:
                    self.specialty_index[specialty.lower()].add(idx)
        
        # Create state index
        self.state_index = defaultdict(set)
        for idx, row in self.hcp_df.iterrows():
            if isinstance(row['states'], list):
                for state in row['states']:
                    self.state_index[state.lower()].add(idx)
        
        # Create hospital index
        self.hospital_index = defaultdict(set)
        for idx, row in self.hcp_df.iterrows():
            if isinstance(row['hospital_names'], list):
                for hospital in row['hospital_names']:
                    self.hospital_index[hospital.lower()].add(idx)
    
    def _initialize_semantic_search(self):
        """Initialize semantic search capabilities for qualitative queries"""
        try:
            # Create text corpus for semantic search
            text_fields = []
            for _, row in self.hcp_df.iterrows():
                text_parts = []
                
                # Add specialties
                if isinstance(row['specialties'], list):
                    text_parts.extend([str(s) for s in row['specialties']])
                
                # Add conditions
                if isinstance(row.get('conditions', []), list):
                    text_parts.extend([str(c) for c in row['conditions']])
                
                # Add affiliations
                if isinstance(row.get('affiliations', []), list):
                    for aff in row['affiliations']:
                        if isinstance(aff, dict):
                            text_parts.extend([str(v) for v in aff.values() if isinstance(v, str)])
                        else:
                            text_parts.append(str(aff))
                
                # Add hospital and system names
                for field in ['hospital_names', 'system_names']:
                    if isinstance(row.get(field, []), list):
                        text_parts.extend([str(h) for h in row[field]])
                
                text_fields.append(' '.join(text_parts).lower())
            
            # Initialize TF-IDF vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1
            )
            
            # Fit vectorizer if we have text data
            if text_fields and any(text_fields):
                self.tfidf_matrix = self.vectorizer.fit_transform(text_fields)
                self.semantic_search_enabled = True
            else:
                self.semantic_search_enabled = False
                
        except ImportError:
            print("Warning: sklearn not available. Semantic search disabled.")
            self.semantic_search_enabled = False
        except Exception as e:
            print(f"Warning: Could not initialize semantic search: {e}")
            self.semantic_search_enabled = False
    
    def _create_analytics_cache(self):
        """Create comprehensive analytics cache for performance optimization"""
        self.analytics_cache = {}
        
        # Cache percentile calculations
        if 'num_publications' in self.hcp_df.columns:
            self.analytics_cache['publication_percentiles'] = np.percentile(
                self.hcp_df['num_publications'].fillna(0), 
                [10, 25, 50, 75, 90, 95, 99]
            )
        
        if 'num_clinical_trials' in self.hcp_df.columns:
            self.analytics_cache['trial_percentiles'] = np.percentile(
                self.hcp_df['num_clinical_trials'].fillna(0), 
                [10, 25, 50, 75, 90, 95, 99]
            )
        
        # Cache specialty distributions
        specialty_counts = defaultdict(int)
        for _, row in self.hcp_df.iterrows():
            if isinstance(row['specialties'], list):
                for specialty in row['specialties']:
                    specialty_counts[specialty.lower()] += 1
        self.analytics_cache['specialty_distribution'] = dict(specialty_counts)
        
        # Cache state distributions
        state_counts = defaultdict(int)
        for _, row in self.hcp_df.iterrows():
            if isinstance(row['states'], list):
                for state in row['states']:
                    state_counts[state] += 1
        self.analytics_cache['state_distribution'] = dict(state_counts)
    
    def _parse_array_string(self, value) -> List[str]:
        if pd.isna(value) or value == '':
            return []
        try:
            if isinstance(value, str):
                return json.loads(value)
            return value if isinstance(value, list) else []
        except:
            return []
    
    def execute_plan(self, plan: Dict[str, Any]) -> pd.DataFrame:
        result_df = self.hcp_df.copy()
        
        if plan.get('filters'):
            result_df = self._apply_hcp_filters(result_df, plan['filters'])
        
        claims_filters = plan.get('claims_filters')
        if claims_filters:
            result_df = self._join_with_claims(result_df, claims_filters)
        
        if plan.get('projection'):
            result_df = self._apply_projection(result_df, plan['projection'])
        
        if plan.get('order_by'):
            result_df = self._apply_ordering(result_df, plan['order_by'])
        
        if plan.get('limit'):
            result_df = result_df.head(plan['limit'])
        
        return result_df
    
    def _apply_hcp_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply comprehensive HCP filters with extensive edge case handling"""
        result_df = df.copy()
        
        # Specialty filters with comprehensive matching
        if filters.get('specialty_any'):
            result_df = self._apply_specialty_filter(result_df, filters['specialty_any'], 'any')
        if filters.get('specialty_all'):
            result_df = self._apply_specialty_filter(result_df, filters['specialty_all'], 'all')
        if filters.get('specialty_exclude'):
            result_df = self._apply_specialty_filter(result_df, filters['specialty_exclude'], 'exclude')
        
        # State/location filters
        if filters.get('state_any'):
            result_df = self._apply_state_filter(result_df, filters['state_any'], 'any')
        if filters.get('state_all'):
            result_df = self._apply_state_filter(result_df, filters['state_all'], 'all')
        if filters.get('state_exclude'):
            result_df = self._apply_state_filter(result_df, filters['state_exclude'], 'exclude')
        
        # Hospital/system filters
        if filters.get('hospital_any'):
            result_df = self._apply_hospital_filter(result_df, filters['hospital_any'], 'any')
        if filters.get('hospital_all'):
            result_df = self._apply_hospital_filter(result_df, filters['hospital_all'], 'all')
        if filters.get('hospital_exclude'):
            result_df = self._apply_hospital_filter(result_df, filters['hospital_exclude'], 'exclude')
        
        if filters.get('system_any'):
            result_df = self._apply_system_filter(result_df, filters['system_any'], 'any')
        if filters.get('system_all'):
            result_df = self._apply_system_filter(result_df, filters['system_all'], 'all')
        if filters.get('system_exclude'):
            result_df = self._apply_system_filter(result_df, filters['system_exclude'], 'exclude')
        
        # Organization type filters
        if filters.get('org_type_any'):
            result_df = self._apply_org_type_filter(result_df, filters['org_type_any'], 'any')
        if filters.get('org_type_exclude'):
            result_df = self._apply_org_type_filter(result_df, filters['org_type_exclude'], 'exclude')
        
        # Publication filters with comprehensive range handling
        result_df = self._apply_numeric_filters(result_df, filters, 'publications', 'num_publications')
        result_df = self._apply_numeric_filters(result_df, filters, 'clinical_trials', 'num_clinical_trials')
        result_df = self._apply_numeric_filters(result_df, filters, 'payments', 'num_payments')
        
        # Social media filters
        result_df = self._apply_boolean_filters(result_df, filters, ['has_linkedin', 'has_twitter', 'has_youtube', 'has_podcast'])
        
        # Social media comprehensive filters
        if filters.get('social_media_any'):
            result_df = self._apply_social_media_filter(result_df, filters['social_media_any'], 'any')
        if filters.get('social_media_all'):
            result_df = self._apply_social_media_filter(result_df, filters['social_media_all'], 'all')
        
        # Demographic filters
        if filters.get('gender'):
            result_df = self._apply_gender_filter(result_df, filters['gender'])
        
        # Name filters
        if filters.get('name_contains'):
            result_df = self._apply_name_filter(result_df, filters['name_contains'])
        
        # Email domain filters
        if filters.get('email_domain'):
            result_df = self._apply_email_domain_filter(result_df, filters['email_domain'])
        
        # Condition filters
        if filters.get('conditions_any'):
            result_df = self._apply_condition_filter(result_df, filters['conditions_any'], 'any')
        if filters.get('conditions_all'):
            result_df = self._apply_condition_filter(result_df, filters['conditions_all'], 'all')
        if filters.get('conditions_exclude'):
            result_df = self._apply_condition_filter(result_df, filters['conditions_exclude'], 'exclude')
        
        # Percentile filters
        if filters.get('top_percentile_publications'):
            result_df = self._apply_percentile_filter(result_df, 'num_publications', filters['top_percentile_publications'])
        if filters.get('top_percentile_trials'):
            result_df = self._apply_percentile_filter(result_df, 'num_clinical_trials', filters['top_percentile_trials'])
        
        # Practice setting filters
        if filters.get('academic_only'):
            result_df = self._apply_academic_filter(result_df, True)
        if filters.get('community_only'):
            result_df = self._apply_community_filter(result_df, True)
        if filters.get('rural_states_only'):
            result_df = self._apply_rural_states_filter(result_df, True)
        
        # Text search with semantic capabilities
        if filters.get('text_search'):
            result_df = self._apply_text_search_filter(result_df, filters['text_search'])
        
        return result_df
    
    def _apply_specialty_filter(self, df: pd.DataFrame, specialties: List[str], mode: str) -> pd.DataFrame:
        """Apply specialty filters with comprehensive matching including subspecialties"""
        if mode == 'any':
            mask = df['specialties'].apply(
                lambda x: any(self._fuzzy_match_specialty(spec, x) for spec in specialties) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'all':
            mask = df['specialties'].apply(
                lambda x: all(any(self._fuzzy_match_specialty(spec, x) for spec in specialties) for spec in specialties) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'exclude':
            mask = df['specialties'].apply(
                lambda x: not any(self._fuzzy_match_specialty(spec, x) for spec in specialties) if isinstance(x, list) else True
            )
            return df[mask]
        return df
    
    def _apply_state_filter(self, df: pd.DataFrame, states: List[str], mode: str) -> pd.DataFrame:
        """Apply state filters with comprehensive state name mapping"""
        expanded_states = self._expand_state_names(states)
        if mode == 'any':
            mask = df['states'].apply(
                lambda x: any(self._fuzzy_match(state, x) for state in expanded_states) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'all':
            mask = df['states'].apply(
                lambda x: all(any(self._fuzzy_match(state, x) for state in expanded_states) for state in states) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'exclude':
            mask = df['states'].apply(
                lambda x: not any(self._fuzzy_match(state, x) for state in expanded_states) if isinstance(x, list) else True
            )
            return df[mask]
        return df
    
    def _apply_hospital_filter(self, df: pd.DataFrame, hospitals: List[str], mode: str) -> pd.DataFrame:
        """Apply hospital filters with comprehensive hospital name mapping"""
        if mode == 'any':
            mask = df['hospital_names'].apply(
                lambda x: any(self._fuzzy_match_hospital(hosp, x) for hosp in hospitals) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'all':
            mask = df['hospital_names'].apply(
                lambda x: all(any(self._fuzzy_match_hospital(hosp, x) for hosp in hospitals) for hosp in hospitals) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'exclude':
            mask = df['hospital_names'].apply(
                lambda x: not any(self._fuzzy_match_hospital(hosp, x) for hosp in hospitals) if isinstance(x, list) else True
            )
            return df[mask]
        return df
    
    def _apply_system_filter(self, df: pd.DataFrame, systems: List[str], mode: str) -> pd.DataFrame:
        """Apply health system filters with comprehensive system name mapping"""
        if mode == 'any':
            mask = df['system_names'].apply(
                lambda x: any(self._fuzzy_match_hospital(sys, x) for sys in systems) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'all':
            mask = df['system_names'].apply(
                lambda x: all(any(self._fuzzy_match_hospital(sys, x) for sys in systems) for sys in systems) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'exclude':
            mask = df['system_names'].apply(
                lambda x: not any(self._fuzzy_match_hospital(sys, x) for sys in systems) if isinstance(x, list) else True
            )
            return df[mask]
        return df
    
    def _apply_org_type_filter(self, df: pd.DataFrame, org_types: List[str], mode: str) -> pd.DataFrame:
        """Apply organization type filters"""
        if mode == 'any':
            mask = df['org_type'].apply(
                lambda x: any(self._fuzzy_match(ot, [x]) for ot in org_types) if pd.notna(x) else False
            )
            return df[mask]
        elif mode == 'exclude':
            mask = df['org_type'].apply(
                lambda x: not any(self._fuzzy_match(ot, [x]) for ot in org_types) if pd.notna(x) else True
            )
            return df[mask]
        return df
    
    def _apply_numeric_filters(self, df: pd.DataFrame, filters: Dict[str, Any], prefix: str, column: str) -> pd.DataFrame:
        """Apply comprehensive numeric filters with range, min, max, and edge case handling"""
        if column not in df.columns:
            return df
        
        result_df = df.copy()
        
        # Handle min filter
        min_key = f'{prefix}_min'
        if filters.get(min_key) is not None:
            min_val = filters[min_key]
            result_df = result_df[result_df[column].fillna(0) >= min_val]
        
        # Handle max filter
        max_key = f'{prefix}_max'
        if filters.get(max_key) is not None:
            max_val = filters[max_key]
            result_df = result_df[result_df[column].fillna(0) <= max_val]
        
        # Handle range filter
        range_key = f'{prefix}_range'
        if filters.get(range_key):
            min_val, max_val = filters[range_key]
            result_df = result_df[
                (result_df[column].fillna(0) >= min_val) & 
                (result_df[column].fillna(0) <= max_val)
            ]
        
        return result_df
    
    def _apply_boolean_filters(self, df: pd.DataFrame, filters: Dict[str, Any], boolean_fields: List[str]) -> pd.DataFrame:
        """Apply boolean filters with null handling"""
        result_df = df.copy()
        
        for field in boolean_fields:
            if filters.get(field) is not None and field in result_df.columns:
                result_df = result_df[result_df[field] == filters[field]]
        
        return result_df
    
    def _apply_social_media_filter(self, df: pd.DataFrame, platforms: List[str], mode: str) -> pd.DataFrame:
        """Apply comprehensive social media filters"""
        platform_mapping = {
            'linkedin': 'has_linkedin',
            'twitter': 'has_twitter', 
            'youtube': 'has_youtube',
            'podcast': 'has_podcast'
        }
        
        if mode == 'any':
            mask = pd.Series(False, index=df.index)
            for platform in platforms:
                if platform.lower() in platform_mapping:
                    column = platform_mapping[platform.lower()]
                    if column in df.columns:
                        mask |= df[column] == True
            return df[mask]
        elif mode == 'all':
            mask = pd.Series(True, index=df.index)
            for platform in platforms:
                if platform.lower() in platform_mapping:
                    column = platform_mapping[platform.lower()]
                    if column in df.columns:
                        mask &= df[column] == True
            return df[mask]
        return df
    
    def _apply_gender_filter(self, df: pd.DataFrame, gender: str) -> pd.DataFrame:
        """Apply gender filter with case insensitive matching"""
        if 'gender' in df.columns:
            return df[df['gender'].str.upper() == gender.upper()]
        return df
    
    def _apply_name_filter(self, df: pd.DataFrame, name_parts: List[str]) -> pd.DataFrame:
        """Apply name contains filter"""
        if 'name' not in df.columns:
            return df
        
        mask = pd.Series(True, index=df.index)
        for name_part in name_parts:
            mask &= df['name'].str.contains(name_part, case=False, na=False)
        return df[mask]
    
    def _apply_email_domain_filter(self, df: pd.DataFrame, domains: List[str]) -> pd.DataFrame:
        """Apply email domain filter"""
        if 'email' not in df.columns:
            return df
        
        domain_pattern = '|'.join([f'@{re.escape(domain)}' for domain in domains])
        return df[df['email'].str.contains(domain_pattern, case=False, na=False, regex=True)]
    
    def _apply_condition_filter(self, df: pd.DataFrame, conditions: List[str], mode: str) -> pd.DataFrame:
        """Apply medical condition filters with comprehensive condition mapping"""
        if 'conditions' not in df.columns:
            return df
        
        expanded_conditions = self._expand_condition_names(conditions)
        
        if mode == 'any':
            mask = df['conditions'].apply(
                lambda x: any(self._fuzzy_match_condition(cond, x) for cond in expanded_conditions) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'all':
            mask = df['conditions'].apply(
                lambda x: all(any(self._fuzzy_match_condition(cond, x) for cond in expanded_conditions) for cond in conditions) if isinstance(x, list) else False
            )
            return df[mask]
        elif mode == 'exclude':
            mask = df['conditions'].apply(
                lambda x: not any(self._fuzzy_match_condition(cond, x) for cond in expanded_conditions) if isinstance(x, list) else True
            )
            return df[mask]
        return df
    
    def _apply_percentile_filter(self, df: pd.DataFrame, column: str, percentile: float) -> pd.DataFrame:
        """Apply percentile filter for top performers"""
        if column not in df.columns:
            return df
        
        threshold = np.percentile(df[column].fillna(0), 100 - percentile)
        return df[df[column].fillna(0) >= threshold]
    
    def _apply_academic_filter(self, df: pd.DataFrame, academic_only: bool) -> pd.DataFrame:
        """Apply academic affiliation filter"""
        if not academic_only:
            return df
        
        academic_keywords = ['university', 'college', 'academic', 'school', 'medical school', 'teaching hospital']
        
        # Check multiple fields for academic indicators
        mask = pd.Series(False, index=df.index)
        
        # Check affiliations
        if 'affiliations' in df.columns:
            mask |= df['affiliations'].apply(
                    lambda x: any(any(keyword in str(item).lower() for keyword in academic_keywords) for item in x) if isinstance(x, list) else False
                )
        
        # Check hospital names
        if 'hospital_names' in df.columns:
            mask |= df['hospital_names'].apply(
                lambda x: any(any(keyword in str(item).lower() for keyword in academic_keywords) for item in x) if isinstance(x, list) else False
            )
        
        # Check system names
        if 'system_names' in df.columns:
            mask |= df['system_names'].apply(
                lambda x: any(any(keyword in str(item).lower() for keyword in academic_keywords) for item in x) if isinstance(x, list) else False
            )
        
        return df[mask]
    
    def _apply_community_filter(self, df: pd.DataFrame, community_only: bool) -> pd.DataFrame:
        """Apply community practice filter"""
        if not community_only:
            return df
        
        if 'org_type' in df.columns:
            return df[df['org_type'].str.contains('Community|Private|Clinic', case=False, na=False)]
        return df
    
    def _apply_rural_states_filter(self, df: pd.DataFrame, rural_only: bool) -> pd.DataFrame:
        """Apply rural states filter"""
        if not rural_only:
            return df
        
        rural_states = ['Wyoming', 'Montana', 'North Dakota', 'South Dakota', 'Alaska', 'Vermont', 
                       'Delaware', 'Rhode Island', 'New Hampshire', 'Maine', 'West Virginia']
        
        mask = df['states'].apply(
                lambda x: any(state in rural_states for state in x) if isinstance(x, list) else False
            )
        return df[mask]
    
    def _apply_text_search_filter(self, df: pd.DataFrame, search_terms: Union[str, List[str]]) -> pd.DataFrame:
        """Apply comprehensive text search with semantic capabilities"""
        if isinstance(search_terms, str):
            search_terms = [search_terms]
        
        # Try semantic search first if available
        if self.semantic_search_enabled and len(search_terms) == 1:
            semantic_results = self._semantic_search(search_terms[0])
            if semantic_results is not None:
                return df.iloc[semantic_results]
        
        # Fallback to keyword search
            search_pattern = '|'.join([re.escape(term.lower()) for term in search_terms])
            
        text_columns = ['name', 'specialties', 'hospital_names', 'system_names', 'conditions']
        if 'affiliations' in df.columns:
            text_columns.append('affiliations')
        
            text_masks = []
            
            for col in text_columns:
            if col in df.columns:
                if col in ['specialties', 'hospital_names', 'system_names', 'affiliations', 'conditions']:
                    mask = df[col].apply(
                            lambda x: any(re.search(search_pattern, str(item), re.IGNORECASE) for item in x) if isinstance(x, list) else False
                        )
                    else:
                    mask = df[col].str.contains(search_pattern, case=False, na=False, regex=True)
                    text_masks.append(mask)
            
            if text_masks:
                combined_mask = text_masks[0]
                for mask in text_masks[1:]:
                    combined_mask |= mask
            return df[combined_mask]
        
        return df
    
    def _semantic_search(self, query: str, top_k: int = 1000) -> Optional[List[int]]:
        """Perform semantic search using TF-IDF similarity"""
        if not self.semantic_search_enabled:
            return None
        
        try:
            # Transform query
            query_vector = self.vectorizer.transform([query.lower()])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()
            
            # Get top matches
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # Filter out very low similarities (threshold = 0.01)
            relevant_indices = [idx for idx in top_indices if similarities[idx] > 0.01]
            
            return relevant_indices[:top_k] if relevant_indices else None
            
        except Exception as e:
            print(f"Warning: Semantic search failed: {e}")
            return None
    
    def _fuzzy_match(self, search_term: str, target_list: List[str]) -> bool:
        if not isinstance(target_list, list):
            return False
        
        search_lower = search_term.lower().strip()
        
        for target in target_list:
            if not isinstance(target, str):
                continue
            
            target_lower = target.lower().strip()
            
            # Exact match
            if search_lower == target_lower:
                return True
            
            # Substring match
            if search_lower in target_lower or target_lower in search_lower:
                return True
            
            # Specialty-specific matching
            if self._specialty_match(search_lower, target_lower):
                return True
        
        return False
    
    def _fuzzy_match_specialty(self, search_term: str, target_list: List[str]) -> bool:
        """Match medical specialties with comprehensive mappings"""
        if not isinstance(target_list, list):
            return False
        
        search_lower = search_term.lower().strip()
        
        for target in target_list:
            if not isinstance(target, str):
                continue
            
            target_lower = target.lower().strip()
            
            if search_lower == target_lower or search_lower in target_lower or target_lower in search_lower:
                return True
            
            if search_lower in self.specialty_mappings:
                for variant in self.specialty_mappings[search_lower]:
                    if variant in target_lower:
                        return True
        
        return False
    
    def _specialty_match(self, search_term: str, target: str) -> bool:
        """Handle specialty-specific matching patterns"""
        specialty_mappings = {
            'neurologist': ['neurology', 'neurological'],
            'rheumatologist': ['rheumatology', 'rheumatic'],
            'dermatologist': ['dermatology', 'dermatologic'],
            'endocrinologist': ['endocrinology', 'endocrine'],
            'cardiologist': ['cardiology', 'cardiac', 'cardiovascular']
        }
        
        for specialty, variants in specialty_mappings.items():
            if specialty in search_term:
                return any(variant in target for variant in variants)
            if any(variant in search_term for variant in variants):
                return specialty in target or any(variant in target for variant in variants)
        
        return False
    
    def _fuzzy_match_hospital(self, search_term: str, target_list: List[str]) -> bool:
        """Match hospital names with comprehensive hospital mappings"""
        if not isinstance(target_list, list):
            return False
        
        search_lower = search_term.lower().strip()
        
        for target in target_list:
            if not isinstance(target, str):
                continue
            
            target_lower = target.lower().strip()
            
            # Exact match
            if search_lower == target_lower:
                return True
            
            # Substring match
            if search_lower in target_lower or target_lower in search_lower:
                return True
            
            # Hospital-specific matching
            if search_lower in self.hospital_mappings:
                for variant in self.hospital_mappings[search_lower]:
                    if variant.lower() in target_lower:
                        return True
        
        return False
    
    def _fuzzy_match_condition(self, search_term: str, target_list: List[str]) -> bool:
        """Match medical conditions with comprehensive condition mappings"""
        if not isinstance(target_list, list):
            return False
        
        search_lower = search_term.lower().strip()
        
        for target in target_list:
            if not isinstance(target, str):
                continue
            
            target_lower = target.lower().strip()
            
            # Exact match
            if search_lower == target_lower:
                return True
            
            # Substring match
            if search_lower in target_lower or target_lower in search_lower:
                return True
            
            # Condition-specific matching
            if search_lower in self.condition_mappings:
                for variant in self.condition_mappings[search_lower]:
                    if variant.lower() in target_lower:
                        return True
        
        return False
    
    def _expand_condition_names(self, conditions: List[str]) -> List[str]:
        """Expand condition names to include all variants and aliases"""
        expanded = set()
        for condition in conditions:
            condition_lower = condition.lower().strip()
            expanded.add(condition_lower)
            if condition_lower in self.condition_mappings:
                expanded.update([alias.lower() for alias in self.condition_mappings[condition_lower]])
        return list(expanded)
    
    def _expand_state_names(self, states: List[str]) -> List[str]:
        """Expand state abbreviations to full names"""
        state_mappings = {
            'CA': 'California', 'NY': 'New York', 'TX': 'Texas', 'FL': 'Florida',
            'IL': 'Illinois', 'PA': 'Pennsylvania', 'OH': 'Ohio', 'GA': 'Georgia',
            'NC': 'North Carolina', 'MI': 'Michigan', 'NJ': 'New Jersey', 'VA': 'Virginia',
            'WA': 'Washington', 'AZ': 'Arizona', 'MA': 'Massachusetts', 'TN': 'Tennessee',
            'IN': 'Indiana', 'MO': 'Missouri', 'MD': 'Maryland', 'WI': 'Wisconsin'
        }
        
        expanded = set()
        for state in states:
            state_upper = state.upper().strip()
            state_title = state.title().strip()
            
            expanded.add(state)
            expanded.add(state_upper)
            expanded.add(state_title)
            
            if state_upper in state_mappings:
                expanded.add(state_mappings[state_upper])
        
        return list(expanded)
    
    def _join_with_claims(self, hcp_df: pd.DataFrame, claims_filters: Dict[str, Any]) -> pd.DataFrame:
        """Join HCP data with Claims data based on filters"""
        
        # Filter claims data
        filtered_claims = self._filter_claims(claims_filters)
        
        if filtered_claims.empty:
            # No matching claims found
            if claims_filters.get('negate', False):
                # For negation, return all HCP data (no one prescribed the drug)
                return hcp_df
            else:
                # For regular queries, return empty result
                return hcp_df.iloc[0:0]
        
        # Aggregate claims by prescriber
        claims_stats = self._aggregate_claims(filtered_claims)
        
        # Apply prescription count filters
        if claims_filters.get('prescription_count_min'):
            claims_stats = claims_stats[claims_stats['total_prescriptions'] >= claims_filters['prescription_count_min']]
        
        if claims_filters.get('negate', False):
            # Anti-join: return doctors who did NOT prescribe
            prescribing_npis = claims_stats['PRESCRIBER_NPI_NBR'].tolist()
            result_df = hcp_df[~hcp_df['npi'].isin(prescribing_npis)]
        else:
            # Inner join: return doctors who did prescribe with stats
            result_df = hcp_df.merge(
                claims_stats,
                left_on='npi',
                right_on='PRESCRIBER_NPI_NBR',
                how='inner'
            )
            # Drop duplicate NPI column
            if 'PRESCRIBER_NPI_NBR' in result_df.columns:
                result_df = result_df.drop('PRESCRIBER_NPI_NBR', axis=1)
        
        return result_df
    
    def _filter_claims(self, claims_filters: Dict[str, Any]) -> pd.DataFrame:
        """Filter claims data with comprehensive criteria and edge case handling"""
        filtered_df = self.claims_df.copy()
        
        # Handle dispensed vs rejected prescriptions
        if claims_filters.get('dispensed_only', True) and 'FINAL_STATUS_CD' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['FINAL_STATUS_CD'] == 'Y']
        elif claims_filters.get('include_rejected', False) and 'FINAL_STATUS_CD' in filtered_df.columns:
            # Include both dispensed and rejected
            pass
        
        # Comprehensive date filtering
        filtered_df = self._apply_date_filters(filtered_df, claims_filters)
        
        # Drug filtering with comprehensive mappings
        filtered_df = self._apply_drug_filters(filtered_df, claims_filters)
        
        # Payer/insurance filtering
        filtered_df = self._apply_payer_filters(filtered_df, claims_filters)
        
        # Cost and quantity filtering
        filtered_df = self._apply_cost_filters(filtered_df, claims_filters)
        
        # Pharmacy filtering
        filtered_df = self._apply_pharmacy_filters(filtered_df, claims_filters)
        
        return filtered_df
    
    def _apply_date_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply comprehensive date filtering with multiple date range options"""
        result_df = df.copy()
        
        # Date range in months (relative)
        if filters.get('date_range_months'):
            end_date = datetime.now()
            start_date = end_date - relativedelta(months=filters['date_range_months'])
            result_df = self._filter_by_date_range(result_df, start_date, end_date)
        
        # Specific date range
        if filters.get('date_range_start') and filters.get('date_range_end'):
            start_date = pd.to_datetime(filters['date_range_start'])
            end_date = pd.to_datetime(filters['date_range_end'])
            result_df = self._filter_by_date_range(result_df, start_date, end_date)
        
        # Year filter
        if filters.get('year'):
            year = filters['year']
            if 'SERVICE_DATE_DD' in result_df.columns:
                result_df = result_df[result_df['SERVICE_DATE_DD'].dt.year == year]
        
        # Quarter filter
        if filters.get('quarter'):
            quarter = filters['quarter']
            if 'SERVICE_DATE_DD' in result_df.columns:
                result_df = result_df[result_df['SERVICE_DATE_DD'].dt.quarter == quarter]
        
        # Month filter
        if filters.get('month'):
            month = filters['month']
            if 'SERVICE_DATE_DD' in result_df.columns:
                result_df = result_df[result_df['SERVICE_DATE_DD'].dt.month == month]
        
        # Weekday filter (0=Monday, 6=Sunday)
        if filters.get('weekday') is not None:
            weekday = filters['weekday']
            if 'SERVICE_DATE_DD' in result_df.columns:
                result_df = result_df[result_df['SERVICE_DATE_DD'].dt.weekday == weekday]
        
        return result_df
    
    def _filter_by_date_range(self, df: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Filter by date range using the best available date column"""
        date_columns = ['SERVICE_DATE_DD', 'DATE_PRESCRIPTION_WRITTEN_DD', 'TRANSACTION_DT']
        
        for date_col in date_columns:
            if date_col in df.columns:
                return df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]
        
        return df
    
    def _apply_drug_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply comprehensive drug filtering with drug classes and groups"""
        result_df = df.copy()
        
        # Drugs any (OR logic)
        if filters.get('drugs_any'):
            expanded_drugs = self._expand_drug_names(filters['drugs_any'])
            result_df = self._filter_by_drugs(result_df, expanded_drugs, 'any')
        
        # Drugs all (AND logic)
        if filters.get('drugs_all'):
            expanded_drugs = self._expand_drug_names(filters['drugs_all'])
            result_df = self._filter_by_drugs(result_df, expanded_drugs, 'all')
        
        # Exclude specific drugs
        if filters.get('drugs_exclude'):
            expanded_drugs = self._expand_drug_names(filters['drugs_exclude'])
            result_df = self._filter_by_drugs(result_df, expanded_drugs, 'exclude')
        
        # Drug classes
        if filters.get('drug_classes_any'):
            class_drugs = []
            for drug_class in filters['drug_classes_any']:
                if drug_class.lower() in self.drug_mappings:
                    class_drugs.extend(self.drug_mappings[drug_class.lower()])
            if class_drugs:
                result_df = self._filter_by_drugs(result_df, class_drugs, 'any')
        
        # Drug groups (broader categories)
        if filters.get('drug_groups_any'):
            group_drugs = []
            for drug_group in filters['drug_groups_any']:
                if drug_group.lower() in self.drug_mappings:
                    group_drugs.extend(self.drug_mappings[drug_group.lower()])
            if group_drugs:
                result_df = self._filter_by_drugs(result_df, group_drugs, 'any')
        
        return result_df
    
    def _filter_by_drugs(self, df: pd.DataFrame, drug_names: List[str], mode: str) -> pd.DataFrame:
        """Filter claims by drug names with flexible matching"""
        if not drug_names or 'all_drug_names' not in df.columns:
            return df
        
        drug_pattern = '|'.join([re.escape(drug.lower()) for drug in drug_names])
        
        if mode == 'any':
            mask = df['all_drug_names'].str.contains(drug_pattern, case=False, na=False, regex=True)
            return df[mask]
        elif mode == 'exclude':
            mask = ~df['all_drug_names'].str.contains(drug_pattern, case=False, na=False, regex=True)
            return df[mask]
        elif mode == 'all':
            # For ALL logic, check each drug individually
            mask = pd.Series(True, index=df.index)
            for drug in drug_names:
                drug_mask = df['all_drug_names'].str.contains(re.escape(drug.lower()), case=False, na=False, regex=True)
                mask &= drug_mask
            return df[mask]
        
        return df
    
    def _apply_payer_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply payer/insurance type filtering"""
        result_df = df.copy()
        
        if filters.get('payer_types'):
            payer_patterns = []
            for payer_type in filters['payer_types']:
                if payer_type.lower() in self.payer_mappings:
                    payer_patterns.extend(self.payer_mappings[payer_type.lower()])
                else:
                    payer_patterns.append(payer_type)
            
            if payer_patterns and 'PAYER_PAYER_NM' in result_df.columns:
                payer_pattern = '|'.join([re.escape(p.lower()) for p in payer_patterns])
                mask = result_df['PAYER_PAYER_NM'].str.contains(payer_pattern, case=False, na=False, regex=True)
                result_df = result_df[mask]
        
        return result_df
    
    def _apply_cost_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply comprehensive cost and quantity filtering"""
        result_df = df.copy()
        
        # Cost filters
        cost_fields = {
            'total_cost': 'TOTAL_PAID_AMT',
            'cost': 'GROSS_DUE_AMT', 
            'patient_pay': 'PATIENT_TO_PAY_AMT'
        }
        
        for field_prefix, column in cost_fields.items():
            if column in result_df.columns:
                result_df = self._apply_numeric_range_filter(result_df, filters, field_prefix, column)
        
        # Quantity filters
        if 'DISPENSED_QUANTITY_VAL' in result_df.columns:
            result_df = self._apply_numeric_range_filter(result_df, filters, 'quantity', 'DISPENSED_QUANTITY_VAL')
        
        # Days supply filters
        if 'DAYS_SUPPLY_VAL' in result_df.columns:
            result_df = self._apply_numeric_range_filter(result_df, filters, 'days_supply', 'DAYS_SUPPLY_VAL')
        
        return result_df
    
    def _apply_numeric_range_filter(self, df: pd.DataFrame, filters: Dict[str, Any], prefix: str, column: str) -> pd.DataFrame:
        """Apply numeric range filtering for any numeric field"""
        result_df = df.copy()
        
        min_key = f'{prefix}_min'
        max_key = f'{prefix}_max'
        
        if filters.get(min_key) is not None:
            result_df = result_df[result_df[column].fillna(0) >= filters[min_key]]
        
        if filters.get(max_key) is not None:
            result_df = result_df[result_df[column].fillna(0) <= filters[max_key]]
        
        return result_df
    
    def _apply_pharmacy_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        """Apply pharmacy-related filtering"""
        result_df = df.copy()
        
        # Pharmacy type
        if filters.get('pharmacy_type') and 'PHARMACY_NPI_NM' in result_df.columns:
            pharmacy_type = filters['pharmacy_type']
            mask = result_df['PHARMACY_NPI_NM'].str.contains(pharmacy_type, case=False, na=False)
            result_df = result_df[mask]
        
        # Pharmacy state
        if filters.get('state_pharmacy') and 'PHARMACY_NPI_STATE_CD' in result_df.columns:
            state = filters['state_pharmacy']
            expanded_states = self._expand_state_names([state])
            state_pattern = '|'.join(expanded_states)
            mask = result_df['PHARMACY_NPI_STATE_CD'].str.contains(state_pattern, case=False, na=False, regex=True)
            result_df = result_df[mask]
        
        return result_df
    
    def _expand_drug_names(self, drug_names: List[str]) -> List[str]:
        """Expand drug names to include aliases"""
        expanded = set()
        for drug in drug_names:
            drug_lower = drug.lower().strip()
            expanded.add(drug_lower)
            if drug_lower in self.drug_mappings:
                expanded.update([alias.lower() for alias in self.drug_mappings[drug_lower]])
        return list(expanded)
    
    def _aggregate_claims(self, filtered_claims: pd.DataFrame) -> pd.DataFrame:
        """Aggregate claims data by prescriber"""
        if filtered_claims.empty:
            return pd.DataFrame(columns=['PRESCRIBER_NPI_NBR'])
        
        agg_dict = {
            'total_prescriptions': ('PRESCRIBER_NPI_NBR', 'count'),
        }
        
        if 'PATIENT_ID' in filtered_claims.columns:
            agg_dict['unique_patients'] = ('PATIENT_ID', 'nunique')
        
        if 'SERVICE_DATE_DD' in filtered_claims.columns:
            agg_dict['last_prescription_date'] = ('SERVICE_DATE_DD', 'max')
        
        result = filtered_claims.groupby('PRESCRIBER_NPI_NBR').agg(**agg_dict).reset_index()
        return result
    
    def _apply_aggregation(self, df: pd.DataFrame, aggregation: Dict[str, Any]) -> pd.DataFrame:
        """Apply custom aggregation logic to results"""
        if not aggregation or not aggregation.get('group_by'):
            return df
        
        group_by = [col for col in aggregation['group_by'] if col in df.columns]
        if not group_by:
            return df
        
        agg_dict = {}
        if aggregation.get('count_doctors'):
            agg_dict['doctor_count'] = ('npi', 'nunique')
        if aggregation.get('avg_publications'):
            agg_dict['avg_publications'] = ('num_publications', 'mean')
        if aggregation.get('avg_trials'):
            agg_dict['avg_clinical_trials'] = ('num_clinical_trials', 'mean')
        
        if not agg_dict:
            return df
        
        result = df.groupby(group_by).agg(**agg_dict).reset_index()
        return result.round(2)
    
    def _apply_analytics(self, df: pd.DataFrame, analytics: Dict[str, Any]) -> pd.DataFrame:
        """Apply advanced analytics and calculations"""
        result_df = df.copy()
        
        if analytics.get('calculate_rankings'):
            if 'num_publications' in result_df.columns:
                result_df['publication_rank'] = result_df['num_publications'].rank(ascending=False)
            if 'num_clinical_trials' in result_df.columns:
                result_df['trial_rank'] = result_df['num_clinical_trials'].rank(ascending=False)
        
        if analytics.get('calculate_scores'):
            score_components = []
            if 'num_publications' in result_df.columns:
                pub_score = (result_df['num_publications'] / result_df['num_publications'].max()).fillna(0) * 0.5
                score_components.append(pub_score)
            if 'num_clinical_trials' in result_df.columns:
                trial_score = (result_df['num_clinical_trials'] / result_df['num_clinical_trials'].max()).fillna(0) * 0.5
                score_components.append(trial_score)
            
            if score_components:
                result_df['composite_score'] = sum(score_components)
        
        if analytics.get('add_categories'):
            if 'num_publications' in result_df.columns:
                result_df['publication_category'] = pd.cut(
                    result_df['num_publications'], 
                    bins=[-1, 0, 10, 50, float('inf')], 
                    labels=['None', 'Low', 'Medium', 'High']
                )
        
        return result_df
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """Get comprehensive summary statistics of the data"""
        return {
            'hcp_data': {
                'total_providers': len(self.hcp_df),
                'avg_publications': self.hcp_df['num_publications'].mean(),
                'avg_trials': self.hcp_df['num_clinical_trials'].mean()
            },
            'claims_data': {
                'total_claims': len(self.claims_df),
                'unique_prescribers': self.claims_df['PRESCRIBER_NPI_NBR'].nunique() if 'PRESCRIBER_NPI_NBR' in self.claims_df.columns else 0
            }
        }
    
    def validate_plan(self, plan: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate query plan for completeness and correctness"""
        try:
            required_fields = ['filters', 'projection', 'limit']
            missing_fields = [field for field in required_fields if field not in plan]
            
            if missing_fields:
                return False, f"Missing required fields: {missing_fields}"
            
            if not isinstance(plan['limit'], int) or plan['limit'] <= 0:
                return False, "Limit must be a positive integer"
            
            return True, "Plan is valid"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _apply_projection(self, df: pd.DataFrame, projection: List[str]) -> pd.DataFrame:
        available_columns = []
        for col in projection:
            if col in df.columns:
                available_columns.append(col)
        return df[available_columns]
    
    def _apply_ordering(self, df: pd.DataFrame, order_by: List[str]) -> pd.DataFrame:
        sort_columns = []
        sort_ascending = []
        
        for order_spec in order_by:
            parts = order_spec.split()
            column = parts[0]
            direction = parts[1].upper() if len(parts) > 1 else 'ASC'
            
            if column in df.columns:
                sort_columns.append(column)
                sort_ascending.append(direction == 'ASC')
        
        if sort_columns:
            return df.sort_values(by=sort_columns, ascending=sort_ascending)
        return df

def execute_json_plan(json_plan: str, csv_path: str = "data/providers.csv") -> pd.DataFrame:
    plan = json.loads(json_plan)
    executor = PlanExecutor(csv_path)
    return executor.execute_plan(plan)

if __name__ == "__main__":
    sample_plan = """{
        "filters": {
            "specialty_any": null,
            "state_any": null,
            "hospital_any": null,
            "system_any": null,
            "org_type_any": null,
            "publications_min": 30
        },
        "projection": [
            "npi",
            "name",
            "num_publications"
        ],
        "order_by": [
            "num_publications DESC",
            "name ASC"
        ],
        "limit": 20,
        "plan_notes": null
    }"""
    
    result = execute_json_plan(sample_plan)
    print(result.to_string(index=False))
