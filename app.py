import os
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, render_template, request
from pymongo import MongoClient
from bson import ObjectId
from werkzeug.utils import secure_filename

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

MONGODB_URI = os.environ.get("MONGODB_URI")
DB_NAME =  os.environ.get("DB_NAME")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]


app = Flask(__name__)

@app.route('/', methods=["GET", "POST"])
def home():
    fruit = list(db.fruits.find({}))
    return render_template('dashboard.html', fruit=fruit)

@app.route('/fruit', methods=["GET"])
def fruit():
    fruit = list(db.fruits.find({}))
    return render_template('fruit.html', fruit=fruit)

@app.route('/addFruit', methods=["GET", "POST"])
def addFruit():
    if request.method == 'POST':
        nama = request.form['nama']
        harga = request.form['harga']
        deskripsi = request.form['deskripsi']
        gambar = request.files['image']
        
        if gambar:
            nama_file_asli = gambar.filename
            nama_file_gambar = secure_filename(nama_file_asli)
            file_path = f'./static/assets/imgFruit/{nama_file_gambar}'
            gambar.save(file_path)
        else:
            nama_file_gambar = None
            
        doc = {
            'nama': nama,
            'harga': harga,
            'gambar': nama_file_gambar,
            'deskripsi': deskripsi
        }
        
        db.fruits.insert_one(doc)
        return redirect(url_for("fruit"))
        
    return render_template('AddFruit.html')



@app.route('/editFruit/<string:_id>', methods=["GET", "POST"])
def editFruit(_id):
    if request.method == 'POST':
        nama = request.form['nama']
        harga = request.form['harga']
        deskripsi = request.form['deskripsi']
        gambar = request.files['image']
        
        doc = {
            'nama': nama,
            'harga': harga,
            'deskripsi': deskripsi  
        }
        if gambar:
            nama_file_asli = gambar.filename
            nama_file_gambar = secure_filename(nama_file_asli)
            file_path = f'./static/assets/imgFruit/{nama_file_gambar}'
            gambar.save(file_path)
            doc['gambar'] = nama_file_gambar
        
        db.fruits.update_one({'_id': ObjectId(_id)}, {'$set': doc})
        return redirect(url_for('fruit'))
    
    data = db.fruits.find_one({'_id': ObjectId(_id)})
    return render_template('EditFruit.html', data=data)


@app.route('/deleteFruit/<string:_id>', methods=["GET", "POST"])
def deleteFruit(_id):
    db.fruits.delete_one({'_id': ObjectId(_id)})
    return redirect(url_for('fruit'))


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)