import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category, CategoryRule


async def categorize_transaction(
    description: str,
    household_id: uuid.UUID,
    db: AsyncSession,
) -> int | None:
    """
    Categorize a transaction by matching its description against rules.
    Priority: household rules > global rules.
    Returns category_id or None.
    """
    description_lower = description.lower()

    # Fetch all rules ordered by priority (household first, then global)
    result = await db.execute(
        select(CategoryRule)
        .where(
            (CategoryRule.household_id == household_id) | (CategoryRule.household_id.is_(None))
        )
        .order_by(
            # Household rules first (not null), then by priority desc
            CategoryRule.household_id.is_(None).asc(),
            CategoryRule.priority.desc(),
        )
    )
    rules = result.scalars().all()

    for rule in rules:
        if rule.pattern.lower() in description_lower:
            return rule.category_id

    return None


async def get_categories_map(db: AsyncSession) -> dict[int, str]:
    """Return a dict of category_id -> category_name."""
    result = await db.execute(select(Category))
    return {cat.id: cat.name for cat in result.scalars().all()}
