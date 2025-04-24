import requests
from bs4 import BeautifulSoup
import sqlite3
import json
import re
import sys

def scrape_magic(url, magic_type='sorcery'):
    """
    Scrape a sorcery or incantation page from the Elden Ring wiki
    
    Args:
        url: URL of the wiki page
        magic_type: Either 'sorcery' or 'incantation'
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract name
    name_tag = soup.find('h1')
    name = name_tag.text.strip() if name_tag else None

    # Extract basic info (FP Cost, Requirements) from the info table
    fp_cost = None
    requirements = {}
    
    # Find the stats table (usually the first table with 'FP Cost' or similar)
    info_table = None
    for table in soup.find_all('table', class_='wiki_table'):
        if 'FP Cost' in table.text:
            info_table = table
            break
            
    if info_table:
        for row in info_table.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            
            # Special case for FP Cost and Slots Used in the same cell
            for cell in cells:
                if 'FP Cost' in cell.text:
                    # Extract FP cost from this cell
                    fp_match = re.search(r'FP Cost\D*(\d+)', cell.text)
                    if fp_match:
                        fp_cost = int(fp_match.group(1))
    
    # Extract requirements (Intelligence, Faith, Arcane) from the table
    if info_table:
        for row in info_table.find_all('tr'):
            # Look for the row with "Requires" text
            if 'Requires' in row.text:
                req_text = row.text
                
                # Extract Intelligence requirement
                int_match = re.search(r'Intelligence\D*(\d+)', req_text)
                if int_match:
                    requirements['Intelligence'] = int(int_match.group(1))
                    
                # Extract Faith requirement
                faith_match = re.search(r'Faith\D*(\d+)', req_text)
                if faith_match:
                    requirements['Faith'] = int(faith_match.group(1))
                    
                # Extract Arcane requirement
                arc_match = re.search(r'Arcane\D*(\d+)', req_text)
                if arc_match:
                    requirements['Arcane'] = int(arc_match.group(1))
                
                break
    
    # Extract guide information from the Guide section
    guide_content = []
    
    # Look for the Guide section with the bonfire class
    guide_header = soup.find('h3', class_='bonfire', string=lambda text: 'Guide' in text)
    if guide_header:
        # Find the first unordered list after the guide header
        guide_ul = guide_header.find_next('ul')
        if guide_ul:
            # Extract all bullet points as a flat list
            for li in guide_ul.find_all('li'):
                text = li.get_text(strip=True)
                if text:
                    guide_content.append(text)
    
    # Extract location (Where to Find section)
    location = None
    for h in soup.find_all(['h2', 'h3']):
        if 'where to find' in h.text.lower() or 'location' in h.text.lower():
            location_data = []
            current = h.find_next_sibling()
            
            while current and current.name not in ['h2', 'h3']:
                if current.name in ['p', 'li']:
                    text = current.text.strip()
                    if text:
                        location_data.append(text)
                elif current.name in ['ul', 'ol']:
                    for li in current.find_all('li'):
                        text = li.text.strip()
                        if text:
                            location_data.append(text)
                current = current.find_next_sibling()
                
            if location_data:
                location = '\n'.join(location_data)
            break
    
    # Connect to the database
    conn = sqlite3.connect('eldenring.db')
    c = conn.cursor()

    # Determine which table to insert into
    table_name = 'sorceries' if magic_type.lower() == 'sorcery' else 'incantations'

    # Insert into appropriate table with correct column names
    c.execute(f'''
        INSERT INTO {table_name} (name, requirements, guide, location, fp_cost)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        name,
        json.dumps(requirements) if requirements else None,
        json.dumps(guide_content) if guide_content else None,
        location,
        fp_cost
    ))

    conn.commit()
    conn.close()

    print(f"Inserted {magic_type}: {name}")
    return name

if __name__ == "__main__":
    # Check if URL and magic type are provided as command line arguments
    if len(sys.argv) > 1:
        url = sys.argv[1]
        magic_type = sys.argv[2] if len(sys.argv) > 2 else 'sorcery'
        scrape_magic(url, magic_type)
    else:
        # Default test case - Rellana's Twin Moons
        test_url = "https://eldenring.wiki.fextralife.com/Rellana's+Twin+Moons"
        scrape_magic(test_url, 'sorcery')