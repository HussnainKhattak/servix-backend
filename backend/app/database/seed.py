import asyncio
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.category import ServiceCategory
from app.core.logging import logger

INITIAL_CATEGORIES = [
    {
        "name": "Plumbing",
        "slug": "plumbing",
        "icon": "🚰",
        "description": "Leak repairs, pipe installations, drain cleaning, and water heater services.",
        "avg_price_min": 75.0,
        "avg_price_max": 250.0,
    },
    {
        "name": "Electrical",
        "slug": "electrical",
        "icon": "⚡",
        "description": "Lighting fixtures, panel upgrades, outlet replacements, and wiring diagnostics.",
        "avg_price_min": 85.0,
        "avg_price_max": 300.0,
    },
    {
        "name": "HVAC & AC",
        "slug": "hvac",
        "icon": "❄️",
        "description": "AC maintenance, heater tune-ups, duct cleaning, and thermostat installations.",
        "avg_price_min": 100.0,
        "avg_price_max": 450.0,
    },
    {
        "name": "Handyman & Assembly",
        "slug": "handyman",
        "icon": "🔨",
        "description": "Furniture assembly, TV mounting, door repairs, and minor home improvements.",
        "avg_price_min": 50.0,
        "avg_price_max": 180.0,
    },
    {
        "name": "Home Cleaning",
        "slug": "cleaning",
        "icon": "✨",
        "description": "Deep cleaning, move-in/move-out cleans, and recurring maid services.",
        "avg_price_min": 80.0,
        "avg_price_max": 220.0,
    },
    {
        "name": "Painting",
        "slug": "painting",
        "icon": "🎨",
        "description": "Interior walls, exterior siding, fence staining, and drywall patching.",
        "avg_price_min": 150.0,
        "avg_price_max": 800.0,
    },
    {
        "name": "Appliance Repair",
        "slug": "appliance-repair",
        "icon": "🔌",
        "description": "Refrigerators, washing machines, dryers, dishwashers, and ovens.",
        "avg_price_min": 70.0,
        "avg_price_max": 220.0,
    },
    {
        "name": "Roofing & Gutters",
        "slug": "roofing",
        "icon": "🏠",
        "description": "Gutter cleaning, roof leak repairs, shingle replacement, and inspections.",
        "avg_price_min": 120.0,
        "avg_price_max": 600.0,
    },
    {
        "name": "Lawn Care & Landscaping",
        "slug": "landscaping",
        "icon": "🌿",
        "description": "Lawn mowing, tree trimming, garden mulching, and yard cleanup.",
        "avg_price_min": 45.0,
        "avg_price_max": 200.0,
    },
]


async def seed_categories() -> int:
    """Seed initial categories into database if empty."""
    seeded_count = 0
    async with AsyncSessionLocal() as session:
        for cat_data in INITIAL_CATEGORIES:
            existing = await session.execute(
                select(ServiceCategory).where(ServiceCategory.slug == cat_data["slug"])
            )
            if not existing.scalars().first():
                category = ServiceCategory(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    icon=cat_data["icon"],
                    description=cat_data["description"],
                    avg_price_min=cat_data["avg_price_min"],
                    avg_price_max=cat_data["avg_price_max"],
                    is_active=True,
                )
                session.add(category)
                seeded_count += 1

        if seeded_count > 0:
            await session.commit()
            logger.info(f"Seeded {seeded_count} service categories.")

    return seeded_count


if __name__ == "__main__":
    asyncio.run(seed_categories())
