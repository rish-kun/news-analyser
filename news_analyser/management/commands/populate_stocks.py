import csv
from django.core.management.base import BaseCommand
from news_analyser.models import Stock

class Command(BaseCommand):
    help = 'Populate stocks from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            for row in reader:
                symbol = row[0]
                name = row[1]
                Stock.objects.get_or_create(symbol=symbol, defaults={'name': name})
        self.stdout.write(self.style.SUCCESS('Successfully populated stocks'))
