from flask import Flask, redirect, url_for, render_template, request
from pymongo import MongoClient
from bson import ObjectId
from bson.objectid import ObjectId, InvalidId
from datetime import datetime

app = Flask(__name__)

MONGODB_CONNECTION_STRING = "mongodb+srv://test:sparta@cluster0.rybvjj7.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGODB_CONNECTION_STRING)
db = client.db_umbrella_project

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


if __name__ == '__main__':
    app.run(port=5000, debug=True)
