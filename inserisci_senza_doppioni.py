import sqlite3

def inserisci_senza_doppioni():
    conn = sqlite3.connect('autoscout_clone.db')
    cursor = conn.cursor()

    # Definiamo i modelli da pulire e reinserire
    modelli_da_gestire = [
        {
            "brand": "Mercedes",
            "model": "EQB 250+ progressive",
            "price": 32900,
            "mileage": 11020,
            "fuel": "Elettrica",
            "date": "04/2025",
            "kw": 95, 
            "desc": "Mercedes EQB full electric, condizioni pari al nuovo.",
            "img_copertina": "/static/uploads/mercedes_eqb_main.jpg"
        },
        {
            "brand": "Audi",
            "model": "S1 SPB 2.0 TFSI quattro",
            "price": 28990,
            "mileage": 59555,
            "fuel": "Benzina",
            "date": "12/2016",
            "kw": 170, 
            "desc": "Audi S1 con pacchetto QUATTRO, 231 CV.",
            "img_copertina": "/static/uploads/audi_s1_main.jpg"
        }
    ]

    print("🧹 Pulizia database in corso...")

    for a in modelli_da_gestire:
        # 1. Eliminiamo prima le immagini collegate ai vecchi annunci di questo modello
        cursor.execute("""
            DELETE FROM CarImages 
            WHERE listing_id IN (
                SELECT l.id FROM Listings l 
                JOIN Models m ON l.model_id = m.id 
                WHERE m.name = ?
            )
        """, (a['model'],))

        # 2. Eliminiamo i vecchi annunci di questo modello
        cursor.execute("""
            DELETE FROM Listings 
            WHERE model_id IN (SELECT id FROM Models WHERE name = ?)
        """, (a['model'],))

        # 3. Ora inseriamo il Brand (se non esiste)
        cursor.execute("INSERT OR IGNORE INTO Brands (name) VALUES (?)", (a['brand'],))
        cursor.execute("SELECT id FROM Brands WHERE name = ?", (a['brand'],))
        brand_id = cursor.fetchone()[0]

        # 4. Inseriamo il Modello (se non esiste)
        cursor.execute("INSERT OR IGNORE INTO Models (brand_id, name) VALUES (?, ?)", (brand_id, a['model']))
        cursor.execute("SELECT id FROM Models WHERE name = ? AND brand_id = ?", (a['model'], brand_id))
        model_id = cursor.fetchone()[0]

        # 5. Inseriamo il nuovo annuncio pulito
        cursor.execute('''
            INSERT INTO Listings (model_id, price, mileage, fuel_type, registration_date, power_kw, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (model_id, a['price'], a['mileage'], a['fuel'], a['date'], a['kw'], a['desc']))
        
        listing_id = cursor.lastrowid

        # 6. Inseriamo l'immagine di copertina corretta
        cursor.execute("INSERT INTO CarImages (listing_id, image_url) VALUES (?, ?)", (listing_id, a['img_copertina']))

    conn.commit()
    conn.close()
    print("✨ Vecchi annunci eliminati e nuovi inseriti correttamente!")

if __name__ == "__main__":
    inserisci_senza_doppioni()