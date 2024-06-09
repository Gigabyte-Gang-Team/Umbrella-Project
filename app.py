from flask import Flask, redirect, url_for, render_template, request, jsonify
from pymongo import MongoClient
import requests
from datetime import datetime, timedelta
import hashlib
import re
from bson import ObjectId
from bson.objectid import ObjectId, InvalidId

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

# Products, Detail & All Start

@app.route('/products')
def products():
    product = list(db.products.find({}).sort("created_at", -1))

    best_selling_products = db.products.find().sort("total_pembelian", -1)

    return render_template('products.html', product=product, best_selling_products=best_selling_products)

@app.route('/all-products')
def all_products():
    sort_option = request.args.get('sort')
    filter_category = request.args.get('filter')

    query = {}

    # Ambil semua produk yang sesuai dengan kategori
    if filter_category:
        products = list(db.products.find({"kategori_produk": filter_category}))
        query['kategori_produk'] = filter_category    
    else:
        products = list(db.products.find({}))

    sort_criteria = [('created_at', -1)]  # Default sorting is by recent products
    if sort_option == 'best_selling':
        sort_criteria = [('total_pembelian', -1)]

    # Ambil produk dari database dengan filter dan urutkan sesuai kriteria
    products = list(db.products.find(query).sort(sort_criteria))

    return render_template('all-products.html', products=products)

@app.route('/detail-product/<product_id>')
def detail_product(product_id):
    product = db.products.find_one({"_id": ObjectId(product_id)})
    if product:
        product['_id'] = str(product['_id'])  # Mengubah ObjectId menjadi string untuk Jinja template
    else:
        return "Product not found", 404
    
    if product and "ulasan_produk" in product:
        ulasan_produk = product["ulasan_produk"]
        ulasan_count = len(ulasan_produk)
        total_rating = 0

        for ulasan in ulasan_produk:
            try:
                # Pastikan ulasan[2] adalah angka
                rating = int(ulasan[2])
                total_rating += rating
            except ValueError:
                print(f"Invalid rating value: {ulasan[2]}")

        average_rating = total_rating / ulasan_count if ulasan_count > 0 else 0
    else:
        ulasan_produk = []
        ulasan_count = 0
        average_rating = 0

    # Tambahkan average_rating ke data product
    product["average_rating"] = average_rating
    product["ulasan_count"] = ulasan_count

    # Untuk Sorting recent review dipaling atas
    product["ulasan_produk"] = product["ulasan_produk"][::-1]

    # Tambahkan query untuk mengurutkan berdasarkan total pembelian
    best_selling_products = db.products.find().sort("total_pembelian", -1)

    return render_template('detail-product.html', product=product, best_selling_products=best_selling_products)
    
# Products, Detail & All End

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
