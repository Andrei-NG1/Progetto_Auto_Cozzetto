import sqlite3

conn = sqlite3.connect('autoscout_clone.db')
cursor = conn.cursor()

# Creazione tabelle pulite
cursor.executescript('''
CREATE TABLE Brands (id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE Models (id INTEGER PRIMARY KEY, brand_id INTEGER, name TEXT);
CREATE TABLE Listings (
    id INTEGER PRIMARY KEY, 
    model_id INTEGER, 
    price REAL, 
    mileage INTEGER, 
    fuel_type TEXT, 
    registration_date TEXT, 
    power_kw INTEGER, 
    description TEXT
);
CREATE TABLE CarImages (id INTEGER PRIMARY KEY, listing_id INTEGER, image_url TEXT);

INSERT INTO Brands (name) VALUES ('Peugeot'), ('Fiat'), ('Audi'), ('BMW'), ('Mercedes');
''')
conn.commit()
conn.close()
print("Database resettato e pronto!")