from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile

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
