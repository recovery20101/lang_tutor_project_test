import asyncio
from app.services.init_db import import_initial_data_if_empty

if __name__ == "__main__":
    asyncio.run(import_initial_data_if_empty())
