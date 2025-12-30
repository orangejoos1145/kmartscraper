import pandas as pd
import html
import json
from datetime import datetime
import pytz # Added for Timezone fix

# --- CONFIGURATION ---
IN_CSV = "kmart_full_catalogue.csv"
OUT_HTML = "index.html"
ITEMS_PER_PAGE = 50

COLOR_PRIMARY = "#E4002B" 
COLOR_ACCENT = "#262D69"

def fmt_price(val):
    try: return f"${float(val):,.2f}" if float(val) > 0 else ""
    except: return ""

try:
    df = pd.read_csv(IN_CSV, sep='|')
except FileNotFoundError:
    print(f"Error: '{IN_CSV}' not found.")
    df = pd.DataFrame()

# Numeric conversion
df['curr_price'] = pd.to_numeric(df['discounted price'], errors='coerce').fillna(0)
df['orig_price'] = pd.to_numeric(df['Original price'], errors='coerce').fillna(0)
mask_disc = (df['orig_price'] > 0) & (df['curr_price'] < df['orig_price'])
df['pct_val'] = 0.0
df.loc[mask_disc, 'pct_val'] = ((df['orig_price'] - df['curr_price']) / df['orig_price']) * 100
df['pct_val'] = df['pct_val'].round(1)
df['pct_text'] = df['pct_val'].apply(lambda x: f"{int(x)}%" if x > 0 else "")
df['category'] = df['category'].fillna("Other")

# Ensure columns exist
if 'stock_status' not in df.columns: df['stock_status'] = 'In Stock'
if 'top_category' not in df.columns: 
    df['top_category'] = df['category'].apply(lambda x: str(x).split('>')[0].strip())

df['clean_id'] = df['id'].astype(str).str.replace(r'^[pP]_', '', regex=True)
unique_cats = sorted(df['top_category'].dropna().unique())

deals_payload = []
for idx, row in df.iterrows():
    final_link = str(row.get('product link', '#'))
    v_label = str(row.get('variant label', ''))
    if v_label == "nan": v_label = ""
    
    # Text Cleanup
    v_label = v_label.replace("Size One Size / ", "").replace("Size One Size", "")

    deals_payload.append({
        "id": str(row['clean_id']),
        "t": str(row.get('product name', '')),
        "v": v_label,
        "l": final_link,
        "op": fmt_price(row['orig_price']),
        "cp": fmt_price(row['curr_price']),
        "pv": float(row['curr_price']),
        "dt": row['pct_text'],
        "dv": float(row['pct_val']),
        "c": str(row['category']),
        "tc": str(row['top_category']),
        "st": str(row.get('stock_status', 'In Stock')) 
    })

json_data = json.dumps(deals_payload)
unique_cats_json = json.dumps(unique_cats)

# ---- TIMEZONE FIX ----
try:
    nz_tz = pytz.timezone('Pacific/Auckland')
    scrape_time_str = datetime.now(nz_tz).strftime("%d/%m/%Y @ %I:%M %p")
except Exception as e:
    print(f"Timezone Error: {e}. Falling back to UTC.")
    scrape_time_str = datetime.now().strftime("%d/%m/%Y @ %I:%M %p UTC")

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kmart Deals Filterer</title>
<style>
    :root {{
        --bg-color: #121212;
        --card-bg: #1e1e1e;
        --text-main: #ffffff;
        --text-muted: #aaaaaa;
        --accent: {COLOR_PRIMARY}; 
        --accent-hover: #b80022;
        --accent-blue: {COLOR_ACCENT}; 
        --border: #333333;
        --table-header: #2c2c2c;
        --pill-bg: #2d2d2d;
        --row-hover: #252525;
        --row-zero-off: rgba(228, 0, 43, 0.15);
        --stock-green: #00c853;
        --stock-red: #d50000;
        --stock-orange: #ff9800;
    }}
    body {{ font-family: 'Segoe UI', sans-serif; background-color: var(--bg-color); color: var(--text-main); margin: 0; padding: 20px; }}
    .container {{ max-width: 1400px; margin: 0 auto; background-color: var(--card-bg); padding: 20px; border-radius: 8px; }}
    
    .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 15px; }}
    .title-group h1 {{ margin: 0; font-size: 24px; color: white; }}
    .title-group .subtitle {{ color: var(--text-muted); font-size: 13px; margin-top: 5px; }}
    .btn {{ background: #333; border: 1px solid #444; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 13px; margin-left: 8px; }}
    .btn.coffee {{ background: #f36f21; border-color: #f36f21; color: white; }}
    
    .search-row {{ display: flex; gap: 10px; align-items: center; background: #252525; padding: 15px; border-radius: 6px; flex-wrap: wrap; }}
    input[type="text"], input[type="number"] {{ background: #121212; border: 1px solid var(--border); color: white; padding: 10px; border-radius: 4px; font-size: 14px; }}
    #searchInput {{ flex-grow: 1; min-width: 200px; }}
    .num-input {{ width: 60px; text-align: center; }}
    .btn-search {{ background-color: var(--accent); color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }}
    .btn-reset {{ background: transparent; border: 1px solid #555; color: #ccc; padding: 9px 15px; border-radius: 4px; cursor:pointer; }}
    .checkbox-group {{ display: flex; align-items: center; gap: 5px; font-size: 14px; margin: 0 10px; color: #ddd; cursor: pointer; }}
    .found-count {{ width: 100%; text-align: right; color: var(--text-muted); font-size: 13px; margin-top: 5px; margin-bottom: 15px; }}
    
    .section-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; }}
    .pill-container {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
    .pill {{ background-color: var(--pill-bg); color: #ddd; padding: 6px 14px; border-radius: 20px; font-size: 13px; cursor: pointer; border: 1px solid transparent; transition: all 0.2s; user-select: none; }}
    .pill:hover {{ background-color: #3a3a3a; border-color: #555; }}
    .pill.active {{ background-color: var(--accent); color: white; border-color: var(--accent); box-shadow: 0 0 8px rgba(228, 0, 43, 0.4); }}
    .pill.cat-pill.active {{ background-color: var(--accent-blue); border-color: var(--accent-blue); box-shadow: 0 0 8px rgba(38, 45, 105, 0.5); }} 
    
    .variant-badge {{
        display: inline-block;
        font-size: 11px;
        color: #ddd;
        background: rgba(255, 255, 255, 0.05);
        padding: 3px 10px;
        border-radius: 12px;
        margin-left: 10px;
        font-weight: 500;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 0 10px rgba(38, 45, 105, 0.2);
        letter-spacing: 0.5px;
    }}

    .stock-badge {{ font-weight: 700; font-size: 11px; }}
    .stock-online {{ color: var(--stock-green); }}
    .stock-store {{ color: var(--stock-orange); }}
    .stock-out {{ color: var(--stock-red); }}
    
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }}
    thead th {{ background-color: var(--table-header); color: var(--text-muted); text-align: left; padding: 12px; font-weight: 600; font-size: 12px; text-transform: uppercase; cursor: pointer; }}
    tbody td {{ padding: 12px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
    tr:hover {{ background-color: var(--row-hover); }}
    tr.zero-off-row {{ background-color: var(--row-zero-off); }}
    
    .col-id {{ color: var(--text-muted); font-family: monospace; font-size: 12px; }}
    .col-title a {{ font-weight: 600; color: #fff; text-decoration: none; }}
    .col-title a:hover {{ color: var(--accent); text-decoration: underline; }}
    .col-orig {{ text-decoration: line-through; color: var(--text-muted); }}
    .col-disc {{ font-weight: bold; font-size: 15px; }}
    .col-pct {{ color: var(--accent); font-weight: bold; }}
    .cat-badge {{ background: #333; color: #ccc; padding: 2px 8px; border-radius: 4px; font-size: 11px; text-transform: uppercase; }}
    .google-icon svg {{ fill: #777; width: 18px; height: 18px; vertical-align: middle; }}
    
    .pagination-container {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid var(--border); }}
    .btn-page {{ background: #333; color: white; border: 1px solid #444; padding: 8px 16px; border-radius: 4px; cursor: pointer; }}
    .btn-page:disabled {{ opacity: 0.5; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="title-group"><h1>Kmart Deals Filterer</h1><div class="subtitle">Last updated: {scrape_time_str}</div></div>
        <div class="header-buttons"><button class="btn coffee">☕ Coffee</button></div>
    </div>
    <div class="search-row">
        <input type="text" id="searchInput" placeholder="Search products...">
        <div style="display:flex; align-items:center; gap:5px; color:#aaa; font-size:13px;">
            Discount % <input type="number" id="minDisc" class="num-input" value="0" min="0" max="100">
            <input type="number" id="maxDisc" class="num-input" value="100" min="0" max="100">
        </div>
        <label class="checkbox-group"><input type="checkbox" id="hideZero" checked onchange="applyFilters()"> Hide 0% Off</label>
        <label class="checkbox-group"><input type="checkbox" id="hideOOS" checked onchange="applyFilters()"> Hide OOS</label>
        <button class="btn-reset" onclick="resetFilters()">Reset</button>
    </div>
    <div class="found-count">Found: <span id="countDisplay">0</span></div>
    
    <div class="section-label">QUICK SEARCH:</div><div class="pill-container" id="quickSearchContainer"></div>
    <div class="section-label">FILTER BY CATEGORY:</div><div class="pill-container" id="catFilterContainer"><span class="pill cat-pill active" onclick="filterCat('All', this)">ALL</span></div>
    
    <div class="pagination-container">
        <div class="pagination-info" id="pageInfo">Page 1</div>
        <div class="pagination-buttons"><button class="btn-page" id="btnPrev" onclick="prevPage()">Previous</button><button class="btn-page" id="btnNext" onclick="nextPage()">Next</button></div>
    </div>

    <table>
        <thead><tr><th onclick="sort('id')">ID</th><th onclick="sort('t')">Title</th><th onclick="sort('op')">Original</th><th onclick="sort('cp')">Discounted</th><th onclick="sort('dv')">% Off</th><th>Category</th><th>Stock</th><th>G</th></tr></thead>
        <tbody id="tableBody"></tbody>
    </table>
</div>
<script>
    const data = {json_data};
    const categories = {unique_cats_json};
    const quickTerms = ["Everlast", "OXX", "Active", "Trackpants", "Hoodie", "Dress", "Briefs", "Bra", "Sneakers", "Pyjama", "Mens", "Womens", "Kids", "Clearance"];
    const ITEMS_PER_PAGE = {ITEMS_PER_PAGE};
    let state = {{ text: "", minD: 0, maxD: 100, hideZero: true, hideOOS: true, cat: "All", activeQuick: null, sortCol: "dv", sortAsc: false, currentPage: 1, filteredData: [] }};

    const qsContainer = document.getElementById('quickSearchContainer');
    quickTerms.forEach(term => {{ const pill = document.createElement('span'); pill.className = 'pill'; pill.innerText = term; pill.onclick = () => toggleQuickSearch(term, pill); qsContainer.appendChild(pill); }});
    const catContainer = document.getElementById('catFilterContainer');
    categories.forEach(c => {{ const pill = document.createElement('span'); pill.className = 'pill cat-pill'; pill.innerText = c.toUpperCase(); pill.onclick = () => filterCat(c, pill); catContainer.appendChild(pill); }});

    function filterAndSort() {{
        let filtered = data.filter(item => {{
            if (state.text && !item.t.toLowerCase().includes(state.text.toLowerCase()) && !item.id.includes(state.text)) return false;
            if (item.dv < state.minD || item.dv > state.maxD) return false;
            if (state.hideZero && item.dv <= 0) return false;
            if (state.hideOOS && item.st === "OOS") return false;
            if (state.cat !== "All" && item.tc !== state.cat) return false;
            return true;
        }});
        filtered.sort((a, b) => {{
            let valA = a[state.sortCol], valB = b[state.sortCol];
            if (typeof valA === 'string') {{ valA = valA.toLowerCase(); valB = valB.toLowerCase(); }}
            if (valA < valB) return state.sortAsc ? -1 : 1;
            if (valA > valB) return state.sortAsc ? 1 : -1;
            return 0;
        }});
        state.filteredData = filtered;
        document.getElementById('countDisplay').innerText = filtered.length;
        renderTable();
    }}

    function renderTable() {{
        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = "";
        const totalPages = Math.ceil(state.filteredData.length / ITEMS_PER_PAGE) || 1;
        if (state.currentPage > totalPages) state.currentPage = 1;
        const start = (state.currentPage - 1) * ITEMS_PER_PAGE;
        const pageItems = state.filteredData.slice(start, start + ITEMS_PER_PAGE);
        document.getElementById('pageInfo').innerText = `Page ${{state.currentPage}} of ${{totalPages}}`;
        document.getElementById('btnPrev').disabled = (state.currentPage === 1);
        document.getElementById('btnNext').disabled = (state.currentPage >= totalPages);

        pageItems.forEach(item => {{
            const tr = document.createElement('tr');
            if (item.dv <= 0) tr.classList.add('zero-off-row');
            
            let titleHtml = `<a href="${{item.l}}" target="_blank">${{item.t}}</a>`;
            if (item.v) {{
                titleHtml += `<span class="variant-badge">${{item.v}}</span>`;
            }}
            
            let stockClass = "stock-out";
            if (item.st.includes("Online") || item.st.includes("In Stock")) stockClass = "stock-online";
            else if (item.st.includes("In Store")) stockClass = "stock-store";
            
            let stockHtml = `<span class="stock-badge ${{stockClass}}">${{item.st}}</span>`;

            tr.innerHTML = `
                <td class="col-id">${{item.id}}</td>
                <td class="col-title">${{titleHtml}}</td>
                <td class="col-orig">${{item.op}}</td>
                <td class="col-disc">${{item.cp}}</td>
                <td class="col-pct">${{item.dt}}</td>
                <td><span class="cat-badge">${{item.c}}</span></td>
                <td>${{stockHtml}}</td>
                <td><a href="https://www.google.com/search?q=${{encodeURIComponent(item.t)}}" target="_blank" class="google-icon"><svg viewBox="0 0 24 24"><path d="M12.48 10.92v3.28h7.84c-.24 1.84-.853 3.187-1.787 4.133-1.147 1.147-2.933 2.4-6.053 2.4-4.827 0-8.6-3.893-8.6-8.72s3.773-8.72 8.6-8.72c2.6 0 4.507 1.027 5.907 2.347l2.307-2.307C18.747 1.44 16.133 0 12.48 0 5.867 0 .533 5.347.533 12S5.867 24 12.48 24c3.44 0 6.04-1.133 8.16-3.293 2.16-2.16 2.84-5.213 2.84-7.667 0-.76-.053-1.467-.173-2.12h-10.827z"></path></svg></a></td>
            `;
            tbody.appendChild(tr);
        }});
    }}

    function applyFilters() {{ state.text = document.getElementById('searchInput').value; state.minD = parseFloat(document.getElementById('minDisc').value)||0; state.maxD = parseFloat(document.getElementById('maxDisc').value)||100; state.hideZero = document.getElementById('hideZero').checked; state.hideOOS = document.getElementById('hideOOS').checked; state.currentPage = 1; filterAndSort(); }}
    function toggleQuickSearch(term, element) {{ const searchInput = document.getElementById('searchInput'); if (state.activeQuick === term) {{ state.activeQuick = null; searchInput.value = ""; element.classList.remove('active'); }} else {{ document.querySelectorAll('#quickSearchContainer .pill').forEach(p => p.classList.remove('active')); state.activeQuick = term; searchInput.value = term; element.classList.add('active'); state.cat = "All"; updateCatPills(); }} applyFilters(); }}
    function filterCat(cat, element) {{ state.cat = cat; updateCatPills(); state.currentPage = 1; filterAndSort(); }}
    function updateCatPills() {{ const pills = document.querySelectorAll('.cat-pill'); pills.forEach(p => {{ if (p.innerText === state.cat.toUpperCase() || (state.cat === "All" && p.innerText === "ALL")) p.classList.add('active'); else p.classList.remove('active'); }}); }}
    function resetFilters() {{ document.getElementById('searchInput').value = ""; document.getElementById('minDisc').value = 0; document.getElementById('maxDisc').value = 100; document.getElementById('hideZero').checked = true; document.getElementById('hideOOS').checked = true; state.cat = "All"; state.text = ""; state.minD = 0; state.maxD = 100; state.hideZero = true; state.hideOOS = true; state.activeQuick = null; state.currentPage = 1; document.querySelectorAll('.pill').forEach(p => p.classList.remove('active')); updateCatPills(); filterAndSort(); }}
    function sort(col) {{ if (state.sortCol === col) state.sortAsc = !state.sortAsc; else {{ state.sortCol = col; state.sortAsc = true; }} filterAndSort(); }}
    function prevPage() {{ if (state.currentPage > 1) {{ state.currentPage--; renderTable(); }} }}
    function nextPage() {{ state.currentPage++; renderTable(); }}
    
    // REALTIME SEARCH LISTENER
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    
    filterAndSort();
</script>
</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"✅ Generated {OUT_HTML} with Real-Time Search and NZ Time!")