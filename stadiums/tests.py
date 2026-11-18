
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from leagues.models import League
from clubs.models import Club
from stadiums.models import Stadium


class StadiumAPITests(TestCase):

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

        self.stadium = Stadium.objects.create(
            name="Anfield",
            city="Liverpool",
            capacity=61276,
            opened=1884,
            club=self.club,
        )

        self.url = "/api/stadiums/"
        self.detail_url = f"{self.url}{self.stadium.id}/"

    def test_get_stadiums(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_stadium_by_id(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Anfield")

    def test_create_stadium(self):
        second_club = Club.objects.create(
            name="Arsenal",
            short_name="ARS",
            league=self.league,
            city="London",
            founded=1886,
            stadium_name="Emirates Stadium",
        )

        payload = {
            "name": "Emirates Stadium",
            "city": "London",
            "capacity": 60704,
            "opened": 2006,
            "club": second_club.id,
        }

        response = self.client.post(
            self.url, payload, format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(Stadium.objects.count(), 2)

    def test_put_stadium(self):
        payload = {
            "name": "Anfield",
            "city": "Liverpool",
            "capacity": 62000,
            "opened": 1884,
            "club": self.club.id,
        }

        response = self.client.put(
            self.detail_url, payload, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.stadium.refresh_from_db()
        self.assertEqual(self.stadium.capacity, 62000)

    def test_patch_stadium(self):
        response = self.client.patch(
            self.detail_url,
            {"capacity": 63000},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.stadium.refresh_from_db()
        self.assertEqual(self.stadium.capacity, 63000)

    def test_delete_stadium(self):
        response = self.client.delete(self.detail_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Stadium.objects.filter(id=self.stadium.id).exists()
        )

    def test_invalid_stadium(self):
        response = self.client.post(
            self.url,
            {
                "name": "",
                "city": "Liverpool",
                "capacity": -100,
                "club": self.club.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_stadium_club_relationship(self):
        self.assertEqual(self.stadium.club, self.club)
