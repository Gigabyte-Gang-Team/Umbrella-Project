from flask import Flask, redirect, url_for, render_template, request, jsonify
from pymongo import MongoClient
import requests
from datetime import datetime, timedelta
import hashlib

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

@app.route('/')
def home():
    return render_template('home.html')

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