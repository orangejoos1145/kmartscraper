import requests
import csv
import time
import re
from urllib.parse import quote_plus

# --- CONFIGURATION ---
API_KEY = "key_EyiTrcbGw7IFH3wR" 

# Add your Category IDs here
CATEGORIES = [
    {"name": "Clearance", "id": "f0bd591d50912ba015ed5fb814c42bbb"},
    # {"name": "Mens", "id": "PASTE_ID_HERE"}, 
]

def scrape_entire_catalogue():
    all_products = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.kmart.co.nz/"
    }

    for cat in CATEGORIES:
        cat_name = cat['name']
        cat_id = cat['id']
        print(f"\n=== STARTING CATEGORY: {cat_name} ===")
        
        base_url = f"https://ac.cnstrc.com/browse/group_id/{cat_id}"
        page = 1
        per_page = 200
        
        while True:
            params = {
                "c": "ciojs-client-2.71.1",
                "key": API_KEY,
                "page": page,
                "num_results_per_page": per_page,
                "sort_by": "relevance",
                "sort_order": "descending",
                "_dt": int(time.time() * 1000)
            }

            try:
                response = requests.get(base_url, headers=headers, params=params)
                data = response.json()
                results = data.get('response', {}).get('results', [])
                
                if not results:
                    break
                    
                print(f"  [+] Page {page}: Found {len(results)} items...")
                
                for item in results:
                    try:
                        # 1. BASE DATA
                        parent_data = item.get('data', {})
                        parent_id = parent_data.get('id', 'N/A')
                        parent_name = item.get('value', 'Unknown Name')
                        
                        raw_url = parent_data.get('url', f"/product/{parent_id}/") 
                        if not raw_url.startswith('/'): raw_url = '/' + raw_url
                        parent_full_url = f"https://www.kmart.co.nz{raw_url}"

                        variations = item.get('variations', [])
                        
                        if variations:
                            process_variants(parent_id, parent_name, parent_data, parent_full_url, variations, cat_name, all_products)
                        else:
                            process_single_item(parent_id, parent_name, parent_data, parent_full_url, cat_name, all_products)
                            
                    except Exception as e:
                        continue

                page += 1
                time.sleep(0.5)

            except Exception as e:
                print(f"  [!] Error: {e}")
                break
    
    # SAVE
    filename = 'kmart_full_catalogue.csv'
    if all_products:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter='|')
            writer.writerow(['id', 'product name', 'variant label', 'Original price', 'discounted price', 'disc%', 'category', 'product link'])
            writer.writerows(all_products)
        print(f"\nSUCCESS! Scraped {len(all_products)} items.")
        print(f"Saved to {filename}")

def extract_price_from_text(text):
    if not text: return None
    clean_text = text.replace(',', '') 
    matches = re.findall(r"[\d]+\.?[\d]*", clean_text)
    if matches:
        try:
            val = float(matches[0])
            if val > 0: return val
        except: pass
    return None

def process_single_item(p_id, name, data, full_url, cat, results_list):
    try: curr_price = float(data.get('price', 0))
    except: curr_price = 0.0
    
    orig_price = curr_price
    
    extracted = extract_price_from_text(data.get('SavePrice', ''))
    if extracted and extracted > curr_price:
        orig_price = extracted
    else:
        for field in ['was_price', 'list_price', 'regular_price']:
            try:
                val = float(data.get(field, 0))
                if val > orig_price: orig_price = val
            except: pass

    # Empty string for variant label on single items
    add_row(p_id, name, "", orig_price, curr_price, cat, full_url, results_list)

def process_variants(parent_id, parent_name, parent_data, parent_url_base, variations, cat, results_list):
    try: parent_price = float(parent_data.get('price', 0))
    except: parent_price = 0.0
    
    parent_save_text = parent_data.get('SavePrice', '')
    parent_was_price = extract_price_from_text(parent_save_text)

    max_variant_price = parent_price
    for v in variations:
        try:
            vp = float(v.get('data', {}).get('price', 0))
            if vp > max_variant_price: max_variant_price = vp
        except: pass
    
    # CHECK: Is there only 1 variant?
    is_single_variant = (len(variations) == 1)

    for v in variations:
        v_data = v.get('data', {})
        v_id = v_data.get('id') or v_data.get('apn') or f"{parent_id}_var"
        
        # --- LABEL LOGIC ---
        variant_label = ""
        
        # Only build label if there is more than 1 variant
        if not is_single_variant:
            details = []
            size_val = v_data.get('Size')
            color_val = v_data.get('SecondaryColour') or v_data.get('Colour')
            
            if size_val and str(size_val).lower() != "one size": 
                details.append(f"Size {size_val}")
            
            if color_val: 
                details.append(color_val)
            
            variant_label = " / ".join(details)

        # --- URL LOGIC ---
        query_params = []
        size_val_raw = v_data.get('Size')
        color_val_raw = v_data.get('SecondaryColour') or v_data.get('Colour')

        if color_val_raw: query_params.append(f"selectedSwatch={quote_plus(color_val_raw)}")
        if size_val_raw: query_params.append(f"size={quote_plus(size_val_raw)}")
        
        final_link = parent_url_base
        if query_params: final_link += "?" + "&".join(query_params)
        
        # --- PRICE LOGIC ---
        try: curr_price = float(v_data.get('price', 0))
        except: curr_price = 0.0
        
        orig_price = curr_price

        v_save_text = v_data.get('SavePrice', '')
        extracted = extract_price_from_text(v_save_text)
        
        if extracted and extracted > curr_price:
            orig_price = extracted
        elif parent_was_price and parent_was_price > curr_price:
             orig_price = parent_was_price
        else:
            for field in ['was_price', 'list_price', 'regular_price']:
                try:
                    val = float(v_data.get(field, 0))
                    if val > orig_price: orig_price = val
                except: pass
            
            if orig_price <= curr_price and max_variant_price > curr_price:
                orig_price = max_variant_price
            
        add_row(v_id, parent_name, variant_label, orig_price, curr_price, cat, final_link, results_list)

def add_row(p_id, name, var_label, orig, curr, cat, link, results_list):
    if orig < curr: orig = curr
    
    disc_percent = "0%"
    if orig > 0 and curr < orig:
        pct = ((orig - curr) / orig) * 100
        disc_percent = f"{round(pct, 1)}%"
        
    if isinstance(cat, list): cat = " > ".join(cat[-2:])
    
    results_list.append([p_id, name, var_label, orig, curr, disc_percent, cat, link])

if __name__ == "__main__":
    scrape_entire_catalogue()