import sqlite3

# Connect to (or create) the database file
conn = sqlite3.connect('../eldenring.db')
c = conn.cursor()

# Create bosses table
c.execute('''
CREATE TABLE IF NOT EXISTS bosses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT,
    stats TEXT,
    negations TEXT,
    resistances TEXT,
    attacks TEXT,
    strategies TEXT
)
''')

# Create weapons table
c.execute('''
CREATE TABLE IF NOT EXISTS weapons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT,
    stats TEXT,
    description TEXT,
    location TEXT,
    notes TEXT,
    one_handed_attacks TEXT,
    two_handed_attacks TEXT,
    max_upgrades TEXT
)
''')

# Drop existing tables if they exist
c.execute('DROP TABLE IF EXISTS spells')
c.execute('DROP TABLE IF EXISTS sorceries')
c.execute('DROP TABLE IF EXISTS incantations')

# Create sorceries table
c.execute('''
CREATE TABLE IF NOT EXISTS sorceries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    fp_cost INTEGER,
    slots_used INTEGER,
    requirements TEXT,
    description TEXT,
    location TEXT,
    notes TEXT,
    effects TEXT
)
''')

# Create incantations table
c.execute('''
CREATE TABLE IF NOT EXISTS incantations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    fp_cost INTEGER,
    slots_used INTEGER,
    requirements TEXT,
    description TEXT,
    location TEXT,
    notes TEXT,
    effects TEXT
)
''')

conn.commit()
conn.close()
