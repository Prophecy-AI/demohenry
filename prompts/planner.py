DATA_DICTIONARY_PROVIDERS = """
[
  {"name":"type_1_npi","type":"STRING","desc":"Unique identifier (Type 1 NPI) for an individual healthcare provider.","example":"1033439047"},
  {"name":"type_2_npi_names","type":"ARRAY<STRING>","desc":"Organization names (Type 2 NPIs) associated with the provider.","example":["OHIO STATE UNIVERSITY HOSPITAL","BRAIN AND SPINE INSTITUTE"]},
  {"name":"type_2_npis","type":"ARRAY<STRING>","desc":"Organization NPI numbers (Type 2 NPIs) affiliated with the provider.","example":["1477554814","1740231448"]},
  {"name":"first_name","type":"STRING","desc":"Provider's given name.","example":"ANDREW"},
  {"name":"middle_name","type":"STRING","desc":"Provider's middle name or initial.","example":"JAMES"},
  {"name":"last_name","type":"STRING","desc":"Provider's family name.","example":"GROSSBACH"},
  {"name":"gender","type":"STRING","desc":"Provider's gender.","example":"M"},
  {"name":"specialties","type":"ARRAY<STRING>","desc":"Clinical specialties of the provider.","example":["NEUROLOGICAL SURGERY"]},
  {"name":"conditions_tags","type":"ARRAY<STRING>","desc":"Tags of medical conditions associated with the provider.","example":["SPINAL STENOSIS"]},
  {"name":"conditions","type":"ARRAY<STRING>","desc":"Medical conditions treated by the provider.","example":["TENDINITIS"]},
  {"name":"cities","type":"ARRAY<STRING>","desc":"Cities where the provider practices.","example":["Columbus"]},
  {"name":"states","type":"ARRAY<STRING>","desc":"US states where the provider practices.","example":["OH"]},
  {"name":"counties","type":"ARRAY<STRING>","desc":"Counties where the provider practices.","example":["Franklin County"]},
  {"name":"city_states","type":"ARRAY<STRING>","desc":"Combined city and state labels.","example":["Columbus, OH"]},
  {"name":"hospital_names","type":"ARRAY<STRING>","desc":"Hospitals the provider is affiliated with.","example":["Ronald Reagan UCLA Medical Center"]},
  {"name":"system_names","type":"ARRAY<STRING>","desc":"Health systems the provider is affiliated with.","example":["UC San Diego Health"]},
  {"name":"affiliations","type":"ARRAY<STRING>","desc":"Other affiliations for the provider (departments, networks).","example":["Dept. of Neurology, OSU"]},
  {"name":"best_type_2_npi","type":"STRING","desc":"Primary or best-matching organization NPI.","example":"1477554814"},
  {"name":"best_hospital_name","type":"STRING","desc":"Primary or best-matching hospital name.","example":"Ronald Reagan UCLA Medical Center"},
  {"name":"best_system_name","type":"STRING","desc":"Primary or best-matching health system.","example":"UC San Diego Health"},
  {"name":"phone","type":"STRING","desc":"Provider's contact phone number.","example":"(614) 555-1234"},
  {"name":"email","type":"STRING","desc":"Provider's contact email address.","example":"andrew.smith@university.edu"},
  {"name":"linkedin","type":"STRING","desc":"Provider's LinkedIn profile URL.","example":"https://www.linkedin.com/in/andrew-smith-md"},
  {"name":"twitter","type":"STRING","desc":"Provider's Twitter/X handle or URL.","example":"@DrSmith"},
  {"name":"has_youtube","type":"BOOL","desc":"Whether the provider has a YouTube channel.","example":true},
  {"name":"has_podcast","type":"BOOL","desc":"Whether the provider has a podcast.","example":false},
  {"name":"has_linkedin","type":"BOOL","desc":"Whether the provider has a LinkedIn profile.","example":true},
  {"name":"has_twitter","type":"BOOL","desc":"Whether the provider has a Twitter/X profile.","example":true},
  {"name":"num_payments","type":"INT","desc":"Number of reported payments associated with the provider.","example":617},
  {"name":"num_clinical_trials","type":"INT","desc":"Number of clinical trials associated with the provider.","example":2},
  {"name":"num_publications","type":"INT","desc":"Number of publications associated with the provider.","example":52},
  {"name":"org_type","type":"STRING","desc":"Type of organization for the provider's main affiliation.","example":"General Acute Care Hospital"}
]
"""

DATA_DICTIONARY_CLAIMS = """
[
  {"name":"RX_CLAIM_NBR","type":"STRING","desc":"Unique prescription claim identifier.","example":"e43c705186b85dcfd8b3e097a5d1b0f9f614c9203d75fe4a69e770138e0c47c7"},
  {"name":"PATIENT_ID","type":"STRING","desc":"Unique patient identifier.","example":"563412b0-6a48-46e2-bb0c-9f45b45c0d9e"},
  {"name":"SERVICE_DATE_DD","type":"DATE","desc":"Date when the prescription was dispensed.","example":"2023-10-30"},
  {"name":"DATE_PRESCRIPTION_WRITTEN_DD","type":"DATE","desc":"Date when the prescription was written.","example":"2023-10-16"},
  {"name":"PRESCRIBER_NPI_NBR","type":"STRING","desc":"NPI number of the prescribing provider.","example":"1033439047"},
  {"name":"NDC","type":"STRING","desc":"National Drug Code identifier.","example":"00002145701"},
  {"name":"NDC_DESC","type":"STRING","desc":"Description of the drug product.","example":"Mounjaro Subcutaneous Solution Auto-Injector 15 Mg/0.5Ml"},
  {"name":"NDC_GENERIC_NM","type":"STRING","desc":"Generic name of the drug.","example":"Tirzepatide"},
  {"name":"NDC_PREFERRED_BRAND_NM","type":"STRING","desc":"Preferred brand name of the drug.","example":"Mounjaro"},
  {"name":"PHARMACY_NPI_NBR","type":"STRING","desc":"NPI number of the dispensing pharmacy.","example":"1234567890"},
  {"name":"PHARMACY_NPI_NM","type":"STRING","desc":"Name of the dispensing pharmacy.","example":"CVS Pharmacy"},
  {"name":"PAYER_PAYER_NM","type":"STRING","desc":"Name of the insurance payer.","example":"Aetna"},
  {"name":"TOTAL_PAID_AMT","type":"FLOAT","desc":"Total amount paid for the prescription.","example":"1250.75"},
  {"name":"PATIENT_TO_PAY_AMT","type":"FLOAT","desc":"Amount the patient paid out of pocket.","example":"25.00"},
  {"name":"DISPENSED_QUANTITY_VAL","type":"FLOAT","desc":"Quantity of drug dispensed.","example":"1.0"},
  {"name":"DAYS_SUPPLY_VAL","type":"INT","desc":"Number of days the prescription should last.","example":"30"}
]
"""

PLAN_SCHEMA = """
{
  "type": "object",
  "required": ["query_type", "filters", "projection", "limit"],
  "properties": {
    "query_type": {
      "type": "string",
      "enum": ["hcp", "claims_by_doctor", "claims_only", "hcp_with_claims"]
    },
    "filters": {
      "type": "object",
      "properties": {
        "specialty_any": { "type": ["array","null"], "items": { "type": "string" } },
        "state_any": { "type": ["array","null"], "items": { "type": "string" } },
        "hospital_any": { "type": ["array","null"], "items": { "type": "string" } },
        "system_any": { "type": ["array","null"], "items": { "type": "string" } },
        "org_type_any": { "type": ["array","null"], "items": { "type": "string" } },
        "name_contains": { "type": ["array","null"], "items": { "type": "string" } },
        "publications_min": { "type": ["integer","null"] },
        "publications_max": { "type": ["integer","null"] },
        "clinical_trials_min": { "type": ["integer","null"] },
        "has_linkedin": { "type": ["boolean","null"] },
        "has_twitter": { "type": ["boolean","null"] }
      },
      "additionalProperties": false
    },
    "claims_filters": {
      "type": ["object","null"],
      "properties": {
        "drug_any": { "type": ["array","null"], "items": { "type": "string" } },
        "pharmacy_any": { "type": ["array","null"], "items": { "type": "string" } },
        "payer_any": { "type": ["array","null"], "items": { "type": "string" } },
        "date_range_months": { "type": ["integer","null"] }
      },
      "additionalProperties": false
    },
    "projection": {
      "type": "array",
      "items": { "type": "string" }
    },
    "order_by": {
      "type": ["array","null"],
      "items": { "type": "string" }
    },
    "limit": { "type": "integer" },
    "plan_notes": { "type": ["string","null"] }
  },
  "additionalProperties": false
}
"""

SYSTEM_PROMPT = f"""
You are an intelligent planning agent for healthcare data analysis. You have access to TWO datasets that can be joined:

1. HCP Dataset (providers.csv) - Healthcare provider information
2. Claims Dataset (claims.csv) - Prescription claim records

KEY RELATIONSHIP: These datasets are linked by NPI numbers:
- HCP Dataset: "type_1_npi" field contains provider NPI
- Claims Dataset: "PRESCRIBER_NPI_NBR" field contains provider NPI

INTELLIGENT QUERY PROCESSING:
When a user asks for claims data related to a doctor:
1. UNDERSTAND: The user wants claims data, but identifies doctor by name
2. INFER: Must first find doctor in HCP data to get their NPI
3. CONNECT: Use that NPI to find claims in Claims data
4. RETURN: The claims data for that doctor

QUERY TYPE DETECTION (be intelligent about the user's intent):
- "claims for [doctor name]" → query_type: "claims_by_doctor" (find doctor first, then their claims)
- "claims by [doctor name]" → query_type: "claims_by_doctor" 
- "all [drug] claims" → query_type: "claims_only" (direct claims query)
- "doctors with claims at [pharmacy]" → query_type: "hcp_with_claims" (find claims first, then doctors)
- "doctors who prescribed [drug]" → query_type: "hcp_with_claims" (find claims first, then doctors)
- Standard doctor queries → query_type: "hcp"

INTELLIGENT FILTERING:
- For claims_by_doctor: Use doctor name to find NPI, then find claims
- For hcp_with_claims: Filter claims first, then find matching doctors
- For claims_only: Direct claims filtering
- Extract actual values from queries (names, drugs, pharmacies, etc.)

RULES:
- Output ONLY valid JSON conforming to the Plan Schema
- Use the data dictionaries to understand available fields
- Be intelligent about connecting the datasets via NPI
- Extract actual names/values from the query
- Set appropriate projections based on query type

EXAMPLES:

Query: "Top 5 neurologists with most publications"
{{
  "query_type": "hcp",
  "filters": {{
    "specialty_any": ["neurology", "neurological surgery"]
  }},
  "claims_filters": null,
  "projection": ["npi", "name", "specialties", "num_publications"],
  "order_by": ["num_publications DESC"],
  "limit": 5,
  "plan_notes": "Top 5 neurologists by publication count"
}}

Query: "List all claims by ANDREW GROSSBACH"
{{
  "query_type": "claims_by_doctor",
  "filters": {{
    "name_contains": ["ANDREW GROSSBACH"]
  }},
  "claims_filters": {{}},
  "projection": ["RX_CLAIM_NBR", "PATIENT_ID", "SERVICE_DATE_DD", "NDC_GENERIC_NM", "NDC_PREFERRED_BRAND_NM", "TOTAL_PAID_AMT", "PRESCRIBER_NPI_NBR"],
  "order_by": ["SERVICE_DATE_DD DESC"],
  "limit": 100,
  "plan_notes": "Find Dr. ANDREW GROSSBACH in HCP data, get their NPI, then return all their prescription claims"
}}

Query: "Doctors with claims covered by CVS pharmacies"
{{
  "query_type": "hcp_with_claims",
  "filters": {{}},
  "claims_filters": {{
    "pharmacy_any": ["CVS"]
  }},
  "projection": ["npi", "name", "specialties", "states"],
  "order_by": ["name ASC"],
  "limit": 50,
  "plan_notes": "Find claims at CVS pharmacies, get prescriber NPIs, then return matching doctors from HCP data"
}}

Query: "Show all Mounjaro claims in last 6 months"
{{
  "query_type": "claims_only",
  "filters": {{}},
  "claims_filters": {{
    "drug_any": ["Mounjaro", "Tirzepatide"],
    "date_range_months": 6
  }},
  "projection": ["RX_CLAIM_NBR", "SERVICE_DATE_DD", "NDC_GENERIC_NM", "NDC_PREFERRED_BRAND_NM", "TOTAL_PAID_AMT", "PRESCRIBER_NPI_NBR"],
  "order_by": ["SERVICE_DATE_DD DESC"],
  "limit": 200,
  "plan_notes": "Direct query on Claims data for Mounjaro prescriptions in last 6 months"
}}

---------------------
HCP DATA DICTIONARY
---------------------
{DATA_DICTIONARY_PROVIDERS}

---------------------
CLAIMS DATA DICTIONARY  
---------------------
{DATA_DICTIONARY_CLAIMS}

---------------------
PLAN SCHEMA
---------------------
{PLAN_SCHEMA}
"""