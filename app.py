from flask import Flask, redirect, url_for, render_template, request, jsonify
from pymongo import MongoClient
import requests
from datetime import datetime, timedelta
import hashlib
import re

import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def home():
    best_products = db.products.find().sort('total_pembelian', -1).limit(3)
    
    products = list(db.products.find({}))
    unique_categories = {}
    for product in products:
        category = product['kategori_produk']
        if category not in unique_categories:
            unique_categories[category] = product

    # Mengubah hasil menjadi daftar
    kategori_produk = list(unique_categories.values())
    
    return render_template('home.html', best_products=best_products, kategori_produk=kategori_produk)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    regex = re.compile(f".*{query}.*", re.IGNORECASE)
    search_results_cursor = db.products.find({"nama_produk": regex})
    search_results = list(search_results_cursor)
    return render_template('search_results.html', products=search_results, query=query)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/products')
def index():
    return render_template("products.html")

@app.route('/all-products')
def all_products():
    return render_template("all-products.html")

@app.route('/detail-product')
def detail_product():
    return render_template("detail-product.html")

@app.route('/purchase')
def purchase():
    return render_template('purchase.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/update-profile')
def update():
    return render_template('update-profile.html')

## admin side
@app.route('/login-admin')
def loginAdmin():
    return render_template('adm-login.html')

@app.route('/register-admin')
def registerAdmin():
    return render_template('adm-register.html')


if __name__ == '__main__':
    app.run(port=5000, debug=True)