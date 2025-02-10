


import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
import time 
load_dotenv()
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',

]
creds = Credentials.from_service_account_file('./creds.json', scopes=scopes)
client = gspread.authorize(creds)


def get_details():
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    sheet = client.open_by_key(sheet_id)
    values = sheet.sheet1.row_values(1)
    cats = sheet.sheet1.col_values(1)[1:]
    keywords = sheet.sheet1.col_values(2)[1:]
    cat_kwd ={} # cat dict of the format: {cat:[kwd1, kwd2, kwd3]}

    for n, i in enumerate(cats):
        try:
            cat_kwd[i] = list(keywords[n].split(','))
        except IndexError:
            cat_kwd[i] = []
    return cat_kwd

def write_news(cat_news=None):
    # takes dict of format {cat:[n1, n2, n3]}

    if cat_news is None:
        cat_news = {
    'Technology': ['Apple releases new iPhone', 'Tesla announces new EV', 'Google unveils AI updates'],
    'Sports': ['Lakers win championship', 'World Cup final results', 'New NBA record set'],
    'Finance': ['Stock market hits record high', 'Bitcoin surges', 'Fed adjusts interest rates']
    }
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    sheet = client.open_by_key(sheet_id)
    #! sheet.sheet1.update_cell(1, 1, 'Category'), 1, 1 = first row, first column

    for en, cat in enumerate(cat_news.keys()):
        sheet.sheet1.update_cell(en+2, 1, cat)
        for e, i in enumerate(cat_news[cat]):
            sheet.sheet1.update_cell(en+2, e+3, i)
        # sheet.sheet1.updatde_cell(en+t)
        # sheet.sheet1.update__cell(en+1, 1, cat)
    #     for n in news:
    #         sheet.sheet1.append_row(['', n])


write_news()

def update_sources(sources):
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    wb = client.open_by_key(sheet_id)
    sheet = wb.worksheet('Config Data')
    sheet.update_cell(1, 3, 'Sources')
    for n, source in enumerate(sources.keys()):
        try:
            sheet.update_cell(n+2,3, source)
        except gspread.exceptions.APIError:
            print("Pausing due to API Limit")
            time.sleep(60)
            sheet.update_cell(n+2,3, source)
            continue

    return True


def write_links(kw_link):
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    wb = client.open_by_key(sheet_id)
    sheet = wb.worksheet('News Links')

    for en, cat in enumerate(kw_link.keys()):
        sheet.update_cell(en+2, 1, cat)
        for e, i in enumerate(kw_link[cat]):
            sheet.update_cell(en+2, e+3, i)
