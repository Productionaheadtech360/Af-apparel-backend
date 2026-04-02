"""Run all seed scripts. Safe to execute on every deploy — all seeds are idempotent."""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from app.core.database import AsyncSessionLocal
from app.seeds.seed_products import seed_products


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed_products(db)
    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
