from sqlalchemy import create_engine
import os
engine = create_engine(os.getenv("DATABASE_URL"))
conn = engine.connect()
print("Connected!", conn)
