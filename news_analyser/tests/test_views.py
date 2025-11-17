from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from news_analyser.models import UserProfile

class SearchViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.user_profile = UserProfile.objects.create(user=self.user)
        self.client.login(username='testuser', password='password')

    def test_search_view_requires_login(self):
        """Test that search view requires authentication"""
        self.client.logout()
        response = self.client.get(reverse('news_analyser:search'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
