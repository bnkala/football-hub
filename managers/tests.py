
from datetime import date

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from leagues.models import League
from clubs.models import Club
from managers.models import Manager


class ManagerAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.league = League.objects.create(
            name="Premier League",
            country="England",
            code="EPL",
            founded=1992,
        )

        self.club = Club.objects.create(
            name="Liverpool",
            short_name="LIV",
            league=self.league,
            city="Liverpool",
            founded=1892,
            stadium_name="Anfield",
        )

        self.manager = Manager.objects.create(
            first_name="Test",
            last_name="Manager",
            nationality="Dutch",
            date_of_birth=date(1978, 9, 17),
            appointed_date=date(2024, 6, 1),
            club=self.club,
        )

        self.url = "/api/managers/"
        self.detail_url = f"{self.url}{self.manager.id}/"

    def test_get_managers(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_manager_by_id(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_name"], "Manager")

    def test_create_manager(self):
        second_club = Club.objects.create(
            name="Arsenal",
            short_name="ARS",
            league=self.league,
            city="London",
            founded=1886,
            stadium_name="Emirates Stadium",
        )

        payload = {
            "first_name": "New",
            "last_name": "Coach",
            "nationality": "Spanish",
            "date_of_birth": "1982-03-26",
            "appointed_date": "2025-01-01",
            "club": second_club.id,
        }

        response = self.client.post(
            self.url, payload, format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(Manager.objects.count(), 2)

    def test_put_manager(self):
        payload = {
            "first_name": "Updated",
            "last_name": "Manager",
            "nationality": "English",
            "date_of_birth": "1978-09-17",
            "appointed_date": "2024-06-01",
            "club": self.club.id,
        }

        response = self.client.put(
            self.detail_url, payload, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.manager.refresh_from_db()
        self.assertEqual(self.manager.first_name, "Updated")

    def test_patch_manager(self):
        response = self.client.patch(
            self.detail_url,
            {"nationality": "German"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.manager.refresh_from_db()
        self.assertEqual(self.manager.nationality, "German")

    def test_delete_manager(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Manager.objects.filter(id=self.manager.id).exists()
        )

    def test_invalid_manager(self):
        response = self.client.post(
            self.url,
            {
                "first_name": "",
                "last_name": "",
                "nationality": "English",
                "club": self.club.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_manager_club_relationship(self):
        self.assertEqual(self.manager.club, self.club)
