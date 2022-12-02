import sqlite3
conn = sqlite3.connect('health.sqlite')

c = conn.cursor()

c.execute('''
            CREATE TABLE health
            (id INTEGER PRIMARY KEY ASC,
            receiver VARCHAR(50) NOT NULL,
            storage VARCHAR(50) NOT NULL,
            processing VARCHAR(50) NOT NULL,
            audit VARCHAR(50) NOT NULL,
            last_updated VARCHAR(100) NOT NULL)
            ''')

conn.commit()
conn.close()