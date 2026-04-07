import sqlite3

def inserisci_auto_scelte():
    conn = sqlite3.connect('autoscout_clone.db')
    cursor = conn.cursor()

    # Dati estratti dalle tue immagini
    annunci = [
        {
            "brand": "Mercedes",
            "model": "EQB 250+ progressive",
            "price": 32900,
            "mileage": 11020,
            "fuel": "Elettrica",
            "date": "04/2025",
            "kw": 95, # 129 CV corrispondono a circa 95 kW
            "desc": "Mercedes EQB full electric, IVA deducibile, condizioni pari al nuovo.",
            "img": "/static/uploads/mercedes_eqb.jpg"
        },
        {
            "brand": "Audi",
            "model": "S1 SPB 2.0 TFSI quattro",
            "price": 28990,
            "mileage": 59555,
            "fuel": "Benzina",
            "date": "12/2016",
            "kw": 170, # 231 CV corrispondono a 170 kW come da foto
            "desc": "Audi S1 con pacchetto QUATTRO-BOSE, assetto sportivo.",
            "img": "/static/uploads/audi_s1.jpg"
        }
    ]

    for a in annunci:
        # 1. Inserimento Brand
        cursor.execute("INSERT OR IGNORE INTO Brands (name) VALUES (?)", (a['brand'],))
        cursor.execute("SELECT id FROM Brands WHERE name = ?", (a['brand'],))
        brand_id = cursor.fetchone()[0]

        # 2. Inserimento Modello
        cursor.execute("INSERT OR IGNORE INTO Models (brand_id, name) VALUES (?, ?)", (brand_id, a['model']))
        cursor.execute("SELECT id FROM Models WHERE name = ? AND brand_id = ?", (a['model'], brand_id))
        model_id = cursor.fetchone()[0]

        # 3. Inserimento Annuncio
        cursor.execute('''
            INSERT INTO Listings (model_id, price, mileage, fuel_type, registration_date, power_kw, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (model_id, a['price'], a['mileage'], a['fuel'], a['date'], a['kw'], a['desc']))
        
        listing_id = cursor.lastrowid

        # 4. Inserimento Immagine
        cursor.execute("INSERT INTO CarImages (listing_id, image_url) VALUES (?, ?)", (listing_id, a['img']))

    conn.commit()
    conn.close()
    print("✅ Mercedes EQB e Audi S1 inserite con successo!")

if __name__ == "__main__":
    inserisci_auto_scelte()