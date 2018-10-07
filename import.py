""" Import script for books to database"""
import csv
import os
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker



# load dotenv in the base root
load_dotenv(find_dotenv())

if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")


#database

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


with open('books.csv', newline='') as csvfile:
    reader =  csv.reader(csvfile)
    for line in reader:
        print(line)
        db.execute("INSERT INTO books (isbn,author,title,year) VALUES (:isbn,:author,:title,:year)",\
                   {"isbn":line[0],"author":line[1],"title":line[2],"year":line[3]})
        db.commit()