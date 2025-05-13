# backend/main.py

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse # Import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import traceback # Import traceback for better error logging
import datetime # Import datetime for isoformat checks

# Import components from other backend files
from backend import models, crud, database, agent # Use backend.* for clarity

# Create FastAPI app instance
app = FastAPI(title="HCP Interaction Logger API")

# --- CORS Middleware ---
# Allow requests from your frontend development server and production domain
origins = [
    "http://localhost:3000",  # Default React dev server port
    "http://localhost:5173",  # Default Vite dev server port
    # Add your production frontend URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- Event Handlers ---
@app.on_event("startup")
async def on_startup():
    """ Initialize the database when the application starts """
    print("Initializing database...")
    # This is okay for development, use Alemic/migrations for production
    await database.init_db()
    print("Database initialized.")

# --- API Endpoints ---

@app.post("/interactions/parse",
          response_model=models.ParseResponse,
          summary="Parse Interaction Text using AI",
          description="Receives free-form text, uses LangGraph/Groq to extract structured data.")
async def parse_interaction_text(
    request: models.ParseRequest
):
    """
    Endpoint to parse free-form text input using the AI agent.
    """
    print(f"Received text to parse: {request.text[:100]}...") # Log received text
    try:
        extracted_data = await agent.run_interaction_parser(request.text)
        print(f"Extracted data: {extracted_data}")
        return extracted_data
    except Exception as e:
        print(f"Error during parsing: {e}")
        # Log the full error traceback if possible
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse interaction text: {str(e)}"
        )

@app.post("/interactions",
           response_model=models.Interaction,
           status_code=status.HTTP_201_CREATED,
           summary="Submit HCP Interaction",
           description="Receives structured interaction data and saves it to the database.")
async def submit_interaction(
    interaction: models.InteractionCreate,
    db: AsyncSession = Depends(database.get_db) # Inject DB session
):
    """
    Endpoint to submit the completed interaction form data.
    """
    print(f"Received interaction data to save: {interaction}")
    try:
        db_interaction = await crud.create_interaction(db=db, interaction_data=interaction)
        print(f"Saved interaction with ID: {db_interaction.id}")

        # --- Manually construct response data dictionary ---
        response_data_dict = {
            "id": db_interaction.id,
            "hcp_name": db_interaction.hcp_name,
            "interaction_type": db_interaction.interaction_type,
            "interaction_date": db_interaction.interaction_date,
            "interaction_time": db_interaction.interaction_time,
            "topics_discussed": db_interaction.topics_discussed,
            "hcp_sentiment": db_interaction.hcp_sentiment,
            "outcomes": db_interaction.outcomes,
            "follow_up_actions": db_interaction.follow_up_actions,
            "created_at": db_interaction.created_at,
            "updated_at": db_interaction.updated_at,
            # Use helper methods to get lists from comma-separated strings
            "attendees": db_interaction.get_attendees(),
            "materials_shared": db_interaction.get_materials_shared(),
            "samples_distributed": db_interaction.get_samples_distributed(),
        }

        # Validate the manually created dictionary using the Pydantic model
        validated_response = models.Interaction(**response_data_dict)
        return validated_response # Return the validated Pydantic model

    except Exception as e:
        print(f"Error saving interaction: {e}")
        traceback.print_exc() # Print full traceback for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save interaction: {str(e)}"
        )


@app.get("/interactions",
          response_model=List[models.Interaction],
          summary="Get Recent Interactions",
          description="Retrieves a list of recently logged interactions.")
async def read_interactions(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(database.get_db)
):
    """
    Endpoint to retrieve a list of interactions (example).
    """
    interactions_db = await crud.get_interactions(db, skip=skip, limit=limit)
    interactions_list = []
    for db_interaction in interactions_db:
         # --- Manually construct response data dictionary ---
        response_data_dict = {
            "id": db_interaction.id,
            "hcp_name": db_interaction.hcp_name,
            "interaction_type": db_interaction.interaction_type,
            "interaction_date": db_interaction.interaction_date,
            "interaction_time": db_interaction.interaction_time,
            "topics_discussed": db_interaction.topics_discussed,
            "hcp_sentiment": db_interaction.hcp_sentiment,
            "outcomes": db_interaction.outcomes,
            "follow_up_actions": db_interaction.follow_up_actions,
            "created_at": db_interaction.created_at,
            "updated_at": db_interaction.updated_at,
            # Use helper methods to get lists
            "attendees": db_interaction.get_attendees(),
            "materials_shared": db_interaction.get_materials_shared(),
            "samples_distributed": db_interaction.get_samples_distributed(),
        }
        # Validate and append
        try:
            validated_interaction = models.Interaction(**response_data_dict)
            interactions_list.append(validated_interaction)
        except Exception as validation_error:
             print(f"Error validating interaction ID {db_interaction.id} for response: {validation_error}")
             traceback.print_exc()

    return interactions_list

# --- EXPORT ENDPOINT ---
@app.get("/interactions/export",
         response_class=JSONResponse, # Explicitly use JSONResponse
         summary="Export All Interactions as JSON",
         description="Retrieves all interaction records from the database and returns them as a JSON array.")
async def export_interactions_json(
    db: AsyncSession = Depends(database.get_db)
):
    """
    Endpoint to retrieve ALL interactions for export.
    """
    try:
        all_interactions_db = await crud.get_all_interactions(db) # Use the CRUD function
        export_data = []
        for db_interaction in all_interactions_db:
            # Construct the dictionary for each interaction, handling lists and formatting
            interaction_dict = {
                "id": db_interaction.id,
                "hcp_name": db_interaction.hcp_name,
                "interaction_type": db_interaction.interaction_type,
                # Safely format date/time/datetime using isoformat()
                "interaction_date": db_interaction.interaction_date.isoformat() if isinstance(db_interaction.interaction_date, datetime.date) else None,
                "interaction_time": db_interaction.interaction_time.isoformat() if isinstance(db_interaction.interaction_time, datetime.time) else None,
                "attendees": db_interaction.get_attendees(),
                "topics_discussed": db_interaction.topics_discussed,
                "materials_shared": db_interaction.get_materials_shared(),
                "samples_distributed": db_interaction.get_samples_distributed(),
                # Safely get enum value
                "hcp_sentiment": db_interaction.hcp_sentiment.value if db_interaction.hcp_sentiment else None,
                "outcomes": db_interaction.outcomes,
                "follow_up_actions": db_interaction.follow_up_actions,
                "created_at": db_interaction.created_at.isoformat() if isinstance(db_interaction.created_at, datetime.datetime) else None,
                "updated_at": db_interaction.updated_at.isoformat() if isinstance(db_interaction.updated_at, datetime.datetime) else None,
            }
            export_data.append(interaction_dict)

        # Set headers to suggest filename for download (optional)
        headers = {
            "Content-Disposition": "attachment; filename=\"hcp_interactions_export.json\""
        }
        # Return data using JSONResponse
        return JSONResponse(content=export_data, headers=headers)

    except Exception as e:
        print(f"Error exporting interactions: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export interactions: {str(e)}"
        )


# --- Root Endpoint (Optional) ---
@app.get("/", summary="API Root", description="Basic API health check.")
async def read_root():
    return {"message": "HCP Interaction Logger API is running!"}

# --- How to Run (Instructions) ---
# 1. Make sure you have SQLite setup (or PostgreSQL if you switched back).
# 2. Create a .env file in the backend directory with DATABASE_URL and GROQ_API_KEY.
# 3. Install requirements: pip install -r requirements.txt
# 4. Run the server: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
#    (Use --reload for development, remove for production)
