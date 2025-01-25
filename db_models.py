

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=True, unique=True)
    status = Column(String, nullable=True)
    created = Column(DateTime, nullable=True)

    user_balance = relationship("UserBalance", back_populates="owner")


class UserBalance(Base):
    __tablename__ = "user_balance"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    currency = Column(String, nullable=True)
    amount = Column(Numeric, nullable=True)
    created = Column(DateTime, nullable=True)
    UniqueConstraint('user_id', 'currency', name='user_balance_user_currency_unique')

    owner = relationship("User", back_populates="user_balance")


class Transaction(Base):
    __tablename__ = "transaction"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    currency = Column(String, nullable=True)
    amount = Column(Numeric, nullable=True)
    status = Column(String, nullable=True)
    created = Column(DateTime, nullable=True)

