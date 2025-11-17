from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile, Source
from unittest.mock import patch


@override_settings(SECRET_KEY='a-test-secret-key')
class UserAuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.search_url = reverse('news_analyser:search')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123'
        }

    def test_registration_page_loads(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

    def test_user_registration(self):
        response = self.client.post(self.register_url, self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='testuser').exists())
        user = User.objects.get(username='testuser')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertRedirects(response, self.search_url)

    def test_login_page_loads(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_user_login(self):
        self.client.post(self.register_url, self.user_data)
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpassword123'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)

    def test_protected_view(self):
        response = self.client.get(self.search_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'{self.login_url}?next={self.search_url}')

        user = User.objects.create_user(username='testuser2', password='testpassword123')
        UserProfile.objects.create(user=user)
        self.client.login(username='testuser2', password='testpassword123')
        response = self.client.get(self.search_url)
        self.assertEqual(response.status_code, 200)


@override_settings(SECRET_KEY='a-test-secret-key')
class NewsAnalysisTasksTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpassword')
        self.profile = UserProfile.objects.create(user=self.user)
        Source.objects.create(id_name="ET", name="Economic Times", url="https://economictimes.indiatimes.com/")
        Source.objects.create(id_name="TOI", name="Times of India", url="https://timesofindia.indiatimes.com/")
        Source.objects.create(id_name="TH", name="The Hindu", url="https://www.thehindu.com/")
        Source.objects.create(id_name="OTHER", name="Other", url="https://www.google.com/")
        self.client = Client()
        self.client.login(username='testuser', password='testpassword')

    @patch('news_analyser.tasks.analyse_news_task.delay')
    def test_search_view_triggers_analysis_task(self, mock_delay):
        response = self.client.post(reverse('news_analyser:search'), {
            'search_type': 'keyword',
            'keyword': 'test',
        })
        self.assertTrue(mock_delay.called)
