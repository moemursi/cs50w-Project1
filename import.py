import csv
import os
from dotenv import load_dotenv,find_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

load_dotenv(find_dotenv())


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")


engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))




def main():
    f = open("books.csv")
    reader = csv.reader(f)
    next(reader, None)
    counter = 0
    for isbn, title , author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author,theyear) VALUES (:isbn,:title,:author,:theyear)",
                    {"isbn": isbn, "title": title, "author": author, "theyear": year})
        counter+=1
        print(f"Added {counter} successfully.")


    db.commit()

if __name__ == "__main__":
    main()
