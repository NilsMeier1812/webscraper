import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def extract_offers_from_html(html_content, date_str, seen_ids):
    """
    Hilfsfunktion: Extrahiert alle Angebote aus einem gegebenen HTML-Code,
    prüft auf Duplikate und fügt das Gültigkeitsdatum sowie den K-Card-Preis hinzu.
    """
    newly_found_offers = []
    soup = BeautifulSoup(html_content, 'lxml')
    offer_tiles = soup.find_all('a', class_='k-product-tile')

    for tile in offer_tiles:
        image_tag = tile.find('img', class_='k-product-tile__main-image')
        if not image_tag or not image_tag.get('src'):
            continue
        try:
            offer_id = image_tag['src'].split('/')[-1].split('?')[0]
        except (IndexError, AttributeError):
            continue

        if offer_id in seen_ids:
            continue
        seen_ids.add(offer_id)

        title = tile.find('div', class_='k-product-tile__title').get_text(strip=True)
        price_tag = tile.find('div', class_='k-price-tag__price')
        price = price_tag.get_text(strip=True) if price_tag else 'N/A'

        if title and price:
            subtitle = tile.find('div', class_='k-product-tile__subtitle').get_text(strip=True)
            old_price_tag = tile.find('span', class_='k-price-tag__old-price-line-through')
            unit_tag = tile.find('div', class_='k-product-tile__unit-price')

            # --- NEU: Suche nach dem K-Card Preis ---
            kcard_preis = 'N/A'  # Standardwert, falls kein K-Card Preis vorhanden
            kcard_container = tile.find('div', class_='k-product-tile__pricetags-kcard')
            if kcard_container:
                kcard_price_tag = kcard_container.find('div', class_='k-price-tag__price')
                if kcard_price_tag:
                    kcard_preis = kcard_price_tag.get_text(strip=True)
            # --- ENDE NEUER TEIL ---

            newly_found_offers.append({
                'gueltig_ab': date_str,
                'marke': title,
                'produkt': subtitle or '',
                'preis': price,
                'kcard_preis': kcard_preis, # NEUES FELD
                'alter_preis': old_price_tag.get_text(strip=True) if old_price_tag else 'N/A',
                'einheit': unit_tag.get_text(strip=True) if unit_tag else ''
            })
            
    return newly_found_offers

def click_all_show_more_buttons(page):
    """Hilfsfunktion, die alle 'Weitere Angebote anzeigen'-Buttons klickt."""
    show_more_selector = 'span:has-text("Weitere Angebote anzeigen")'
    while page.locator(show_more_selector).count() > 0:
        print(f"  -> 'Weitere Angebote'-Button gefunden. Klicke...")
        try:
            page.locator(show_more_selector).first.click(timeout=5000)
            page.wait_for_timeout(2000)
        except PlaywrightTimeoutError:
            print("  -> Button war nicht mehr klickbar, wahrscheinlich verschwunden. Mache weiter.")
            break

def scrape_all_kaufland_offers():
    """
    Steuert einen Browser, akzeptiert Cookies, klickt sich durch alle Tage 
    und "mehr anzeigen"-Buttons, sammelt alle einzigartigen Angebote 
    und speichert sie in einer JSON-Datei.
    """
    url = "https://filiale.kaufland.de/angebote/uebersicht.html"
    output_filename = 'angebote.json'
    
    all_unique_offers = []
    seen_offer_ids = set()

    print(f"Starte Scraping-Prozess für: {url}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, timeout=90000)

            try:
                print("Suche nach Cookie-Banner und akzeptiere ihn...")
                accept_button_selector = '#onetrust-accept-btn-handler'
                page.locator(accept_button_selector).click(timeout=10000)
                print("Cookie-Banner akzeptiert.")
                page.wait_for_timeout(2000)
            except PlaywrightTimeoutError:
                print("Cookie-Banner nicht gefunden oder bereits akzeptiert. Mache weiter.")

            print("\n--- Scrape Angebote für 'Heute' ---")
            click_all_show_more_buttons(page)
            html_today = page.content()
            offers_today = extract_offers_from_html(html_today, "Heute", seen_offer_ids)
            all_unique_offers.extend(offers_today)
            print(f"  -> {len(offers_today)} neue Angebote für 'Heute' gefunden.")

            date_buttons = page.locator('.k-navigation-bubble:not([disabled])').all()
            
            future_dates = []
            for button in date_buttons:
                button_id = button.get_attribute('id')
                if button_id and "20" in button_id:
                    future_dates.append(button_id)

            for date in future_dates:
                print(f"\n--- Scrape Angebote für '{date}' ---")
                selector_for_date = f'[id="{date}"]'
                page.locator(selector_for_date).click()
                page.wait_for_load_state('networkidle', timeout=30000)
                
                click_all_show_more_buttons(page)
                
                html_future = page.content()
                offers_future = extract_offers_from_html(html_future, date, seen_offer_ids)
                all_unique_offers.extend(offers_future)
                print(f"  -> {len(offers_future)} neue Angebote für '{date}' gefunden.")

            browser.close()

        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_unique_offers, f, ensure_ascii=False, indent=2)
            
        print(f"\n✅ Erfolgreich! Insgesamt {len(all_unique_offers)} einzigartige Angebote in '{output_filename}' geschrieben.")

    except Exception as e:
        print(f"❌ Ein unerwarteter Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
    scrape_all_kaufland_offers()
