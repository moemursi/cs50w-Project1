import json
import os
from functools import wraps
from flask import Flask, session, request, g, redirect, url_for, render_template
from flask_session import Session
from passlib.hash import pbkdf2_sha256
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

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
def getGoodreads(id,book_info):
    response  = {}
    request_url = "https://www.goodreads.com/book/review_counts.json"
    res = request.get(request_url,params={"key":os.getenv('GOODREADS_KEY'),"isbns":book_info[1]})
    json_data = res.json()
    response['score']  = json_data['books'][0]['average_rating']
    response['review_qty'] = json_data['books'][0]['work_review_count']

    return response

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
        return render_template("index.html")
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
        return "search.html"
@app.route("/logout")
def logout():
    """Logout user"""
    # remover username from the session
    session.pop('user',None)
    session.pop('logged_in',None)

    return redirect(url_for(index))
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
        result  = db.execute("SELECT * FROM books WHERE ")

@app.route("/book/<isbn>",methods=['GET'])
def book(isbn):

    response = {}
    data  = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    if not data:
        return "No books found"
    response["isbn"] = data[1]
    response["author"] = data[2]
    response["title"] = data[3]
    response["year"]= data[4]

    return  json.dumps(response, ensure_ascii=False)