from django.contrib import admin

from news_analyser.models import News, Keyword, Source

# Register your models here.
admin.site.register(News)
admin.site.register(Keyword)
admin.site.register(Source)
