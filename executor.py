import pandas as pd
import json
import ast
from typing import Dict, List, Any, Optional

class PlanExecutor:
    def __init__(self, csv_path: str = "data/providers.csv", claims_path: str = "data/Mounjaro Claim Sample.csv"):
        self.hcp_df = pd.read_csv(csv_path)
        self.claims_df = pd.read_csv(claims_path)
        self._preprocess_data()
    
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
            
            if 'PRESCRIBER_NPI_NBR' in self.claims_df.columns:
                self.claims_df['PRESCRIBER_NPI_NBR'] = self.claims_df['PRESCRIBER_NPI_NBR'].fillna(0).astype(float).astype(int).astype(str)
                self.claims_df = self.claims_df[self.claims_df['PRESCRIBER_NPI_NBR'] != '0']
    
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
        query_type = plan.get('query_type', 'hcp')
        
        if query_type == 'claims_by_doctor':
            return self._execute_claims_by_doctor(plan)
        elif query_type == 'claims_only':
            return self._execute_claims_only(plan)
        elif query_type == 'hcp_with_claims':
            return self._execute_hcp_with_claims(plan)
        else:
            result_df = self.hcp_df.copy()
            
            if plan.get('filters'):
                result_df = self._apply_filters(result_df, plan['filters'])
            
            if plan.get('projection'):
                result_df = self._apply_projection(result_df, plan['projection'])
            
            if plan.get('order_by'):
                result_df = self._apply_ordering(result_df, plan['order_by'])
            
            if plan.get('limit'):
                result_df = result_df.head(plan['limit'])
            
            return result_df
    
    def _execute_claims_by_doctor(self, plan: Dict[str, Any]) -> pd.DataFrame:
        print(f"🔍 Looking for doctor with filters: {plan.get('filters')}")
        
        hcp_df = self.hcp_df.copy()
        
        if plan.get('filters'):
            hcp_df = self._apply_filters(hcp_df, plan['filters'])
        
        print(f"📋 Found {len(hcp_df)} matching doctors in HCP data")
        
        if hcp_df.empty:
            print("❌ No doctors found matching the criteria")
            return pd.DataFrame()
        
        if len(hcp_df) <= 5:
            for _, doctor in hcp_df.iterrows():
                print(f"   - {doctor['name']} (NPI: {doctor['npi']})")
        
        doctor_npis = hcp_df['npi'].tolist()
        print(f"🔗 Looking for claims with NPIs: {doctor_npis}")
        
        result_df = self.claims_df.copy()
        if 'PRESCRIBER_NPI_NBR' in result_df.columns:
            result_df = result_df[result_df['PRESCRIBER_NPI_NBR'].isin(doctor_npis)]
        
        print(f"💊 Found {len(result_df)} claims for these doctors")
        
        if plan.get('claims_filters'):
            result_df = self._apply_claims_filters(result_df, plan['claims_filters'])
            print(f"🔍 After claims filtering: {len(result_df)} claims")
        
        if plan.get('projection'):
            result_df = self._apply_projection(result_df, plan['projection'])
        if plan.get('order_by'):
            result_df = self._apply_ordering(result_df, plan['order_by'])
        if plan.get('limit'):
            result_df = result_df.head(plan['limit'])
        
        return result_df
    
    def _execute_claims_only(self, plan: Dict[str, Any]) -> pd.DataFrame:
        """Execute claims-only query"""
        result_df = self.claims_df.copy()
        
        if plan.get('claims_filters'):
            result_df = self._apply_claims_filters(result_df, plan['claims_filters'])
        
        if plan.get('projection'):
            result_df = self._apply_projection(result_df, plan['projection'])
        if plan.get('order_by'):
            result_df = self._apply_ordering(result_df, plan['order_by'])
        if plan.get('limit'):
            result_df = result_df.head(plan['limit'])
        
        return result_df
    
    def _execute_hcp_with_claims(self, plan: Dict[str, Any]) -> pd.DataFrame:
        """Intelligently find claims first, then return matching doctors"""
        print(f"🔍 Looking for claims with filters: {plan.get('claims_filters')}")
        
        claims_df = self.claims_df.copy()
        if plan.get('claims_filters'):
            claims_df = self._apply_claims_filters(claims_df, plan['claims_filters'])
        
        print(f"💊 Found {len(claims_df)} matching claims")
        
        if claims_df.empty:
            print("❌ No claims found matching the criteria")
            return pd.DataFrame()
        
        if 'PRESCRIBER_NPI_NBR' in claims_df.columns:
            prescriber_npis = claims_df['PRESCRIBER_NPI_NBR'].unique()
            print(f"🔗 Found {len(prescriber_npis)} unique prescriber NPIs")
        else:
            print("❌ No prescriber NPI column in claims data")
            return pd.DataFrame()
        
        result_df = self.hcp_df.copy()
        result_df = result_df[result_df['npi'].isin(prescriber_npis)]
        print(f"👨‍⚕️ Found {len(result_df)} doctors with matching claims")
        
        if plan.get('filters'):
            result_df = self._apply_filters(result_df, plan['filters'])
            print(f"🔍 After HCP filtering: {len(result_df)} doctors")
        
        if plan.get('projection'):
            result_df = self._apply_projection(result_df, plan['projection'])
        if plan.get('order_by'):
            result_df = self._apply_ordering(result_df, plan['order_by'])
        if plan.get('limit'):
            result_df = result_df.head(plan['limit'])
        
        return result_df
    
    def _apply_claims_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        result_df = df.copy()
        
        if filters.get('pharmacy_any'):
            if 'PHARMACY_NPI_NM' in result_df.columns:
                mask = result_df['PHARMACY_NPI_NM'].apply(
                    lambda x: any(pharm.lower() in str(x).lower() for pharm in filters['pharmacy_any']) if pd.notna(x) else False
                )
                result_df = result_df[mask]
        
        if filters.get('payer_any'):
            if 'PAYER_PAYER_NM' in result_df.columns:
                mask = result_df['PAYER_PAYER_NM'].apply(
                    lambda x: any(payer.lower() in str(x).lower() for payer in filters['payer_any']) if pd.notna(x) else False
                )
                result_df = result_df[mask]
        
        if filters.get('drug_any'):
            drug_columns = ['NDC_GENERIC_NM', 'NDC_PREFERRED_BRAND_NM', 'NDC_DESC']
            mask = pd.Series(False, index=result_df.index)
            for col in drug_columns:
                if col in result_df.columns:
                    col_mask = result_df[col].apply(
                        lambda x: any(drug.lower() in str(x).lower() for drug in filters['drug_any']) if pd.notna(x) else False
                    )
                    mask |= col_mask
            result_df = result_df[mask]
        
        if filters.get('date_range_months'):
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=filters['date_range_months'] * 30)
            
            if 'SERVICE_DATE_DD' in result_df.columns:
                result_df = result_df[
                    (result_df['SERVICE_DATE_DD'] >= start_date) & 
                    (result_df['SERVICE_DATE_DD'] <= end_date)
                ]
        
        return result_df
    
    def _apply_filters(self, df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
        result_df = df.copy()
        
        if filters.get('name_contains'):
            mask = result_df['name'].apply(
                lambda x: any(name.lower() in str(x).lower() for name in filters['name_contains']) if pd.notna(x) else False
            )
            result_df = result_df[mask]
        
        if filters.get('specialty_any'):
            mask = result_df['specialties'].apply(
                lambda x: any(spec.lower() in [s.lower() for s in x] for spec in filters['specialty_any']) if isinstance(x, list) else False
            )
            result_df = result_df[mask]
        
        if filters.get('state_any'):
            mask = result_df['states'].apply(
                lambda x: any(state.lower() in [s.lower() for s in x] for state in filters['state_any']) if isinstance(x, list) else False
            )
            result_df = result_df[mask]
        
        if filters.get('hospital_any'):
            mask = result_df['hospital_names'].apply(
                lambda x: any(hosp.lower() in [h.lower() for h in x] for hosp in filters['hospital_any']) if isinstance(x, list) else False
            )
            result_df = result_df[mask]
        
        if filters.get('system_any'):
            mask = result_df['system_names'].apply(
                lambda x: any(sys.lower() in [s.lower() for s in x] for sys in filters['system_any']) if isinstance(x, list) else False
            )
            result_df = result_df[mask]
        
        if filters.get('org_type_any'):
            mask = result_df['org_type'].apply(
                lambda x: x.lower() in [ot.lower() for ot in filters['org_type_any']] if pd.notna(x) else False
            )
            result_df = result_df[mask]
        
        if filters.get('publications_min') is not None:
            result_df = result_df[result_df['num_publications'] >= filters['publications_min']]
        
        if filters.get('publications_max') is not None:
            result_df = result_df[result_df['num_publications'] <= filters['publications_max']]
        
        if filters.get('clinical_trials_min') is not None:
            result_df = result_df[result_df['num_clinical_trials'] >= filters['clinical_trials_min']]
        
        if filters.get('has_linkedin') is not None:
            result_df = result_df[result_df['has_linkedin'] == filters['has_linkedin']]
        
        if filters.get('has_twitter') is not None:
            result_df = result_df[result_df['has_twitter'] == filters['has_twitter']]
        
        return result_df
    
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


def execute_json_plan(json_plan: str, csv_path: str = "data/providers.csv", claims_path: str = "data/Mounjaro Claim Sample.csv") -> pd.DataFrame:
    plan = json.loads(json_plan)
    executor = PlanExecutor(csv_path, claims_path)
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