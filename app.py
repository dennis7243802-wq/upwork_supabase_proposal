import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import streamlit as st
from supabase import create_client

# ==========================================
# 1. Page Configuration & Setup
# ==========================================
st.set_page_config(
    page_title="Upwork Demo", layout="wide"
)

st.title("🔬 Research Workflow AI Automation - Proposal Demo")
st.markdown(
    "This demo showcases how unstructured research evidence is extracted "
    "into structured values using Gemini, reviewed/edited by a human, and saved to Supabase with evidence linkage."
)

# ==========================================
# 2. Sidebar: Configuration & Sample Input
# ==========================================
with st.sidebar:
  st.header("⚙️ System Configuration")
  '''
  gemini_api_key = st.text_input("Gemini API Key", type="password")
  supabase_url = st.text_input("Supabase URL", value="")
  supabase_key = st.text_input("Supabase Anon Key", type="password")
  '''
  gemini_api_key = st.text_input(
      "Gemini API Key",
      value=st.secrets.get("GEMINI_API_KEY", ""),
      type="password",
  )
  supabase_url = st.text_input(
      "Supabase URL", value=st.secrets.get("SUPABASE_URL", "")
  )
  supabase_key = st.text_input(
      "Supabase Anon Key",
      value=st.secrets.get("SUPABASE_KEY", ""),
      type="password",
  )
=======
  gemini_api_key = st.text_input("Gemini API Key", type="password")
  supabase_url = st.text_input("Supabase URL", value="")
  supabase_key = st.text_input("Supabase Anon Key", type="password")

  st.markdown("---")
  st.markdown("### 📥 Test Sample Evidence")
  default_sample_evidence = (
      "According to the Q4 2025 financial research report, "
      "ABC Technology Corp achieved a total revenue of $12.5 million "
      "for the quarter, representing an 18.5% year-over-year increase, "
      "primarily driven by higher cloud subscription volume."
  )
  sample_input_text = st.text_area(
      "Source Evidence Text", value=default_sample_evidence, height=150
  )


# ==========================================
# 3. Define Pydantic Schema for Structured Output
# ==========================================
class ResearchExtractionSchema(BaseModel):
  field_name: str = Field(
      description="The structured field name extracted (e.g., Total Revenue, YoY Growth Rate)"
  )
  extracted_value: str = Field(
      description="The structured value or key conclusion extracted by AI"
  )
  evidence_snippet: str = Field(
      description="The exact verbatim text snippet from the source document supporting this conclusion"
  )
  confidence_score: float = Field(
      description="AI confidence score for this extraction ranging from 0.0 to 1.0"
  )


# ==========================================
# 4. Main Panel: Extraction & Human Review UI
# ==========================================
col1, col2 = st.columns(2)

# Initialize Session State to hold extraction results
if "extraction_result" not in st.session_state:
  st.session_state.extraction_result = None

with col1:
  st.subheader("📄 1. Source Evidence Inspector")
  st.info(sample_input_text)

  run_button = st.button("🚀 Run AI Extraction", type="primary")

  if run_button:
    # check Gemini key
    if not gemini_api_key:
      st.error("Please enter your Gemini API Key in the sidebar first!")
    # check empty text 
    elif not sample_input_text.strip():
      st.error(
          "Please enter or paste some source evidence text before running"
          " extraction!"
      )
    else:
      try:
        with st.spinner("Analyzing evidence and extracting structured fields..."):
          # Initialize Google GenAI client with official SDK
          client = genai.Client(api_key=gemini_api_key)

          prompt = f"""
                    Extract key business or research structured metrics/attributes from the source evidence below.
                    Ensure the evidence_snippet field is strictly quoted from the source text.
                    
                    Source Evidence:
                    {sample_input_text}
                    """

          # Generate structured output using gemini-3.5-flash
          response = client.models.generate_content(
              model="gemini-3.5-flash",
              contents=prompt,
              config=types.GenerateContentConfig(
                  response_mime_type="application/json",
                  response_schema=ResearchExtractionSchema,
                  temperature=0.1,
              ),
          )

          # Parse JSON response
          parsed_data = json.loads(response.text)
          st.session_state.extraction_result = parsed_data
          st.success("Extraction successful! Proceed to review on the right.")
      except Exception as e:
        st.error(f"An error occurred: {e}")

with col2:
  st.subheader("✍️ 2. Human Review & Approval Interface")

  if st.session_state.extraction_result:
    res = st.session_state.extraction_result

    with st.form("review_form"):
      st.markdown(
          "Review the AI-extracted values below. Make adjustments if"
          " necessary before saving:"
      )

      revised_field_name = st.text_input("Field Name", value=res.get("field_name", ""))
      revised_value = st.text_input(
          "Extracted Value / Conclusion", value=res.get("extracted_value", "")
      )
      revised_snippet = st.text_area(
          "Linked Evidence Snippet", value=res.get("evidence_snippet", "")
      )
      confidence = res.get("confidence_score", 0.0)
      st.caption(f"🤖 AI Original Confidence Score: {confidence}")

      submitted = st.form_submit_button("✅ Approve & Save to Supabase")

      if submitted:
        if not supabase_url or not supabase_key:
          st.error(
              "Please configure your Supabase URL and Anon Key in the sidebar!"
          )
        else:
          try:
            # Connect to Supabase and insert record
            supabase = create_client(supabase_url, supabase_key)

            payload = {
                "field_name": revised_field_name,
                "extracted_value": revised_value,
                "evidence_snippet": revised_snippet,
                "status": "approved",
            }

            response = (
                supabase.table("extracted_records").insert(payload).execute()
            )

            st.success("🎉 Record successfully reviewed and saved to Supabase!")
            st.json(payload)
          except Exception as db_error:
            st.error(
                "Failed to write to Supabase (ensure table"
                f" 'extracted_records' is created): {db_error}"
            )
  else:
    st.warning(
        "No extraction data available. Click 'Run AI Extraction' on the left"
        " first."
    )

# ==========================================
# 5. Local Execution Instructions
# ==========================================
st.markdown("---")
st.markdown("### 📖 Local Execution Guide")
st.markdown("""
1. Save this script as `app.py`.
2. Install dependencies: `pip install streamlit google-genai pydantic supabase`
3. Run the app in your terminal: `streamlit run app.py`
4. Enter your **Gemini API Key** and **Supabase credentials** in the sidebar.
5. Click **Run AI Extraction**, review or edit the fields on the right, and click **Approve & Save to Supabase** to complete the pipeline demo!
""")