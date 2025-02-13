from django.db import models
from email.utils import parsedate_to_datetime


    
class Keyword(models.Model):
    name = models.CharField(max_length=200)
    create_date = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name


    def get_news(self):
        return {self:self.news.all()}
    


class News(models.Model):
    title = models.CharField(max_length=200)
    content_summary = models.TextField()
    content = models.TextField()
    date = models.DateTimeField()
    source = models.CharField(max_length=200)
    keyword=models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="news")
    def __str__(self):
        return self.title
    
    @staticmethod
    def parse_news(news, kwd):
        obj = News()
        obj.title = news['title']
        obj.content_summary = news['summary']
        obj.source = news['link']
        obj.date = parsedate_to_datetime(news['published'])
        obj.keyword = kwd
        obj.save()
        return obj
    
    def get_content(self):
        pass
