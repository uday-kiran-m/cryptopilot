"""Database models for persistent storage."""

from sqlalchemy import create_engine, Column, String, DateTime, Float, Integer, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path

Base = declarative_base()


class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(50), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    msg_metadata = Column(JSON, default={})
    
    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.msg_metadata or {},
        }


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    symbol = Column(String(20), nullable=False)
    action = Column(String(10), nullable=False)
    confidence = Column(Float)
    price = Column(Float)
    factors = Column(JSON)
    explanation = Column(Text)
    outcome = Column(String(20))
    profit_loss = Column(Float)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'symbol': self.symbol,
            'action': self.action,
            'confidence': self.confidence,
            'price': self.price,
            'factors': self.factors,
            'explanation': self.explanation,
            'outcome': self.outcome,
            'profit_loss': self.profit_loss,
        }


class CachedNews(Base):
    __tablename__ = 'cached_news'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000))
    source = Column(String(100))
    published = Column(DateTime)
    sentiment_label = Column(String(20))
    sentiment_score = Column(Float)
    symbol = Column(String(20))
    cached_at = Column(DateTime, default=datetime.now)


class Database:
    _instance = None
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if db_path is None:
                db_path = Path(__file__).parent.parent.parent.parent / 'data' / 'cryptopilot.db'
            cls._instance.engine = create_engine(f'sqlite:///{db_path}')
            cls._instance.SessionLocal = sessionmaker(bind=cls._instance.engine)
            Base.metadata.create_all(cls._instance.engine)
        return cls._instance
    
    def get_session(self):
        return self.SessionLocal()
    
    def save_chat_message(self, thread_id: str, role: str, content: str, metadata: dict = None):
        session = self.get_session()
        try:
            msg = ChatMessage(
                thread_id=thread_id,
                role=role,
                content=content,
                msg_metadata=metadata or {}
            )
            session.add(msg)
            session.commit()
            return msg.id
        finally:
            session.close()
    
    def get_chat_history(self, thread_id: str = None, limit: int = 100):
        session = self.get_session()
        try:
            query = session.query(ChatMessage)
            if thread_id:
                query = query.filter(ChatMessage.thread_id == thread_id)
            return query.order_by(ChatMessage.timestamp.desc()).limit(limit).all()
        finally:
            session.close()
    
    def save_audit_log(self, symbol: str, action: str, confidence: float, price: float,
                       factors: dict, explanation: str, outcome: str = None, profit_loss: float = None):
        session = self.get_session()
        try:
            log = AuditLog(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price=price,
                factors=factors,
                explanation=explanation,
                outcome=outcome,
                profit_loss=profit_loss
            )
            session.add(log)
            session.commit()
            return log.id
        finally:
            session.close()
    
    def get_audit_logs(self, symbol: str = None, start_date: datetime = None,
                        end_date: datetime = None, limit: int = 100):
        session = self.get_session()
        try:
            query = session.query(AuditLog)
            if symbol:
                query = query.filter(AuditLog.symbol == symbol)
            if start_date:
                query = query.filter(AuditLog.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditLog.timestamp <= end_date)
            return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        finally:
            session.close()
    
    def update_audit_outcome(self, log_id: int, outcome: str, profit_loss: float = None):
        session = self.get_session()
        try:
            log = session.query(AuditLog).filter(AuditLog.id == log_id).first()
            if log:
                log.outcome = outcome
                log.profit_loss = profit_loss
                session.commit()
        finally:
            session.close()
