from django.test import TestCase

from datetime import date
from rest_framework.test import APIClient
from rest_framework import status

from leagues.models import League
from clubs.models import Club
from players.models import Player
# Create your tests here.

class PlayerAPITests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.league = League.objects.create(name="Premier League", country="England")
        self.club = Club.objects.create(
            name="Manchester United",
            short_name="Man Utd",
            league=self.league,
            city="Manchester",
            founded=1878,
            stadium_name="Old Trafford"
        )
        self.player = Player.objects.create(
            first_name="Cristiano",
            last_name="Ronaldo",
            position="FW",
            club=self.club,
            date_of_birth=date(1985, 2, 5)
        )

    def test_get_players(self):
        response = self.client.get('/api/players/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['first_name'], 'Cristiano')

    def test_get_player_by_id(self):
        response = self.client.get(
            f"/api/players/{self.player.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_players_by_position(self):
        response = self.client.get(
            "/api/players/?position=FW"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_players_by_club(self):
        response = self.client.get(
            f"/api/players/?club={self.club.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_player(self):
        payload = {
            "first_name": "New",
            "last_name": "Forward",
            "date_of_birth": "2002-06-15",
            "nationality": "English",
            "club": self.club.id,
            "position": "FWD",
            "shirt_number": 9,
        }

        response = self.client.post(
            "/api/players/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_patch_player(self):
        response = self.client.patch(
            f"/api/players/{self.player.id}/",
            {"shirt_number": 5},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.player.refresh_from_db()
        self.assertEqual(self.player.shirt_number, 5)

    def test_delete_player(self):
        response = self.client.delete(
            f"/api/players/{self.player.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Player.objects.filter(id=self.player.id).exists()
        )
