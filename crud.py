# backend/crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.models import InteractionDB, InteractionCreate, Interaction # Import necessary models
from typing import List, Optional

async def create_interaction(db: AsyncSession, interaction_data: InteractionCreate) -> InteractionDB:
    """
    Creates a new interaction record in the database.

    Args:
        db: The AsyncSession instance.
        interaction_data: The Pydantic model containing interaction data.

    Returns:
        The newly created InteractionDB object.
    """
    # Convert Pydantic model to dictionary, handle list fields
    db_interaction_data = interaction_data.dict(exclude_unset=True) # Exclude fields not provided

    # Handle list fields specifically if storing as comma-separated strings
    attendees_list = db_interaction_data.pop('attendees', None)
    materials_list = db_interaction_data.pop('materials_shared', None)
    samples_list = db_interaction_data.pop('samples_distributed', None)

    db_interaction = InteractionDB(**db_interaction_data)

    if attendees_list:
        db_interaction.set_attendees(attendees_list)
    if materials_list:
        db_interaction.set_materials_shared(materials_list)
    if samples_list:
        db_interaction.set_samples_distributed(samples_list)

    db.add(db_interaction)
    await db.flush() # Flush to get the ID before commit (if needed)
    await db.refresh(db_interaction) # Refresh to get defaults like created_at
    # Note: commit happens in the get_db dependency
    return db_interaction

async def get_interaction(db: AsyncSession, interaction_id: int) -> Optional[InteractionDB]:
    """
    Retrieves a single interaction by its ID.

    Args:
        db: The AsyncSession instance.
        interaction_id: The ID of the interaction to retrieve.

    Returns:
        The InteractionDB object if found, otherwise None.
    """
    result = await db.execute(select(InteractionDB).filter(InteractionDB.id == interaction_id))
    return result.scalars().first()

async def get_interactions(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[InteractionDB]:
    """
    Retrieves a list of interactions with pagination.

    Args:
        db: The AsyncSession instance.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of InteractionDB objects.
    """
    result = await db.execute(
        select(InteractionDB)
        .order_by(InteractionDB.created_at.desc()) # Example ordering
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def get_all_interactions(db: AsyncSession) -> List[InteractionDB]:
    """
    Retrieves ALL interactions from the database without pagination.

    Args:
        db: The AsyncSession instance.

    Returns:
        A list of all InteractionDB objects.
    """
    result = await db.execute(
        select(InteractionDB)
        .order_by(InteractionDB.created_at.desc()) # Example ordering
    )
    return result.scalars().all()

