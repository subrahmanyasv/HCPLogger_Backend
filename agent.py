import os
import json
import traceback  # Import traceback
from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.pydantic_v1 import BaseModel, Field  # Keep v1 for now
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from backend.database import settings  # Import settings to get API key
from backend.models import ParseResponse, SentimentEnum  # Import the response model
from datetime import datetime  # Import datetime


# --- Define the State for the Graph ---
class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        original_text: The initial input text from the user.
        extracted_data: The structured data extracted by the LLM.
        error_message: Any error message encountered during processing.
    """
    original_text: str
    extracted_data: Optional[dict] = None  # Store extracted data as dict initially
    error_message: Optional[str] = None


# --- Define the Pydantic Model for Structured Extraction ---
class ExtractedInteractionInfo(BaseModel):
    """Pydantic model for the LLM to extract information into."""
    hcp_name: Optional[str] = Field(None, description="Full name of the main Healthcare Professional met.")
    interaction_type: Optional[str] = Field(
        None, description="Type of interaction (e.g., 'Meeting', 'Call', 'Conference', 'Email'). Default to 'Meeting' if unclear."
    )
    interaction_date: Optional[str] = Field(
        None,
        description=f"Date of interaction in YYYY-MM-DD format. Infer from context (e.g., 'yesterday', 'last Tuesday'). Current date is {datetime.now().strftime('%Y-%m-%d')}."
    )
    interaction_time: Optional[str] = Field(
        None,
        description="Time of interaction, preferably in HH:MM (24-hour) format (e.g., 14:30) or HH:MM AM/PM format (e.g., 02:30 PM). If only hour is given, assume '00' minutes. If time is not mentioned, leave empty.",
    )
    attendees: Optional[List[str]] = Field(
        None, description="List of ALL people present, including the HCP and the user if mentioned. If only last name is given, try to find full name."
    )
    topics_discussed: Optional[str] = Field(
        None,
        description="A concise summary of the main topics discussed during the interaction. Focus on key points and avoid extraneous details. Include any concerns or reservations expressed.",
    )
    materials_shared: Optional[List[str]] = Field(
        None, description="List of specific materials, documents, brochures, or links shared. Be specific about the type of material."
    )
    samples_distributed: Optional[List[str]] = Field(
        None, description="List of specific drug samples distributed. Include dosage if available."
    )
    hcp_sentiment: Optional[SentimentEnum] = Field(
        None,
        description="The perceived sentiment of the HCP ('Positive', 'Neutral', 'Negative'). Infer from keywords or tone. If sentiment is not clear, leave empty. ALWAYS include the sentiment.",
    )
    outcomes: Optional[str] = Field(
        None,
        description="Key decisions, agreements, or conclusions reached during the interaction. What was decided? Even if the sentiment is negative, try to extract any decisions or agreements.",
    )
    follow_up_actions: Optional[str] = Field(
        None,
        description="Specific next steps or tasks agreed upon or planned. What are the next steps? Even if the sentiment is negative, try to extract any follow-up actions.",
    )


# --- Initialize the LLM (Groq) ---
print("-" * 20)
print(f"DEBUG: Attempting to use Groq API Key read from settings: '{settings.GROQ_API_KEY}'")
if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "YOUR_GROQ_API_KEY_HERE":
    print("ERROR: Groq API Key is missing, empty, or still the default placeholder!")
    raise ValueError("GROQ_API_KEY is not configured correctly in .env file")
print("-" * 20)

llm = ChatGroq(
    temperature=0,
    model_name="llama3-70b-8192",  # Or "gemma2-9b-it"
    groq_api_key=settings.GROQ_API_KEY,
    streaming=False # Disable streaming
)

# Use the Pydantic model with the LLM for structured output
structured_llm = llm.with_structured_output(ExtractedInteractionInfo)


# --- Define Nodes for the Graph ---
async def call_extraction_model(state: GraphState) -> GraphState:
    """
    Node that calls the Groq LLM with structured output instruction.

    Args:
        state: The current graph state.

    Returns:
        Updated graph state with extracted_data or error_message.
    """
    print("--- CALLING EXTRACTION MODEL ---")
    # Refined prompt for robust sentiment handling
    prompt = f"""
You are an expert information extractor. Your task is to extract information from interaction descriptions and format it as a JSON object.

Instructions:

1.  Carefully read the entire interaction description.
2.  Identify and extract the following information, regardless of the overall sentiment expressed. Do not let sentiment distract you from finding all the facts.
    * HCP name: Extract the full name of the Healthcare Professional.
    * Interaction type: Identify the type of interaction (e.g., meeting, call). If unclear, default to "Meeting".
    * Interaction date: Extract the date in YYYY-MM-DD format. Infer from context if necessary (e.g., "yesterday").
    * Interaction time: Extract the time. Use HH:MM 24-hour format if possible. If AM/PM is used, convert it. If only the hour is mentioned, assume minutes are "00". If no time is mentioned, leave it empty.
    * Attendees: List all attendees, including the HCP and the user.
    * Topics discussed: Summarize the main topics, focusing on factual information. Include any concerns, opinions, or reservations expressed.
    * Materials shared: List any materials shared (documents, brochures, etc.).
    * Samples distributed: List any drug samples distributed.
    * Outcomes: Describe any decisions, agreements, or conclusions reached.
    * Follow-up actions: List any specific next steps or tasks planned.
3.  After extracting all the information, determine the overall sentiment of the HCP's statements and attitude. Use "Positive", "Neutral", or "Negative".
4.  Output ONLY a valid JSON object. Do not include any other text.

Schema:
{{
  "hcp_name": "(string, optional) Full name of the Healthcare Professional.",
  "interaction_type": "(string, optional) Type of interaction.",
  "interaction_date": "(string, optional) Date in YYYY-MM-DD format.",
  "interaction_time": "(string, optional) Time (HH:MM 24-hour or HH:MM AM/PM).",
  "attendees": "(list of strings, optional) List of attendees.",
  "topics_discussed": "(string, optional) Summary of topics discussed.",
  "materials_shared": "(list of strings, optional) List of materials shared.",
  "samples_distributed": "(list of strings, optional) List of samples distributed.",
  "hcp_sentiment": "(string, optional) Sentiment ('Positive', 'Neutral', 'Negative').",
  "outcomes": "(string, optional) Outcomes of the interaction.",
  "follow_up_actions": "(string, optional) Follow-up actions."
}}

Interaction Description:
\"{state['original_text']}\"
"""
    messages = [
        SystemMessage(content="You are an expert information extractor. Output ONLY valid JSON."),
        HumanMessage(content=prompt),
    ]
    try:
        # Make the async call
        response = await structured_llm.ainvoke(messages)
        print(f"--- EXTRACTION RESPONSE ({type(response)}) ---")
        print(response)

        # Convert Pydantic model to dictionary for the state
        extracted_dict = response.dict(exclude_none=True)  # Exclude fields that are None
        return {**state, "extracted_data": extracted_dict, "error_message": None}

    except Exception as e:
        print(f"--- EXTRACTION ERROR ---")
        print(e)
        # Store the specific error message in the state
        error_msg = f"Error during LLM call: {str(e)}"
        return {**state, "extracted_data": None, "error_message": error_msg}


# --- Build the Graph ---
workflow = StateGraph(GraphState)
workflow.add_node("extract_info", call_extraction_model)
workflow.set_entry_point("extract_info")
workflow.add_edge("extract_info", END)
app_graph = workflow.compile()


# --- Function to Run the Agent ---
async def run_interaction_parser(text: str) -> ParseResponse:  # Changed return type annotation
    """
    Runs the LangGraph agent to parse the interaction text.

    Args:
        text: The free-form text input.

    Returns:
        A ParseResponse Pydantic model containing the extracted data,
        or a ParseResponse with an error message if extraction fails.
    """
    inputs = {"original_text": text}
    try:
        final_state = await app_graph.ainvoke(inputs)

        # Check if the agent workflow itself produced an error message
        if final_state.get("error_message"):
            print(f"Agent Error: {final_state['error_message']}")
            # Return an error response
            return ParseResponse(error=final_state["error_message"])

        extracted_data = final_state.get("extracted_data")

        # Check if extraction actually yielded data
        if not extracted_data:
            print("Agent Warning: No data extracted, though no explicit error reported.")
            # Return an error response
            return ParseResponse(error="No data extracted")

        # Validate and create the ParseResponse object
        try:
            # --- Date and Time Parsing ---
            if 'interaction_date' in extracted_data and isinstance(extracted_data['interaction_date'], str):
                try:
                    extracted_data['interaction_date'] = datetime.strptime(
                        extracted_data['interaction_date'], "%Y-%m-%d"
                    ).date()
                except (ValueError, TypeError):
                    print(f"Warning: Could not parse date '{extracted_data['interaction_date']}'. Setting to None.")
                    extracted_data["interaction_date"] = None  # Handle invalid date format

            if "interaction_time" in extracted_data and isinstance(extracted_data["interaction_time"], str):
                time_str = extracted_data["interaction_time"].strip()
                parsed_time = None
                # Try parsing with AM/PM first
                try:
                    parsed_time = datetime.strptime(time_str, "%I:%M %p").time()  # Format like '10:30 AM'
                except (ValueError, TypeError):
                    # If AM/PM parse fails, try 24-hour format
                    try:
                        parsed_time = datetime.strptime(time_str, "%H:%M").time()  # Format like '10:30' or '14:00'
                    except (ValueError, TypeError):
                        print(
                            f"Warning: Could not parse time '{time_str}' using known formats. Setting to None."
                        )
                        # Keep parsed_time as None
                extracted_data["interaction_time"] = parsed_time
            # --- End of Date and Time Parsing ---

            # Create the response model, Pydantic handles validation
            response_obj = ParseResponse(**extracted_data)
            return response_obj

        except Exception as validation_error:  # Catch Pydantic validation errors specifically
            print(f"Validation Error creating ParseResponse: {validation_error}")
            print(f"Data causing error: {extracted_data}")
            traceback.print_exc()
            # Return a validation error response
            return ParseResponse(error="Validation error", error_details=str(validation_error))

    except Exception as agent_exec_error:
        # Catch errors during the agent execution itself
        print(f"Critical Agent Execution Error: {agent_exec_error}")
        traceback.print_exc()
        # Return a general agent execution error
        return ParseResponse(error="Agent execution error", error_details=str(agent_exec_error))