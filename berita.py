import os
from os.path import join, dirname
from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient
from datetime import datetime
from app import app

# connection_string = 'mongodb+srv://richard:sparta@cluster0.rgniilv.mongodb.net/?retryWrites=true&w=majority'
# client = MongoClient(connection_string)

password = 'sparta'
cxn_str = f'mongodb+srv://richard:{password}@cluster0.rgniilv.mongodb.net/?retryWrites=true&w=majority'
client = MongoClient(cxn_str)
db = client.berita

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'


@app.route('/berita', methods=['GET'])
def berita():
    berita = list(db.berita.find({},{'_id':False}))
    return jsonify({'berita': berita})

@app.route('/berita', methods=['POST'])
def save_diary():
    title_receive = request.form.get('title_give')
    content_receive = request.form.get('content_give')
    
    today = datetime.now()
    mytime = today.strftime("%Y-%m-%d-%H-%M-%S")
    
    file = request.files['file_give']
    extension = file.filename.split('.')[-1]
    filename = f'static/post-{mytime}.{extension}'
    file.save(filename)
    
    profile = request.files['profile_give']
    extension = profile.filename.split('.')[-1]
    profilename = f'static/-{mytime}.{extension}'
    profile.save(profilename)
    
    time = today.strftime('%Y.%m.%d')
    
    doc = {
        'file': filename,
        'profile': profilename,
        'title': title_receive,
        'content': content_receive,
        'time' : time,
    }
    db.diary.insert_one(doc)
    return jsonify({'message': 'data was saved'})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000,debug=True)