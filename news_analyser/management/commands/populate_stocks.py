import csv
from django.core.management.base import BaseCommand
from news_analyser.models import Stock

class Command(BaseCommand):
    help = 'Populate stocks from a CSV file'

    def handle(self, *args, **kwargs):
        with open('Ticker_List_NSE_India.csv', 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            for row in reader:
                symbol = row[0]
                name = row[1]
                Stock.objects.get_or_create(symbol=symbol, defaults={'name': name})
        self.stdout.write(self.style.SUCCESS('Successfully populated stocks'))
