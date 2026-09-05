import os
import data.db as db
from user.models import *
from stock.models import *
db.sql.SQLModel.metadata.create_all(db.engine)


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from user.views import router as user_routes
from stock.views import router as stock_routes
from misc_views import router as misc_routes


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ['CLIENT_ORIGINS'].split(','),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(user_routes, prefix='/user')
app.include_router(stock_routes, prefix='/stocks')
app.include_router(misc_routes)