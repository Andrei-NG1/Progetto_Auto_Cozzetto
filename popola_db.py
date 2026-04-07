import sqlite3

def inserisci_auto():
    conn = sqlite3.connect('autoscout_clone.db')
    cursor = conn.cursor()

    # Dati degli annunci basati sulle tue immagini
    annunci = [
        {
            "brand": "BMW",
            "model": "120d Sport",
            "price": 12700,
            "mileage": 5000,
            "fuel": "Diesel",
            "date": "02/2017",
            "kw": 190,
            "desc": "BMW 120d Sport in ottime condizioni, km certificati.",
            "img": "/static/uploads/bmw.jpg" # Cambia con il nome file reale
        },
        {
            "brand": "Mercedes",
            "model": "Mercedes-Benz AMG GT",
            "price": 120000,
            "mileage": 0,
            "fuel": "Diesel",
            "date": "03/2026",
            "kw": 840,
            "desc": "Nuovissima AMG GT, potenza estrema e lusso.",
            "img": "/static/uploads/mercedes.jpg" # Cambia con il nome file reale
        }
    ]

    for a in annunci:
        # 1. Trova o inserisci il Brand
        cursor.execute("INSERT OR IGNORE INTO Brands (name) VALUES (?)", (a['brand'],))
        cursor.execute("SELECT id FROM Brands WHERE name = ?", (a['brand'],))
        brand_id = cursor.fetchone()[0]

        # 2. Trova o inserisci il Modello
        cursor.execute("INSERT OR IGNORE INTO Models (brand_id, name) VALUES (?, ?)", (brand_id, a['model']))
        cursor.execute("SELECT id FROM Models WHERE name = ? AND brand_id = ?", (a['model'], brand_id))
        model_id = cursor.fetchone()[0]

        # 3. Inserisci l'annuncio (Listing)
        cursor.execute('''
            INSERT INTO Listings (model_id, price, mileage, fuel_type, registration_date, power_kw, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (model_id, a['price'], a['mileage'], a['fuel'], a['date'], a['kw'], a['desc']))
        
        listing_id = cursor.lastrowid

        # 4. Inserisci l'immagine principale
        cursor.execute("INSERT INTO CarImages (listing_id, image_url) VALUES (?, ?)", (listing_id, a['img']))

    conn.commit()
    conn.close()
    print("✅ I due annunci sono stati inseriti con successo nel database!")

if __name__ == "__main__":
    inserisci_auto()