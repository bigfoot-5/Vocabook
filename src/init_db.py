from sqlalchemy import create_engine
from models import Base

from models import Book, Sentence, Vocabulary 


engine = create_engine("sqlite:///vocabook.db", echo=True)

def init_db():
    print("Creating database tables...")

    Base.metadata.create_all(engine)
    print("Database initialization complete!")

if __name__ == "__main__":
    init_db()
