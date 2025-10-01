# Zuerst die notwendigen Bibliotheken importieren
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def scrape_kaufland_offers():
    """
    Diese Funktion steuert einen Browser, um die Kaufland-Angebotsseite zu laden,
    extrahiert alle sichtbaren Angebote und speichert sie in einer JSON-Datei.
    """
    url = "https://filiale.kaufland.de/angebote/uebersicht.html"
    output_filename = 'angebote.json'
    
    print(f"Starte Scraping-Prozess für: {url}")

    try:
        # Playwright wird im 'with'-Block gestartet, damit es sich selbst aufräumt
        with sync_playwright() as p:
            # 1. Browser starten und eine neue Seite öffnen
            browser = p.chromium.launch() # 'headless=True' ist Standard, d.h. unsichtbar
            page = browser.new_page()
            
            # 2. Zur Zielseite navigieren
            print("Navigiere zur Seite...")
            page.goto(url, timeout=60000)  # 60 Sekunden Timeout für das Laden der Seite

            # 3. Warten, bis die Angebotskacheln von JavaScript gerendert wurden
            print("Warte, bis die Angebote erscheinen...")
            # Wir verwenden den Selector '.k-product-tile', den wir im HTML-Code gefunden haben
            page.wait_for_selector('.k-product-tile', timeout=30000) # 30 Sekunden auf Angebote warten
            
            print("Angebote sind geladen. Extrahiere HTML-Inhalt.")
            # 4. Den finalen, vollständigen HTML-Code der Seite auslesen
            html_content = page.content()
            
            # 5. Browser schließen, wir haben was wir brauchen
            browser.close()

        # 6. Den HTML-Code mit BeautifulSoup für die Analyse vorbereiten
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 7. Alle Angebots-Container finden
        offer_tiles = soup.find_all('a', class_='k-product-tile')
        
        if not offer_tiles:
            print("Warnung: Keine Angebote gefunden. Möglicherweise hat sich die Seitenstruktur geändert.")
            return

        # 8. Jedes Angebot durchgehen und die Daten in eine Liste extrahieren
        extracted_offers = []
        for tile in offer_tiles:
            # Hilfsfunktion, um Text sicher zu extrahieren, auch wenn ein Element fehlt
            def get_text(element, selector, class_name):
                found = element.find(selector, class_=class_name)
                return found.get_text(strip=True) if found else None

            # Daten aus der Kachel ziehen
            title = get_text(tile, 'div', 'k-product-tile__title')
            subtitle = get_text(tile, 'div', 'k-product-tile__subtitle')
            price = get_text(tile, 'div', 'k-price-tag__price')
            old_price = get_text(tile, 'span', 'k-price-tag__old-price-line-through')
            unit = get_text(tile, 'div', 'k-product-tile__unit-price')

            # Nur wenn Titel und Preis vorhanden sind, zur Liste hinzufügen
            if title and price:
                extracted_offers.append({
                    'marke': title,
                    'produkt': subtitle or '', # Falls es keinen Untertitel gibt
                    'preis': price,
                    'alter_preis': old_price or 'N/A', # Falls kein alter Preis da ist
                    'einheit': unit or ''
                })

        # 9. Die gesammelten Daten in eine JSON-Datei schreiben
        with open(output_filename, 'w', encoding='utf-8') as f:
            # indent=2 sorgt für eine schön formatierte Datei
            json.dump(extracted_offers, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Erfolgreich! {len(extracted_offers)} Angebote in die Datei '{output_filename}' geschrieben.")

    except PlaywrightTimeoutError:
        print("❌ Fehler: Timeout beim Warten auf die Angebote. Die Seite hat zu lange gebraucht oder der Selector '.k-product-tile' wurde nicht gefunden.")
    except Exception as e:
        print(f"❌ Ein unerwarteter Fehler ist aufgetreten: {e}")

# Hauptteil des Skripts: Führt die Funktion aus, wenn die Datei direkt gestartet wird
if __name__ == "__main__":
    scrape_kaufland_offers()
