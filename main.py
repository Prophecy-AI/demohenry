import json
import sys
from agent import Agent
from executor import PlanExecutor

def main():
    print("🎯 HCP TARGETING AGENT")
    print("=" * 50)
    print("Enter natural language queries to find healthcare providers.")
    print("Type 'quit' to exit.\n")
    
    agent = Agent()
    executor = PlanExecutor("data/providers.csv", "data/Mounjaro Claim Sample.csv")
    
    while True:
        user_input = input("🔍 Query: ").strip()
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
            
        try:
            json_plan = agent.process_message(user_input)
            
            if "```json" in json_plan:
                json_start = json_plan.find("```json") + 7
                json_end = json_plan.find("```", json_start)
                json_plan = json_plan[json_start:json_end].strip()
            elif "```" in json_plan:
                json_start = json_plan.find("```") + 3
                json_end = json_plan.find("```", json_start)
                if json_end == -1:
                    json_end = len(json_plan)
                json_plan = json_plan[json_start:json_end].strip()
            
            if not json_plan.startswith('{'):
                start_idx = json_plan.find('{')
                if start_idx != -1:
                    json_plan = json_plan[start_idx:]
            
            plan = json.loads(json_plan)
            
            result_df = executor.execute_plan(plan)
            print(f"\n📊 Results: {len(result_df)} doctors found")
            
            if not result_df.empty:
                display_columns = []
                for col in ['name', 'specialties', 'states', 'num_publications', 'total_prescriptions', 'unique_patients']:
                    if col in result_df.columns:
                        display_columns.append(col)
                
                if not display_columns:
                    display_columns = list(result_df.columns)[:5]
                
                print(f"\nTop {min(10, len(result_df))} results:")
                print(result_df[display_columns].head(10).to_string(index=False, max_colwidth=25))
                
                if len(result_df) > 10:
                    print(f"... and {len(result_df) - 10} more results")
                    
                if plan.get('plan_notes'):
                    print(f"\n{plan['plan_notes']}")
            else:
                print("No doctors found matching your criteria.")
            
            print("\n" + "=" * 60)
            
        except json.JSONDecodeError as e:
            print(f"❌ Error: Could not parse the generated plan as JSON")
            print(f"Raw response: {json_plan[:200]}...")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

def run_test_queries():
    """Run a set of test queries to demonstrate capabilities"""
    print("🧪 Running test queries...")
    
    agent = Agent()
    executor = PlanExecutor("data/providers.csv", "data/Mounjaro Claim Sample.csv")
    
    test_queries = [
        "Neurologists in California with more than 30 publications",
        "Doctors with at least 5 clinical trials",
        "Doctors who prescribed Mounjaro in the last 6 months",
        "Rheumatologists who did not prescribe Humira in the last year"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: {query}")
        try:
            json_plan = agent.process_message(query)
            
            # Extract JSON
            if "```json" in json_plan:
                json_start = json_plan.find("```json") + 7
                json_end = json_plan.find("```", json_start)
                json_plan = json_plan[json_start:json_end].strip()
            
            plan = json.loads(json_plan)
            result_df = executor.execute_plan(plan)
            
            print(f"✅ Found {len(result_df)} results")
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        run_test_queries()
    else:
        main()
