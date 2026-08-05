"""One-off fixture seeding for the baseline load test.

Inserts N pre-verified users directly into Postgres, bypassing the
register/verify-email flow (and its per-IP rate limits) since we only need
authenticated sessions for k6 to drive, not to exercise registration itself.
Run once inside the backend container: docker compose exec backend python performance/seed_users.py <count>
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://voiceguard:voiceguard@postgres:5432/voiceguard"
PASSWORD = "LoadTest!2345"
COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 100


async def main():
    password_hash = bcrypt.hashpw(PASSWORD.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    engine = create_async_engine(DATABASE_URL)
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        for i in range(COUNT):
            email = f"loadtest_user{i:03d}@example.com"
            user_id = uuid.uuid5(uuid.NAMESPACE_DNS, email)
            await conn.execute(
                text(
                    """
                    INSERT INTO users (id, email, password_hash, role, subscription_tier,
                                        email_verified, onboarding_completed, display_name,
                                        created_at, updated_at)
                    VALUES (:id, :email, :password_hash, 'user', 'free', true, true, :display_name, :now, :now)
                    ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash,
                                                       email_verified = true
                    """
                ),
                {
                    "id": str(user_id),
                    "email": email,
                    "password_hash": password_hash,
                    "display_name": f"Load Test User {i:03d}",
                    "now": now,
                },
            )
    await engine.dispose()
    print(f"Seeded {COUNT} users")


if __name__ == "__main__":
    asyncio.run(main())
