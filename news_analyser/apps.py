from django.apps import AppConfig


class NewsAnalyserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'news_analyser'

    def ready(self):
        import news_analyser.signals
