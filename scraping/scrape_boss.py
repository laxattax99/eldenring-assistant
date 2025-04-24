import requests
from bs4 import BeautifulSoup
import sqlite3
import json

BOSS_URL = 'https://eldenring.wiki.fextralife.com/Malenia+Blade+of+Miquella'

response = requests.get(BOSS_URL)
soup = BeautifulSoup(response.text, 'html.parser')

# Extract boss name
name_tag = soup.find('h1')
name = name_tag.text.strip() if name_tag else None

# Extract location and combat info from the first info table
location = None
combat_info = {}
info_table = soup.find('table')
if info_table:
    for row in info_table.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        if len(cells) == 2:
            label = cells[0].text.strip()
            value = cells[1].text.strip()
            if 'Location' in label:
                location = value
            else:
                combat_info[label] = value

def extract_list_by_h4_with_divs(header_keywords):
    """Extracts all list items under an h4 header, including those in col-sm-6 divs."""
    results = []
    for h in soup.find_all('h4'):
        if any(kw in h.text.lower() for kw in header_keywords):
            # Look for the first div that might contain col-sm-6 divs
            div_container = None
            node = h.find_next_sibling()
            while node and node.name != 'h4':
                if node.name == 'div' and node.find('div', class_='col-sm-6'):
                    div_container = node
                    break
                node = node.find_next_sibling()
            
            if div_container:
                # Extract from all col-sm-6 divs
                for col_div in div_container.find_all('div', class_='col-sm-6'):
                    for ul in col_div.find_all('ul'):
                        for li in ul.find_all('li'):
                            results.append(li.get_text(strip=True))
            else:
                # Fallback to regular list extraction
                node = h.find_next_sibling()
                while node and node.name != 'h4':
                    if node.name in ['ul', 'ol']:
                        for li in node.find_all('li'):
                            results.append(li.get_text(strip=True))
                    node = node.find_next_sibling()
            break
    return results

def extract_attacks_table():
    """Extracts all attack names and descriptions from the attacks table under the h4 header."""
    attacks = []
    for h in soup.find_all('h4'):
        if 'attack' in h.text.lower():
            table = h.find_next('table')
            if table:
                for row in table.find_all('tr'):
                    tds = row.find_all('td')
                    if len(tds) >= 1:
                        # Combine all columns for a full attack description
                        attack = ' | '.join(td.get_text(strip=True) for td in tds)
                        attacks.append(attack)
            break
    return attacks

def extract_strategies():
    """Extract all strategy-related content from multiple h4 headers and their content"""
    strategies = []
    strategy_started = False
    
    # Get the main strategies div
    for div in soup.find_all('div', class_='col-sm-6'):
        # Look for strategy headers
        for h4 in div.find_all('h4'):
            if any(kw in h4.text.lower() for kw in ['tip', 'strategy', 'breakdown', 'note', 'melee', 'magic']):
                strategy_started = True
                # Add header as a strategy entry
                strategies.append(f"## {h4.text.strip()}")
                
                # Process all content until the next h4
                current = h4.next_sibling
                while current and (not isinstance(current, type(h4)) or current.name != 'h4'):
                    if current.name == 'ul':
                        for li in current.find_all('li'):
                            strategies.append(f"- {li.get_text(strip=True)}")
                    elif current.name == 'p':
                        text = current.get_text(strip=True)
                        if text:
                            strategies.append(text)
                    current = current.next_sibling
    
    return strategies

negations = extract_list_by_h4_with_divs(['negation'])
resistances = extract_list_by_h4_with_divs(['resist'])
strategies = extract_strategies()
attacks = extract_attacks_table()

# Connect to the database
conn = sqlite3.connect('eldenring.db')
c = conn.cursor()

# Insert into bosses table (with strategies)
c.execute('''
    INSERT INTO bosses (name, location, stats, negations, resistances, attacks, strategies)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', (
    name,
    location,
    json.dumps(combat_info) if combat_info else None,
    json.dumps(negations) if negations else None,
    json.dumps(resistances) if resistances else None,
    json.dumps(attacks) if attacks else None,
    json.dumps(strategies) if strategies else None
))

conn.commit()
conn.close()

print(f"Inserted boss: {name}")
