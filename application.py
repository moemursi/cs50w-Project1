import json
import os
import requests
from functools import wraps
from flask import Flask, session, request, g, redirect, url_for, render_template
from flask_session import Session
from passlib.hash import pbkdf2_sha256
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from dotenv import load_dotenv,find_dotenv



load_dotenv(find_dotenv())


app = Flask(__name__)
DEBUG = True


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.before_request
def before_request():
    if 'logged_in' in session:
        g.user = session["user"]
    else:
        g.user = None
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/registeration")
def registeration():
    """registeration method"""

    return render_template("registeration.html")

@app.route("/register_user",methods=['POST'])
def register_user():
    """register user into the database"""
    username = request.form.get("username")
    password = request.form.get("password")
    check_username = db.execute("SELECT * FROM users WHERE username= :username",{"username":username}).fetchone()
    if check_username is None:
        hash = pbkdf2_sha256.encrypt(password,rounds=200000,salt_size=16) #hash the password
        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",{"username":username,"password":hash})
        db.commit()
        return render_template("search.html")
    else:
        return "Sorry Pal !!! username is already taken"

@app.route("/login")
def login():
    return render_template('login.html')
@app.route("/login_user",methods=['POST'])
def login_user():

     username = str(request.form.get("username"))
     password = str(request.form.get("password"))
     user_data = db.execute("SELECT password FROM users WHERE username = :username",{"username":username}).fetchone()
     if user_data is None:
        return "Sorry Pal , This user Doesn't exist !!! "
     if pbkdf2_sha256.verify(password,user_data.password):
        session["user"] = username
        session["logged_in"] = True
        return render_template("search.html")
     else:
         return "wrong info entered"
@app.route("/logout")
def logout():
    """Logout user"""
    # remover username from the session
    session.pop('user',None)
    session.pop('logged_in',None)

    return redirect(url_for('index'))
@app.route("/search/",methods=['GET','POST'])
@login_required
def search():
    """search engine"""
    if request.method == 'POST':
        search = str(request.form.get("search"))
        if search is '' :
            print(search)
            return render_template("search.html")

        search_input = '%' + str.lower(search) + '%'

        message = "No Results Found "
        result = db.execute("SELECT * FROM books WHERE isbn LIKE :search \
        			OR LOWER(author) LIKE :search \
        			OR LOWER(title) LIKE :search \
        			OR theyear LIKE :search", \
                            {"search": search_input}).fetchall()

        if not result:
            return render_template("search.html" , message=message)
        return render_template("search.html" , result=result)
    else:
        return render_template('search.html')
def getGoodreads(id,book_info):
    response  = {}
    request_url = "https://www.goodreads.com/book/review_counts.json"
    res = requests.get(request_url,params={"key":os.getenv('GOODREADS_KEY'),"isbns":book_info[1]})
    json_data = res.json()
    response['score']  = json_data['books'][0]['average_rating']
    response['review_qty'] = json_data['books'][0]['work_reviews_count']

    return response

@app.route('/search/<id>')
@login_required
def search_id(id):
    book_id = int(id)
    book_info = db.execute("SELECT * FROM books WHERE id = :id", {"id": book_id}).fetchone()

    goodreads_data = getGoodreads(id,book_info)
    review_list = db.execute("SELECT * FROM reviews WHERE review_id = :review_id",{"review_id": book_id}).fetchall()
    return render_template("book.html", book_info=book_info , review_list = review_list , goodreads = goodreads_data)


@app.route("/review/<id>", methods=['POST'])
def review(id):
    """
    Handles user review submission and display, and also manages
    Goodreads API for fetching average rating and number of reviews
    for books.
    """
    user_id = db.execute("SELECT id FROM users WHERE username = :username", \
                         {"username": session["user"]}).fetchone()

    user_id = int(user_id[0])
    book_id = int(id)
    message = None

    book_info = db.execute("SELECT * FROM books WHERE id = :id", \
                           {"id": book_id}).fetchone()

    goodreads_data = getGoodreads(id, book_info)

    if not db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND review_id = :review_id", \
                      {"user_id": user_id, "review_id": book_id}).fetchone():
        rating = request.form.get("review")
        comment = request.form.get("comment")

        db.execute("INSERT INTO reviews (rating, review_id, text, user_id) VALUES (:rating, :book_id, :comment, :user_id)", \
                   {"rating": rating, "book_id": book_id, "comment": comment, "user_id": user_id})
        db.commit()
    elif db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND review_id = :review_id", \
                      {"user_id": user_id, "review_id": book_id}).fetchone():

        message = "You already Submitted  a review"


    index = 0
    rows = []

    review_list = db.execute("SELECT * FROM reviews WHERE review_id = :review_id", \
                             {"review_id": book_id}).fetchall()

    for entry in review_list:
        row = dict(rating=review_list[index]["rating"],
                   comment=review_list[index]["text"])
        rows.append(row)
        index += 1

    return render_template("book.html", book_info=book_info, review_list=review_list, goodreads=goodreads_data,rows=rows,message=message)

    return redirect(url_for('search', id=book_id))


@app.route("/api/<isbn>", methods=['GET'])
def api(isbn):

    response = {}

    data = db.execute("SELECT * FROM books WHERE isbn = :isbn", \
                      {"isbn": isbn}).fetchone()

    if not data:
        abort(404)

    response["isbn"] = data[1]
    response["author"] = data[2]
    response["title"] = data[3]
    response["year"] = data[4]

    return json.dumps(response, ensure_ascii=False)