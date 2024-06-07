from flask import Flask, redirect, url_for, render_template, request
from pymongo import MongoClient

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

@app.route('/purchase')
def purchase():
    return render_template('purchase.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')
@app.route('/products')
def index():
    return render_template("products.html")

@app.route('/all-products')
def all_products():
    return render_template("all-products.html")

@app.route('/detail-product')
def detail_product():
    return render_template("detail-product.html")


if __name__ == '__main__':
    app.run(port=5000, debug=True)
