"""清理 MFI 重复数据 — 同名保留最早记录，更新客户关联到保留的 ID"""
import asyncio
from sqlalchemy import select, func, update

from app.database import AsyncSessionLocal
from app.models import Mfi, Customer


async def dedup_mfis():
    async with AsyncSessionLocal() as db:
        # 查找重复名称
        dupes_result = await db.execute(
            select(Mfi.name, func.count().label("cnt"))
            .group_by(Mfi.name)
            .having(func.count() > 1)
        )
        dup_names = [row[0] for row in dupes_result.all()]

        if not dup_names:
            print("No duplicate MFIs found.")
            return

        for name in dup_names:
            rows_result = await db.execute(
                select(Mfi).where(Mfi.name == name).order_by(Mfi.created_at)
            )
            rows = rows_result.scalars().all()
            keep = rows[0]  # 保留最早的
            for dup in rows[1:]:
                # 将引用该重复 MFI 的客户重新指向保留的 MFI
                await db.execute(
                    update(Customer).where(Customer.mfi_id == dup.id).values(mfi_id=keep.id)
                )
                await db.delete(dup)
                print(f"Dedup: {name} — deleted {dup.id}, kept {keep.id}, reassigned customers")

        await db.commit()
        print(f"Dedup complete: {len(dup_names)} duplicates resolved.")


if __name__ == "__main__":
    asyncio.run(dedup_mfis())
