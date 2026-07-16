"""创建默认租户和管理员用户，用于首次登录。"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from pydantic import SecretStr
from policymind.infrastructure.postgres.base import Base
from policymind.auth.models import Tenant, User
from policymind.auth.security import hash_password

async def seed():
    engine = create_async_engine(
        "postgresql+asyncpg://policymind:policymind@localhost:5432/policymind"
    )
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession)
    async with factory() as s:
        t = Tenant(name="默认租户", slug="default")
        s.add(t)
        await s.flush()

        u = User(
            tenant_id=t.id,
            username="admin",
            password_hash=hash_password(SecretStr("admin123")),
            role="employee",
            access_level=1,
            is_active=True,
        )
        s.add(u)
        await s.commit()
        print("种子数据创建完成！")
        print("  租户: default")
        print("  用户: admin")
        print("  密码: admin123")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
