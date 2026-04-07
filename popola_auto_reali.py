import sqlite3

def inserisci_auto_reali():
    conn = sqlite3.connect('autoscout_clone.db')
    cursor = conn.cursor()

    # Dati estratti fedelmente dalla tua immagine
    annunci = [
        {
            "brand": "BMW",
            "model": "X1 F48 2019 sdrive18d",
            "price": 18500,
            "mileage": 145000,
            "fuel": "Diesel",
            "date": "12/2020",
            "kw": 110, # Valore standard per 18d
            "desc": "BMW X1 in ottime condizioni, Prezzo ribassato.",
            "img": "/static/uploads/bmw_x1.jpg"
        },
        {
            "brand": "Lamborghini",
            "model": "Urus 4.0 V8 PHEV",
            "price": 329000,
            "mileage": 1361,
            "fuel": "Elettrica/Benzina",
            "date": "05/2025",
            "kw": 588, # Potenza di sistema PHEV
            "desc": "Lamborghini Urus plug-in hybrid, come nuova.",
            "img": "/static/uploads/urus.jpg"
        },
        {
            "brand": "CUPRA",
            "model": "Leon 1.5 Hybrid",
            "price": 27790,
            "mileage": 13790,
            "fuel": "Elettrica/Benzina",
            "date": "03/2025",
            "kw": 110,
            "desc": "CUPRA Leon ibrida, ottime prestazioni e consumi ridotti.",
            "img": "/static/uploads/cupra.jpg"
        },
        {
            "brand": "Alfa Romeo",
            "model": "Tonale 1.6 JTD",
            "price": 38900,
            "mileage": 10,
            "fuel": "Diesel",
            "date": "04/2024",
            "kw": 96,
            "desc": "Alfa Romeo Tonale nuova, pronta consegna.",
            "img": "/static/uploads/tonale.jpg"
        }
    ]

    for a in annunci:
        # Gestione Brand
        cursor.execute("INSERT OR IGNORE INTO Brands (name) VALUES (?)", (a['brand'],))
        cursor.execute("SELECT id FROM Brands WHERE name = ?", (a['brand'],))
        brand_id = cursor.fetchone()[0]

        # Gestione Modello
        cursor.execute("INSERT OR IGNORE INTO Models (brand_id, name) VALUES (?, ?)", (brand_id, a['model']))
        cursor.execute("SELECT id FROM Models WHERE name = ? AND brand_id = ?", (a['model'], brand_id))
        model_id = cursor.fetchone()[0]

        # Inserimento Annuncio
        cursor.execute('''
            INSERT INTO Listings (model_id, price, mileage, fuel_type, registration_date, power_kw, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (model_id, a['price'], a['mileage'], a['fuel'], a['date'], a['kw'], a['desc']))
        
        listing_id = cursor.lastrowid

        # Inserimento Immagine
        cursor.execute("INSERT INTO CarImages (listing_id, image_url) VALUES (?, ?)", (listing_id, a['img']))

    conn.commit()
    conn.close()
    print(f"✅ Inseriti {len(annunci)} nuovi annunci reali!")

if __name__ == "__main__":
    inserisci_auto_reali()