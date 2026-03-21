# seed_runner.py

import asyncio
from app.scripts.seed_permissions import seed  # поправь путь

asyncio.run(seed())