import uvicorn
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import analysis, auth, transactions, users
from app.db.sessions import create_db_and_tables, get_async_session

app = FastAPI()

app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])


@app.on_event("startup")
async def on_startup(session: AsyncSession = Depends(get_async_session)):
    await create_db_and_tables()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7999, reload=True)
