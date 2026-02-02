from django.core.management.base import BaseCommand
from django.db import connection
import os

class Command(BaseCommand):
    help = 'Reseeds the database with data from DB_query.txt'

    def handle(self, *args, **options):
        # Path to DB_query.txt
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'DB_query.txt')
        
        self.stdout.write(f'Reading SQL from {file_path}...')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # Split content into individual statements, but handle the fact that it might be one large block
        # The file seems to have multiple INSERT statements.
        # We need to be careful about SQLite integrity.
        
        with connection.cursor() as cursor:
            # 1. Clear existing data
            self.stdout.write('Clearing existing data...')
            # Disable foreign key checks for SQLite to allow truncation in any order
            cursor.execute('PRAGMA foreign_keys = OFF;')
            cursor.execute('DELETE FROM api_propertyfact;')
            cursor.execute('DELETE FROM api_propertyimage;')
            cursor.execute('DELETE FROM api_property;')
            cursor.execute('DELETE FROM api_broker;')
            cursor.execute('PRAGMA foreign_keys = ON;')
            
            # 2. Execute SQL from file
            self.stdout.write('Executing SQL statements...')
            
            # We can try executing script if it's multiple statements separated by semicolon
            try:
                cursor.executescript(sql_content)
                self.stdout.write(self.style.SUCCESS('Successfully reseeded database'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error executing SQL: {e}'))
