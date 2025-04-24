import requests
from bs4 import BeautifulSoup
import sqlite3
import json
import re

WEAPON_URL = 'https://eldenring.wiki.fextralife.com/Star+Fist'

response = requests.get(WEAPON_URL)
soup = BeautifulSoup(response.text, 'html.parser')

# Extract weapon name
name_tag = soup.find('h1')
name = name_tag.text.strip() if name_tag else None

# Extract weapon type and other basic info from the first info table
weapon_info = {}
info_table = soup.find('table')
if info_table:
    for row in info_table.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        if len(cells) == 2:
            label = cells[0].text.strip()
            value = cells[1].text.strip()
            weapon_info[label] = value

# Extract location and other information from the text
location = None
notes = []

# Find weapon location
for p in soup.find_all('p'):
    text = p.text.strip()
    if 'location:' in text.lower() or 'found' in text.lower():
        location = text
        break

# Extract notes and tips
for p in soup.find_all('p'):
    text = p.text.strip()
    if text and len(text) > 20 and not text.startswith('Location'):
        # Look for descriptive paragraphs that might be notes
        notes.append(text)

# Also check bulleted lists for notes
for ul in soup.find_all('ul'):
    for li in ul.find_all('li'):
        text = li.text.strip()
        if text:
            notes.append(text)

# Extract weapon description (first paragraph of the page is usually the description)
description = None
first_p = soup.find('p')
if first_p:
    description = first_p.text.strip()

# Extract attack data
def extract_attacks_section(header_text):
    attacks = {}
    for h in soup.find_all(['h2', 'h3', 'h4']):
        if header_text.lower() in h.text.lower():
            # Extract the bullet points under this header
            node = h.find_next_sibling()
            while node and node.name not in ['h2', 'h3', 'h4']:
                if node.name == 'ul':
                    for li in node.find_all('li'):
                        text = li.text.strip()
                        if ':' in text:
                            key, value = text.split(':', 1)
                            attacks[key.strip()] = value.strip()
                node = node.find_next_sibling()
    return attacks

one_handed_attacks = extract_attacks_section("ONE-HANDED ATTACKS")
two_handed_attacks = extract_attacks_section("TWO-HANDED ATTACKS")

# Extract max upgrades table with improved method
def extract_max_upgrades():
    max_upgrades = {}
    
    # Find the Max Upgrades section
    for div in soup.find_all('div', class_='tabcontent'):
        if div.find('h3') and 'Max Upgrades' in div.find('h3').text:
            # Get the table within this div
            table = div.find('table', class_='wiki_table')
            if not table:
                continue
            
            # Parse the headers - they span multiple rows and columns
            headers = []
            header_row = table.find('tr')
            
            # First column is usually empty or upgrade type
            headers.append("Upgrade")
            
            # Extract column group headers
            col_groups = []
            for th in header_row.find_all('th'):
                colspan = int(th.get('colspan', 1))
                header_text = th.text.strip()
                # Add the column group and its span
                if header_text:
                    col_groups.append((header_text, colspan))
            
            # Get the actual column headers from the second row
            subheader_row = table.find_all('tr')[1]
            subheaders = []
            for th in subheader_row.find_all('th'):
                subheaders.append(th.text.strip())
            
            # Now process each data row
            for row in table.find_all('tr')[2:]:  # Skip the header rows
                cells = row.find_all(['th', 'td'])
                if len(cells) < 2:
                    continue
                
                # First cell is the upgrade type (e.g., "Std+25")
                upgrade_type = cells[0].text.strip()
                upgrade_data = {"Upgrade": upgrade_type}
                
                # Process the remaining cells, mapping them to appropriate headers
                for i, cell in enumerate(cells[1:], 1):
                    if i < len(subheaders):
                        # Regular numeric or text data
                        cell_text = cell.text.strip()
                        upgrade_data[subheaders[i-1]] = cell_text
                    else:
                        # Handle special cells with images (passive effects)
                        effects = []
                        for img in cell.find_all('img'):
                            # Get effect name from alt text or title
                            effect_name = img.get('alt', '').split('_')[0] if img.get('alt') else ''
                            # Get effect value from text near the image
                            effect_text = cell.text.strip()
                            values = re.findall(r'\((\d+)\)', effect_text)
                            effect_value = values[0] if values else ''
                            
                            if effect_name:
                                effects.append(f"{effect_name}: {effect_value}")
                        
                        if effects:
                            upgrade_data["Passive Effects"] = effects
                
                # Add this upgrade type data to the results
                max_upgrades[upgrade_type] = upgrade_data
    
    return max_upgrades

max_upgrades = extract_max_upgrades()

# Connect to the database
conn = sqlite3.connect('eldenring.db')
c = conn.cursor()

# Insert into weapons table
c.execute('''
    INSERT INTO weapons (name, type, stats, description, location, notes, one_handed_attacks, two_handed_attacks, max_upgrades)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    name,
    weapon_info.get('Type', None),
    json.dumps(weapon_info) if weapon_info else None,
    description,
    location,
    json.dumps(notes) if notes else None,
    json.dumps(one_handed_attacks) if one_handed_attacks else None,
    json.dumps(two_handed_attacks) if two_handed_attacks else None,
    json.dumps(max_upgrades) if max_upgrades else None
))

conn.commit()
conn.close()

print(f"Inserted weapon: {name}")