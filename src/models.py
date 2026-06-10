from typing import List, Optional
from sqlalchemy import ForeignKey, String, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[Optional[str]] = mapped_column(String(255))


    sentences: Mapped[List["Sentence"]] = relationship(back_populates="book", cascade="all, delete-orphan")


class Sentence(Base):
    __tablename__ = "sentences"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    

    sentence_text: Mapped[str] = mapped_column(Text)
    

    order_index: Mapped[int] = mapped_column(Integer, index=True)


    book: Mapped["Book"] = relationship(back_populates="sentences")


class Vocabulary(Base):
    __tablename__ = "vocabulary"

    id: Mapped[int] = mapped_column(primary_key=True)
    

    word: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    translation: Mapped[Optional[str]] = mapped_column(String(255))
    definition: Mapped[Optional[str]] = mapped_column(Text)
