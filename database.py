import streamlit as st
import pymongo
import hashlib
from datetime import datetime
from geopy.geocoders import Nominatim

@st.cache_resource
def get_db():
    uri = st.secrets["MONGO_URI"]
    client = pymongo.MongoClient(uri)
    return client['sistema_comercial']

db = get_db()
users_col = db['usuarios']
visits_col = db['atendimentos']
metas_col = db['metas']

def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="rovema_app")
        location = geolocator.reverse((lat, lon), exactly_one=True, timeout=5)
        return location.address if location else "Endereço não identificado"
    except:
        return "Erro ao obter endereço"

def init_admin():
    admin_email = "luiz.bicalho@rovemabank.com.br"
    if not users_col.find_one({"email": admin_email}):
        users_col.insert_one({
            "nome": "Luiz Bicalho",
            "email": admin_email,
            "senha": hash_pw("123456"),
            "role": "admin",
            "ativo": True
        })
