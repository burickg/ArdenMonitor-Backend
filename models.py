from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from db import Base

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String, unique=True, index=True)
    node_name = Column(String)
    last_seen = Column(DateTime)
    status = Column(String, default="unknown")
