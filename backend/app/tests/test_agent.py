import os
import sys
import json
import logging
import asyncio
from typing import TypedDict, List, Dict, Any, Annotated
from datetime import datetime

# Add parent directories to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# Import Engines Directly (No MCP)
from app.engines.pre import PromptRiskEvaluator
from app.engines.ose import OutputSafetyEvaluator
from app.engines.aim import AgentIntentMonitor
from app.engines.rts import RedTeamEngine

import test_agent_config as config

# --- CONFIGURATION ---
# Get API key from environment variable ONLY (never hardcode it!)
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY environment variable not set. "
        "Please set it using: set GEMINI_API_KEY=your_api_key_here (Windows) "
        "or export GEMINI_API_KEY=your_api_key_here (Linux/Mac)"
    )

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VeridianAgent")

# Set Google API Key for LangChain
os.environ["GOOGLE_API_KEY"] = API_KEY

# Initialize Engines
pre_engine = PromptRiskEvaluator()
ose_engine = OutputSafetyEvaluator()
aim_engine = AgentIntentMonitor()
rts_engine = RedTeamEngine(safety_evaluator=ose_engine)

# --- STATE DEFINITION ---
class AgentState(TypedDict):
    test_cases: List[Dict]
    results: List[Dict]
    report: str
    logs: List[str]

# --- NODES ---

async def generate_tests(state: AgentState) -> AgentState:
    """Generates test cases using Gemini."""
    logger.info("Generating test cases...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite", 
        temperature=0.7,
        google_api_key=API_KEY
    )
    
    messages = [
        SystemMessage(content=config.TEST_GENERATION_PROMPT),
        HumanMessage(content="Generate the test cases now.")
    ]
    
    response = await llm.ainvoke(messages)
    content = response.content.strip()
    
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
        
    try:
        test_cases = json.loads(content)
        logger.info(f"Generated {len(test_cases)} test cases.")
    except json.JSONDecodeError:
        logger.error("Failed to parse test cases JSON.")
        test_cases = []
        
    return {"test_cases": test_cases, "results": [], "report": "", "logs": state.get("logs", []) + ["Generated tests"]}

async def run_tests(state: AgentState) -> AgentState:
    """Executes tests using direct function calls."""
    logger.info("Running tests (Direct Import)...")
    
    test_cases = state["test_cases"]
    results = []
    
    for test in test_cases:
        engine = test.get("engine")
        input_data = test.get("input")
        
        logger.info(f"Testing {engine} with input: {str(input_data)[:50]}...")
        
        actual_decision = "error"
        system_output = {}
        
        try:
            if engine == "PRE":
                system_output = pre_engine.evaluate_prompt(input_data)
                actual_decision = system_output.get("decision")
                
            elif engine == "OSE":
                system_output = ose_engine.evaluate_output("test_prompt", input_data)
                actual_decision = system_output.get("decision")
                
            elif engine == "AIM":
                # Handle string or dict input for AIM
                if isinstance(input_data, str):
                    try:
                        input_data = json.loads(input_data)
                    except:
                        pass # Pass as string if not valid json, let engine handle
                system_output = aim_engine.evaluate_agent_action(input_data)
                actual_decision = system_output.get("decision")
                
            elif engine == "RTS":
                # RTS returns a list of results, we'll take the first one for simplicity in this agent structure
                # or we could wrap it. For now, let's assume input is a prompt to test.
                rts_results = rts_engine.run_red_team_test(user_prompt=input_data)
                # RTS doesn't have a single "decision", it has evaluations for each attack.
                # We'll summarize: if any attack was successful (flagged/blocked), we report that.
                # But wait, RTS uses OSE to evaluate. OSE returns "flag" or "allow".
                # Let's check if any result was flagged.
                any_flagged = any(r.get("evaluation", {}).get("decision") == "flag" for r in rts_results)
                actual_decision = "flag" if any_flagged else "allow"
                system_output = {"rts_results": rts_results}
                
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            system_output = {"error": str(e)}
        
        results.append({
            "test_case": test,
            "actual_decision": actual_decision,
            "system_output": system_output
        })
                
    return {"results": results}

async def evaluate_results(state: AgentState) -> AgentState:
    """Evaluates the results using an LLM Judge."""
    logger.info("Evaluating results...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite", 
        temperature=0.1,
        google_api_key=API_KEY
    )
    evaluated_results = []
    
    for res in state["results"]:
        test_case = res["test_case"]
        
        prompt = config.EVALUATION_PROMPT.format(
            engine=test_case.get("engine"),
            input=test_case.get("input"),
            expected_decision=test_case.get("expected_decision"),
            actual_decision=res.get("actual_decision"),
            system_output=json.dumps(res.get("system_output"))
        )
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        try:
            eval_json = json.loads(content)
            res["status"] = eval_json.get("status", "UNKNOWN")
            res["analysis"] = eval_json.get("analysis", "")
        except:
            res["status"] = "UNKNOWN"
            res["analysis"] = "Failed to parse judge output"
            
        evaluated_results.append(res)
        
    return {"results": evaluated_results}

async def generate_report(state: AgentState) -> AgentState:
    """Generates the final markdown report."""
    logger.info("Generating report...")
    
    results = state["results"]
    total = len(results)
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = total - passed
    
    # Generate Table Rows
    rows = []
    for i, res in enumerate(results):
        test = res["test_case"]
        row = f"| {i+1} | {test.get('engine')} | {res.get('status')} | `{str(test.get('input'))[:30]}...` | {test.get('expected_decision')} | {res.get('actual_decision')} | {res.get('analysis')} |"
        rows.append(row)
        
    table_rows = "\n".join(rows)
    
    # Generate Summary & Recommendations using LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite", 
        temperature=0.5,
        google_api_key=API_KEY
    )
    summary_prompt = f"Analyze these test results and provide an executive summary and recommendations:\n{json.dumps(results, indent=2)}"
    summary_resp = await llm.ainvoke([HumanMessage(content=summary_prompt)])
    
    report = config.REPORT_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_tests=total,
        passed_tests=passed,
        failed_tests=failed,
        summary=summary_resp.content,
        table_rows=table_rows,
        recommendations="See Executive Summary"
    )
    
    # Save report to file
    with open("veridian_test_report.md", "w") as f:
        f.write(report)
        
    return {"report": report}

# --- GRAPH CONSTRUCTION ---

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("generate", generate_tests)
    workflow.add_node("execute", run_tests)
    workflow.add_node("evaluate", evaluate_results)
    workflow.add_node("report", generate_report)
    
    workflow.set_entry_point("generate")
    
    workflow.add_edge("generate", "execute")
    workflow.add_edge("execute", "evaluate")
    workflow.add_edge("evaluate", "report")
    workflow.add_edge("report", END)
    
    return workflow.compile()

if __name__ == "__main__":
    import asyncio
    
    async def main():
        app = build_graph()
        initial_state = {"test_cases": [], "results": [], "report": "", "logs": []}
        result = await app.ainvoke(initial_state)
        print("Workflow completed. Report generated: veridian_test_report.md")
        
    asyncio.run(main())
