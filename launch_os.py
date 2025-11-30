import streamlit as st
import json
import requests
import time
import os

st.set_page_config(layout="wide", page_title="Product Launch Governance Prototype", page_icon="🚀")

# --- CONFIGURATION ---
# User requested specific model slug
MODEL_SLUG = "anthropic/claude-4.5-sonnet"

# --- AUTHENTICATION ---
# This is crucial for Streamlit Cloud. We check secrets first.
if "OPENROUTER_API_KEY" in st.secrets:
    api_key = st.secrets["OPENROUTER_API_KEY"]
    auth_status = "✅ Key loaded from Environment"
else:
    # Fallback for local testing or if secrets aren't set
    api_key = st.sidebar.text_input("OpenRouter API Key", type="password")
    if api_key:
        auth_status = "✅ Key entered manually"
    else:
        auth_status = "⚠️ Waiting for Key..."

# --- STATE MANAGEMENT ---
if 'constitution' not in st.session_state:
    try:
        with open('baseline_rules.json', 'r') as f:
            st.session_state.constitution = json.load(f)
    except FileNotFoundError:
        st.error("⚠️ baseline_rules.json not found! Using fallback rules.")
        st.session_state.constitution = [
            {"id": "R1", "concept": "PII Data", "action": "Mandatory Privacy Legal Review", "owner": "Legal"}
        ]

if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None

if 'council_feedback' not in st.session_state:
    st.session_state.council_feedback = None

# --- HELPER FUNCTIONS ---
def call_llm(prompt, system_prompt, key):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://launch-governance-prototype.streamlit.app/", 
        "X-Title": "Launch Governance Prototype"
    }
    data = {
        "model": MODEL_SLUG, 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status() 
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"Debug Error: {str(e)}") # This will print the real API error to the screen
        return None

def extract_json(text):
    """Robust JSON extractor for LLM responses"""
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
        return None
    except:
        return None

def load_default_prd():
    try:
        with open('risky_prd.txt', 'r') as f:
            return f.read()
    except:
        return "Error loading risky_prd.txt"

# --- UI LAYOUT ---
st.title("🚀 Product Launch Automated Governance Agent")
st.markdown("""
**Simulation Goal:** Demonstrate how AI agents can "Cure the Scaling Tax" by moving from static checklists to dynamic risk analysis.
""")

# DESIGN TWEAK 2: Help Box to frame the scenario
with st.expander("ℹ️  **How this Prototype works (Read Me)**", expanded=True):
    st.markdown("""
    1. **The System of Record:** The sidebar contains the "Constitution" (our fixed governance policies).
    2. **The Happy Path:** If a PRD matches known rules, it auto-generates a checklist.
    3. **The Novel Risk (Demo):** We have pre-loaded a **"Structural Engineering"** PRD below. This contains a risk *not* in the Constitution.
    4. **The Agent:** Watch how the system detects the ambiguity and triggers a "Synthetic Council" to update the policy in real-time.
    """)

st.divider()

# SIDEBAR: SYSTEM OF RECORD
with st.sidebar:
    st.header("⚙️ System of Record")
    st.caption(f"Status: {auth_status}")
    
    st.divider()
    st.subheader("📜 Active Policy Guardrails")
    st.info("These rules are dynamically applied to every launch.")
    
    for rule in st.session_state.constitution:
        with st.expander(f"🔐 {rule['owner']}: {rule['concept']}"):
            st.write(f"**Action:** {rule['action']}")

# MAIN AREA
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Feature Intake")
    
    default_text = load_default_prd()
    
    prd_text = st.text_area(
        "📝 Draft PRD / Spec (Pre-loaded with High-Risk Scenario)", 
        value=default_text, 
        height=450,
        help="This text represents a draft PRD submitted by a PM. You can edit it, or use the pre-loaded example."
    )
    
    if st.button("🔍 Run Governance Scan", type="primary", disabled=not api_key):
        with st.spinner("🕵️‍♀️ Consulting the Constitution & Analyzing Risk..."):
            
            # 1. Prepare Rules Context
            rules_str = json.dumps(st.session_state.constitution)
            
            # 2. System Prompt for The Scanner
            sys_prompt = f"""
            You are the Anthropic Governance Engine. 
            Compare the Input PRD against the following Strict Governance Rules: {rules_str}
            
            Task:
            1. Check if any existing rules are triggered.
            2. DETECT NOVEL RISKS: Look for risks that are NOT covered by existing rules (e.g., 3rd party data sharing, biometrics, etc).
            3. Assign an 'ambiguity_score' (1-10). 10 = Highly risky/novel with NO matching rule.
            
            Output strictly valid JSON:
            {{
                "checklist": [
                    {{ "rule_id": "RULE-XXX", "triggered": true, "reason": "Explanation" }}
                ],
                "ambiguity_score": int,
                "ambiguity_reason": "Explanation of the novel risk",
                "risk_level": "Low" | "Medium" | "High"
            }}
            """
            
            raw_res = call_llm(prd_text, sys_prompt, api_key)
            if raw_res:
                data = extract_json(raw_res)
                if data:
                    st.session_state.scan_results = data
                    st.session_state.council_feedback = None # Reset downstream state
                else:
                    st.error("Failed to parse Governance response.")
            else:
                st.error("Connection Error or Invalid Key")

with col2:
    st.subheader("2. Launch Readiness")
    
    if st.session_state.scan_results:
        res = st.session_state.scan_results
        
        # Risk Badge
        risk_map = {"Low": "green", "Medium": "orange", "High": "red"}
        st.markdown(f":{risk_map.get(res.get('risk_level', 'Medium'), 'grey')}[**Risk Level: {res.get('risk_level')}**]")
        
        # Display Standard Checklist
        st.markdown("#### ✅ Compliance Checklist")
        checklist_items = res.get('checklist', [])
        
        triggered_rules = [i for i in checklist_items if i['triggered']]
        
        if not triggered_rules:
            st.success("No existing governance rules triggered.")
        
        for item in triggered_rules:
            # Find the rule details
            rule_def = next((r for r in st.session_state.constitution if r['id'] == item['rule_id']), None)
            if rule_def:
                st.error(f"**STOP: {rule_def['owner']} Review Required**")
                st.markdown(f"**Trigger:** {rule_def['concept']}")
                st.markdown(f"**Reason:** {item['reason']}")
                st.caption(f"Required Action: {rule_def['action']}")
                st.divider()

        # AMBIGUITY HANDLING
        ambiguity = res.get('ambiguity_score', 0)
        if ambiguity > 6:
            st.warning(f"⚠️ **High Ambiguity Detected (Score: {ambiguity}/10)**")
            st.write(f"**System Note:** {res.get('ambiguity_reason')}")
            
            st.info("💡 No existing rule covers this specific risk. Initiating Synthetic Council...")
            
            if st.button("⚡ Trigger Synthetic Stakeholder Review (Safety + Legal)"):
                with st.spinner("Simulating debate between Safety, Legal, and Security..."):
                    council_prompt = """
                    You are a Synthetic Stakeholder Council (Safety, Legal, Security).
                    The user is proposing a feature with a NOVEL RISK that is not in our Constitution.
                    
                    1. Analyze the risk.
                    2. PROPOSE A NEW PERMANENT RULE for the Constitution to handle this in the future.
                    
                    Output JSON:
                    {
                        "safety_opinion": "text",
                        "legal_opinion": "text",
                        "proposed_new_rule": {
                            "concept": "Short Name (e.g. 3rd Party Data)",
                            "action": "The required process (e.g. Vendor Security Review)",
                            "owner": "Team Name"
                        }
                    }
                    """
                    raw_council = call_llm(prd_text, council_prompt, api_key)
                    if raw_council:
                        c_data = extract_json(raw_council)
                        st.session_state.council_feedback = c_data

    # EVOLUTION STEP
    if st.session_state.council_feedback:
        cf = st.session_state.council_feedback
        st.markdown("---")
        st.subheader("🏛️ Council Findings")
        
        c1, c2 = st.columns(2)
        c1.warning(f"**Safety:** {cf.get('safety_opinion')}")
        c2.error(f"**Legal:** {cf.get('legal_opinion')}")
        
        st.success("✨ Proposal: Update System of Record")
        st.markdown("The Council recommends codifying a new rule so future launches are caught automatically.")
        
        new_rule = cf.get('proposed_new_rule', {})
        
        with st.form("update_constitution"):
            c_concept = st.text_input("New Rule Trigger", value=new_rule.get('concept'))
            c_owner = st.text_input("Owner", value=new_rule.get('owner'))
            c_action = st.text_input("Required Action", value=new_rule.get('action'))
            
            if st.form_submit_button("Commit New Rule to Constitution"):
                # Add to session state
                st.session_state.constitution.append({
                    "id": f"RULE-{len(st.session_state.constitution)+1:03d}",
                    "concept": c_concept,
                    "action": c_action,
                    "owner": c_owner
                })
                st.balloons()
                st.success("Constitution Updated! This logic is now part of the operating system.")
                time.sleep(2)
                st.rerun()