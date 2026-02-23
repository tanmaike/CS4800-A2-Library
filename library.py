from flask import Flask, jsonify, render_template, request
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
import sys

env_path = os.path.join(os.path.dirname(__file__), '.env')

load_dotenv(env_path)

app = Flask(__name__)

mongo_uri = os.getenv("MONGO_URI")

if not mongo_uri:
    print("ERROR: MONGO_URI not found in environment variables!")
    sys.exit(1)

app.config["MONGO_URI"] = mongo_uri
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default-secret-key")

try:
    mongo = PyMongo(app)
    
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    sys.exit(1)

@app.route("/")
def library_welcome():
    # Get search parameters from URL
    search_query = request.args.get('q', '').lower()
    search_field = request.args.get('field', 'all')
    min_pages = request.args.get('min_pages', type=int)
    max_pages = request.args.get('max_pages', type=int)
    genre = request.args.get('genre', '')
    rating = request.args.get('rating', '')
    
    # Build MongoDB query
    query = {}
    
    if search_query:
        if search_field == 'title':
            query["name"] = {"$regex": search_query, "$options": "i"}
        elif search_field == 'author':
            query["author"] = {"$regex": search_query, "$options": "i"}
        elif search_field == 'isbn':
            query["isbn"] = {"$regex": search_query, "$options": "i"}
        elif search_field == 'all':
            query["$or"] = [
                {"name": {"$regex": search_query, "$options": "i"}},
                {"author": {"$regex": search_query, "$options": "i"}},
                {"isbn": {"$regex": search_query, "$options": "i"}},
                {"genre": {"$regex": search_query, "$options": "i"}}
            ]
    
    # Apply additional filters
    if min_pages or max_pages:
        query["pages"] = {}
        if min_pages:
            query["pages"]["$gte"] = min_pages
        if max_pages:
            query["pages"]["$lte"] = max_pages
    
    if genre:
        query["genre"] = {"$regex": genre, "$options": "i"}
    
    if rating:
        query["rating"] = {"$regex": rating, "$options": "i"}
    
    # Execute query
    try:
        books = list(mongo.db.books.find(query))
        # Convert ObjectId to string for template
        for book in books:
            book['_id'] = str(book['_id'])
        print(f"Found {len(books)} books")
    except Exception as e:
        print(f"Error executing query: {e}")
        books = []
    
    return render_template('format.html', books=books)

@app.route("/api/books")
def api_books():
    try:
        books = list(mongo.db.books.find({}, {"_id": 0}))
        return jsonify(books)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/addbook", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        try:
            book = {
                "isbn": request.form["isbn"],
                "name": request.form["name"],
                "author": request.form["author"],
                "yearPublished": int(request.form["yearPublished"]),
                "genre": request.form["genre"],
                "rating": request.form["rating"],
                "pages": int(request.form["pages"])
            }
            result = mongo.db.books.insert_one(book)
            if result.inserted_id:
                return render_template("addsuccess.html", book=book)
            else:
                return "Error adding book", 500
        except Exception as e:
            return f"Error: {e}", 500
    
    return render_template("addbook.html")
