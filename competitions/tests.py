
from datetime import date, datetime, timezone

from django.test import TestCase

from clubs.models import Club
from leagues.models import League
from fixtures.models import Match
from competitions.models import (
    Competition,
    Season,
    KnockoutRound,
    KnockoutTie,
)
from competitions.knockout import (
    calculate_aggregate,
    determine_winner,
    complete_knockout_tie,
    progress_knockout_round,
)

from rest_framework.test import APIClient
from rest_framework import status
from competitions.models import CompetitionEntry


class KnockoutTestBase(TestCase):

    def setUp(self):
        self.league = League.objects.create(
            name="La Liga",
            country="Spain",
            code="LAL",
        )

        self.barcelona = Club.objects.create(
            name="Barcelona",
            short_name="BAR",
            league=self.league,
            city="Barcelona",
            stadium_name="Camp Nou",
        )

        self.real_madrid = Club.objects.create(
            name="Real Madrid",
            short_name="RMA",
            league=self.league,
            city="Madrid",
            stadium_name="Santiago Bernabeu",
        )

        self.competition = Competition.objects.create(
            name="UEFA Champions League",
            competition_type="CONTINENTAL_CUP",
        )

        self.season = Season.objects.create(
            competition=self.competition,
            name="2026/27",
            start_date=date(2026, 7, 1),
            end_date=date(2027, 6, 30),
        )

        self.round = KnockoutRound.objects.create(
            season=self.season,
            name="ROUND_OF_16",
            order=1,
            tie_format="SINGLE_LEG",
        )

        self.tie = KnockoutTie.objects.create(
            knockout_round=self.round,
            home_club=self.barcelona,
            away_club=self.real_madrid,
        )

    def create_match(
        self,
        home_club,
        away_club,
        home_score,
        away_score,
        leg=1,
        home_penalties=None,
        away_penalties=None,
    ):
        return Match.objects.create(
            league=None,
            season=self.season,
            knockout_tie=self.tie,
            home_club=home_club,
            away_club=away_club,
            kickoff=datetime(
                2027, 2, 17, 20, 0, tzinfo=timezone.utc
            ),
            status="FINISHED",
            home_score=home_score,
            away_score=away_score,
            leg=leg,
            home_penalties=home_penalties,
            away_penalties=away_penalties,
        )

class KnockoutTests(KnockoutTestBase):
    def test_single_leg_winner(self):
        self.create_match(
            self.barcelona, self.real_madrid, 2, 1
        )

        winner = determine_winner(self.tie)

        self.assertEqual(winner, self.barcelona)

    def test_single_leg_penalty_winner(self):
        self.create_match(
            self.barcelona,
            self.real_madrid,
            1,
            1,
            home_penalties=4,
            away_penalties=5,
        )

        winner = determine_winner(self.tie)

        self.assertEqual(winner, self.real_madrid)

    def test_draw_without_penalties(self):
        self.create_match(
            self.barcelona, self.real_madrid, 1, 1
        )

        winner = determine_winner(self.tie)

        self.assertIsNone(winner)

    def test_two_legged_tie_incomplete_after_first_leg(self):
        self.round.tie_format = "TWO_LEGGED"
        self.round.save()

        self.create_match(
            self.barcelona, self.real_madrid, 2, 1
        )

        winner = determine_winner(self.tie)

        self.assertIsNone(winner)

    def test_two_legged_aggregate_winner(self):
        self.round.tie_format = "TWO_LEGGED"
        self.round.save()

        self.create_match(
            self.barcelona, self.real_madrid, 2, 1, leg=1
        )

        self.create_match(
            self.real_madrid, self.barcelona, 2, 0, leg=2
        )

        result = calculate_aggregate(self.tie)
        winner = determine_winner(self.tie)

        self.assertEqual(result["home_aggregate"], 2)
        self.assertEqual(result["away_aggregate"], 3)
        self.assertEqual(result["matches_played"], 2)
        self.assertEqual(winner, self.real_madrid)

    def test_complete_knockout_tie(self):
        self.create_match(
            self.barcelona, self.real_madrid, 2, 0
        )

        winner = complete_knockout_tie(self.tie)

        self.tie.refresh_from_db()

        self.assertEqual(winner, self.barcelona)
        self.assertTrue(self.tie.is_completed)
        self.assertEqual(self.tie.winner, self.barcelona)



class KnockoutAPITests(KnockoutTestBase):

    def setUp(self):
        super().setUp()

        self.client = APIClient()

        CompetitionEntry.objects.create(
            season=self.season,
            club=self.barcelona,
        )

        CompetitionEntry.objects.create(
            season=self.season,
            club=self.real_madrid,
        )

    def fixture_payload(
        self,
        home_club,
        away_club,
        home_score,
        away_score,
        leg=1,
    ):
        return {
            "league": None,
            "home_club": home_club.id,
            "away_club": away_club.id,
            "season": self.season.id,
            "knockout_tie": self.tie.id,
            "kickoff": "2027-02-17T20:00:00Z",
            "status": "FINISHED",
            "home_score": home_score,
            "away_score": away_score,
            "matchweek": 1,
            "leg": leg,
        }

    def test_api_automatically_completes_single_leg_tie(self):
        payload = self.fixture_payload(
            self.barcelona,
            self.real_madrid,
            2,
            1,
        )

        response = self.client.post(
            "/api/fixtures/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        self.tie.refresh_from_db()

        self.assertTrue(self.tie.is_completed)
        self.assertEqual(self.tie.winner, self.barcelona)

    def test_api_rejects_update_to_completed_tie(self):
        payload = self.fixture_payload(
            self.barcelona,
            self.real_madrid,
            2,
            1,
        )

        response = self.client.post(
            "/api/fixtures/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        match_id = response.data["id"]

        update_response = self.client.patch(
            f"/api/fixtures/{match_id}/",
            {"home_score": 3},
            format="json",
        )

        self.assertEqual(
            update_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        match = Match.objects.get(id=match_id)
        self.assertEqual(match.home_score, 2)

    def test_api_rejects_delete_from_completed_tie(self):
        payload = self.fixture_payload(
            self.barcelona,
            self.real_madrid,
            2,
            1,
        )

        response = self.client.post(
            "/api/fixtures/",
            payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        match_id = response.data["id"]

        delete_response = self.client.delete(
            f"/api/fixtures/{match_id}/"
        )

        self.assertEqual(
            delete_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(
            Match.objects.filter(id=match_id).exists()
        )

    def test_api_completes_two_legged_tie_after_second_leg(self):
        self.round.tie_format = "TWO_LEGGED"
        self.round.save()

        first_leg = self.fixture_payload(
            self.barcelona,
            self.real_madrid,
            2,
            1,
            leg=1,
        )

        response = self.client.post(
            "/api/fixtures/",
            first_leg,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        self.tie.refresh_from_db()
        self.assertFalse(self.tie.is_completed)

        second_leg = self.fixture_payload(
            self.real_madrid,
            self.barcelona,
            2,
            0,
            leg=2,
        )

        second_leg["kickoff"] = "2027-03-10T20:00:00Z"

        response = self.client.post(
            "/api/fixtures/",
            second_leg,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        self.tie.refresh_from_db()

        self.assertTrue(self.tie.is_completed)
        self.assertEqual(self.tie.winner, self.real_madrid)



class KnockoutProgressionTests(KnockoutTestBase):

    def test_progress_completed_round(self):
        quarter_final = KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        # First completed tie: Barcelona qualifies.
        self.create_match(
            self.barcelona,
            self.real_madrid,
            2,
            0,
        )
        complete_knockout_tie(self.tie)

        # Create two additional clubs.
        arsenal = Club.objects.create(
            name="Arsenal",
            short_name="ARS",
            league=self.league,
            city="London",
            stadium_name="Emirates Stadium",
        )

        liverpool = Club.objects.create(
            name="Liverpool",
            short_name="LIV",
            league=self.league,
            city="Liverpool",
            stadium_name="Anfield",
        )

        second_tie = KnockoutTie.objects.create(
            knockout_round=self.round,
            home_club=arsenal,
            away_club=liverpool,
            winner=arsenal,
            is_completed=True,
        )

        # Advance both winners.
        new_ties = progress_knockout_round(self.round)

        self.assertEqual(len(new_ties), 1)

        new_tie = new_ties[0]

        self.assertEqual(
            new_tie.knockout_round,
            quarter_final,
        )
        self.assertEqual(
            new_tie.home_club,
            self.barcelona,
        )
        self.assertEqual(
            new_tie.away_club,
            arsenal,
        )
        self.assertFalse(new_tie.is_completed)
        self.assertIsNone(new_tie.winner)


    def test_cannot_progress_incomplete_round(self):
        KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        # The existing Round of 16 tie is not completed.
        self.assertFalse(self.tie.is_completed)

        with self.assertRaisesMessage(
            ValueError,
            "All knockout ties must be completed before progression.",
        ):
            progress_knockout_round(self.round)

        # No quarter-final ties should have been created.
        self.assertEqual(
            KnockoutTie.objects.filter(
                knockout_round__season=self.season,
                knockout_round__order=2,
            ).count(),
            0,
        )


    def test_cannot_progress_round_twice(self):
        quarter_final = KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        # Complete the first tie.
        self.create_match(
            self.barcelona,
            self.real_madrid,
            2,
            0,
        )
        complete_knockout_tie(self.tie)

        # Create a second completed tie.
        arsenal = Club.objects.create(
            name="Arsenal",
            short_name="ARS",
            league=self.league,
            city="London",
            stadium_name="Emirates Stadium",
        )

        liverpool = Club.objects.create(
            name="Liverpool",
            short_name="LIV",
            league=self.league,
            city="Liverpool",
            stadium_name="Anfield",
        )

        KnockoutTie.objects.create(
            knockout_round=self.round,
            home_club=arsenal,
            away_club=liverpool,
            winner=arsenal,
            is_completed=True,
        )

        # First progression succeeds.
        progress_knockout_round(self.round)

        self.assertEqual(
            KnockoutTie.objects.filter(
                knockout_round=quarter_final
            ).count(),
            1,
        )

        # Second progression must be rejected.
        with self.assertRaisesMessage(
            ValueError,
            "The next round already contains knockout ties.",
        ):
            progress_knockout_round(self.round)

        # Confirm no duplicate ties were created.
        self.assertEqual(
            KnockoutTie.objects.filter(
                knockout_round=quarter_final
            ).count(),
            1,
        )


    def test_cannot_progress_without_next_round(self):
        # Complete the existing knockout tie.
        self.create_match(
            self.barcelona,
            self.real_madrid,
            2,
            0,
        )

        complete_knockout_tie(self.tie)

        self.tie.refresh_from_db()

        self.assertTrue(self.tie.is_completed)
        self.assertEqual(self.tie.winner, self.barcelona)

        # Add a second completed tie so there
        # are two winners eligible to advance.
        arsenal = Club.objects.create(
            name="Arsenal",
            short_name="ARS",
            league=self.league,
            city="London",
            stadium_name="Emirates Stadium",
        )

        liverpool = Club.objects.create(
            name="Liverpool",
            short_name="LIV",
            league=self.league,
            city="Liverpool",
            stadium_name="Anfield",
        )

        KnockoutTie.objects.create(
            knockout_round=self.round,
            home_club=arsenal,
            away_club=liverpool,
            winner=arsenal,
            is_completed=True,
        )

        # No quarter-final round has been created.
        with self.assertRaisesMessage(
            ValueError,
            "No next knockout round exists for this season.",
        ):
            progress_knockout_round(self.round)

        # Verify no new ties were created.
        self.assertEqual(
            KnockoutTie.objects.filter(
                knockout_round__season=self.season
            ).count(),
            2,
        )



class KnockoutProgressionAPITests(KnockoutTestBase):

    def test_unauthenticated_user_cannot_progress_round(self):
        response = self.client.post(
            f"/api/knockout-rounds/{self.round.id}/progress/"
        )

        self.assertIn(
            response.status_code,
            [401, 403],
        )

        # Verify no new knockout ties were created.
        self.assertEqual(
            KnockoutTie.objects.count(),
            1,
        )


    def test_regular_user_cannot_progress_round(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        user = User.objects.create_user(
            username="regularuser",
            password="TestPassword123!",
        )

        self.assertFalse(user.is_staff)

        self.client.force_login(user)

        response = self.client.post(
            f"/api/knockout-rounds/{self.round.id}/progress/"
        )

        self.assertEqual(response.status_code, 403)

        # Ensure no new knockout ties were created.
        self.assertEqual(
            KnockoutTie.objects.count(),
            1,
        )



    def test_staff_user_can_progress_round(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        staff_user = User.objects.create_user(
            username="staffuser",
            password="TestPassword123!",
            is_staff=True,
        )

        self.client.force_login(staff_user)

        # Create the next knockout round.
        quarter_final = KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        # Complete Barcelona vs Real Madrid.
        self.create_match(
            self.barcelona,
            self.real_madrid,
            2,
            0,
        )

        complete_knockout_tie(self.tie)

        # Create another completed tie.
        arsenal = Club.objects.create(
            name="Arsenal",
            short_name="ARS",
            league=self.league,
            city="London",
            stadium_name="Emirates Stadium",
        )

        liverpool = Club.objects.create(
            name="Liverpool",
            short_name="LIV",
            league=self.league,
            city="Liverpool",
            stadium_name="Anfield",
        )

        KnockoutTie.objects.create(
            knockout_round=self.round,
            home_club=arsenal,
            away_club=liverpool,
            winner=arsenal,
            is_completed=True,
        )

        # Progress the round through the API.
        response = self.client.post(
            f"/api/knockout-rounds/{self.round.id}/progress/"
        )

        self.assertEqual(response.status_code, 201)

        self.assertEqual(
            response.data["message"],
            "Knockout round progressed successfully.",
        )

        self.assertEqual(
            len(response.data["created_ties"]),
            1,
        )

        # Verify the new tie was saved.
        new_tie = KnockoutTie.objects.get(
            knockout_round=quarter_final,
        )

        self.assertEqual(new_tie.home_club, self.barcelona)
        self.assertEqual(new_tie.away_club, arsenal)
        self.assertFalse(new_tie.is_completed)



    def test_staff_cannot_progress_incomplete_round(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        staff_user = User.objects.create_user(
            username="staff_incomplete",
            password="TestPassword123!",
            is_staff=True,
        )

        self.client.force_login(staff_user)

        # Create the next knockout round.
        quarter_final = KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        # The existing Barcelona vs Real Madrid
        # knockout tie is still incomplete.
        response = self.client.post(
            f"/api/knockout-rounds/{self.round.id}/progress/"
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.data["error"],
            "All knockout ties must be completed before progression.",
        )

        # No quarter-final ties should be created.
        self.assertFalse(
            KnockoutTie.objects.filter(
                knockout_round=quarter_final
            ).exists()
        )


    def test_staff_cannot_progress_round_twice(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        staff_user = User.objects.create_user(
            username="staff_duplicate",
            password="TestPassword123!",
            is_staff=True,
        )
        self.client.force_login(staff_user)

        quarter_final = KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        # Complete Barcelona vs Real Madrid.
        self.create_match(
            self.barcelona,
            self.real_madrid,
            2,
            0,
        )
        complete_knockout_tie(self.tie)

        # Create a second completed tie.
        arsenal = Club.objects.create(
            name="Arsenal",
            short_name="ARS",
            league=self.league,
            city="London",
            stadium_name="Emirates Stadium",
        )

        liverpool = Club.objects.create(
            name="Liverpool",
            short_name="LIV",
            league=self.league,
            city="Liverpool",
            stadium_name="Anfield",
        )

        KnockoutTie.objects.create(
            knockout_round=self.round,
            home_club=arsenal,
            away_club=liverpool,
            winner=arsenal,
            is_completed=True,
        )

        url = f"/api/knockout-rounds/{self.round.id}/progress/"

        # First request should succeed.
        first_response = self.client.post(url)
        self.assertEqual(first_response.status_code, 201)

        # Second request should be rejected.
        second_response = self.client.post(url)
        self.assertEqual(second_response.status_code, 400)

        self.assertEqual(
            second_response.data["error"],
            "The next round already contains knockout ties.",
        )

        # Only one quarter-final tie should exist.
        self.assertEqual(
            KnockoutTie.objects.filter(
                knockout_round=quarter_final
            ).count(),
            1,
        )



class KnockoutFixtureGenerationTests(KnockoutTestBase):

    def test_generate_single_leg_fixture(self):
        from django.utils import timezone
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        kickoff = timezone.now().replace(microsecond=0)

        fixtures = generate_knockout_fixtures(
            tie=self.tie,
            first_kickoff=kickoff,
        )

        self.assertEqual(len(fixtures), 1)

        match = Match.objects.get(knockout_tie=self.tie)

        self.assertEqual(match.home_club, self.barcelona)
        self.assertEqual(match.away_club, self.real_madrid)
        self.assertEqual(match.season, self.season)
        self.assertEqual(match.leg, 1)
        self.assertEqual(match.kickoff, kickoff)
        self.assertEqual(
            match.status,
            Match.MatchStatus.SCHEDULED,
        )

        self.assertIsNone(match.home_score)
        self.assertIsNone(match.away_score)


    def test_generate_two_legged_fixtures(self):
        from datetime import timedelta
        from django.utils import timezone
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        self.round.tie_format = "TWO_LEGGED"
        self.round.save(update_fields=["tie_format"])

        kickoff = timezone.now().replace(microsecond=0)

        fixtures = generate_knockout_fixtures(
            tie=self.tie,
            first_kickoff=kickoff,
            days_between_legs=7,
        )

        self.assertEqual(len(fixtures), 2)

        first_leg = Match.objects.get(
            knockout_tie=self.tie,
            leg=1,
        )

        second_leg = Match.objects.get(
            knockout_tie=self.tie,
            leg=2,
        )

        # Verify first-leg participants.
        self.assertEqual(first_leg.home_club, self.barcelona)
        self.assertEqual(first_leg.away_club, self.real_madrid)

        # Verify reversed second-leg participants.
        self.assertEqual(second_leg.home_club, self.real_madrid)
        self.assertEqual(second_leg.away_club, self.barcelona)

        # Verify kickoff dates.
        self.assertEqual(first_leg.kickoff, kickoff)
        self.assertEqual(
            second_leg.kickoff,
            kickoff + timedelta(days=7),
        )

        # Verify season and match status.
        for match in (first_leg, second_leg):
            self.assertEqual(match.season, self.season)
            self.assertEqual(
                match.status,
                Match.MatchStatus.SCHEDULED,
            )
            self.assertIsNone(match.home_score)
            self.assertIsNone(match.away_score)

    def test_cannot_generate_duplicate_fixtures(self):
        from django.utils import timezone
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        kickoff = timezone.now().replace(microsecond=0)

        generate_knockout_fixtures(
            tie=self.tie,
            first_kickoff=kickoff,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Fixtures already exist for this knockout tie.",
        ):
            generate_knockout_fixtures(
                tie=self.tie,
                first_kickoff=kickoff,
            )

        self.assertEqual(
            Match.objects.filter(
                knockout_tie=self.tie,
            ).count(),
            1,
        )

    def test_cannot_generate_fixtures_for_completed_tie(self):
        from django.utils import timezone
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        self.tie.winner = self.barcelona
        self.tie.is_completed = True
        self.tie.save(
            update_fields=["winner", "is_completed"]
        )

        kickoff = timezone.now().replace(microsecond=0)

        with self.assertRaisesMessage(
            ValueError,
            "Cannot generate fixtures for a completed tie.",
        ):
            generate_knockout_fixtures(
                tie=self.tie,
                first_kickoff=kickoff,
            )

        self.assertFalse(
            Match.objects.filter(
                knockout_tie=self.tie,
            ).exists()
        )

    def test_cannot_generate_fixtures_without_kickoff(self):
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        with self.assertRaisesMessage(
            ValueError,
            "A kickoff date is required.",
        ):
            generate_knockout_fixtures(
                tie=self.tie,
                first_kickoff=None,
            )

        self.assertFalse(
            Match.objects.filter(
                knockout_tie=self.tie,
            ).exists()
        )

    def test_cannot_generate_fixtures_with_invalid_leg_interval(self):
        from django.utils import timezone
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        self.round.tie_format = "TWO_LEGGED"
        self.round.save(update_fields=["tie_format"])

        kickoff = timezone.now().replace(microsecond=0)

        for invalid_interval in (0, -1, -7):
            with self.subTest(interval=invalid_interval):
                with self.assertRaisesMessage(
                    ValueError,
                    "Days between legs must be at least 1.",
                ):
                    generate_knockout_fixtures(
                        tie=self.tie,
                        first_kickoff=kickoff,
                        days_between_legs=invalid_interval,
                    )

                self.assertFalse(
                    Match.objects.filter(
                        knockout_tie=self.tie,
                    ).exists()
                )

    def test_cannot_generate_fixtures_with_invalid_kickoff_type(self):
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        for invalid_kickoff in ("2026-12-01", 123, True):
            with self.subTest(kickoff=invalid_kickoff):
                with self.assertRaisesMessage(
                    ValueError,
                    "Kickoff must be a valid datetime.",
                ):
                    generate_knockout_fixtures(
                        tie=self.tie,
                        first_kickoff=invalid_kickoff,
                    )

        self.assertFalse(
            Match.objects.filter(knockout_tie=self.tie).exists()
        )

    def test_cannot_generate_fixtures_with_naive_kickoff(self):
        from datetime import datetime
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        kickoff = datetime(2026, 12, 1, 20, 0)

        with self.assertRaisesMessage(
            ValueError,
            "Kickoff must include timezone information.",
        ):
            generate_knockout_fixtures(
                tie=self.tie,
                first_kickoff=kickoff,
            )

        self.assertFalse(
            Match.objects.filter(knockout_tie=self.tie).exists()
        )


from django.test import TransactionTestCase


class KnockoutFixtureConcurrencyTests(TransactionTestCase):

    def setUp(self):
        from datetime import date

        league = League.objects.create(
            name="La Liga",
            country="Spain",
        )

        barcelona = Club.objects.create(
            name="Barcelona",
            short_name="BAR",
            league=league,
            city="Barcelona",
            stadium_name="Camp Nou",
        )

        real_madrid = Club.objects.create(
            name="Real Madrid",
            short_name="RMA",
            league=league,
            city="Madrid",
            stadium_name="Santiago Bernabeu",
        )

        competition = Competition.objects.create(
            name="Champions League",
            competition_type="CONTINENTAL_CUP",
        )

        season = Season.objects.create(
            competition=competition,
            name="2026/27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
        )

        knockout_round = KnockoutRound.objects.create(
            season=season,
            name="ROUND_OF_16",
            order=1,
            tie_format="SINGLE_LEG",
        )

        self.tie = KnockoutTie.objects.create(
            knockout_round=knockout_round,
            home_club=barcelona,
            away_club=real_madrid,
        )

    def test_concurrent_fixture_generation(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from django.utils import timezone
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        kickoff = timezone.now().replace(microsecond=0)
        tie_id = self.tie.pk
        barrier = Barrier(2)

        def generate():
            try:
                tie = KnockoutTie.objects.get(pk=tie_id)

                barrier.wait(timeout=10)

                generate_knockout_fixtures(
                    tie=tie,
                    first_kickoff=kickoff,
                )

                return "created"

            except ValueError as exc:
                return str(exc)

            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(generate)
            second = executor.submit(generate)

            results = [
                first.result(timeout=30),
                second.result(timeout=30),
            ]

        self.assertCountEqual(
            results,
            [
                "created",
                "Fixtures already exist for this knockout tie.",
            ],
        )

        self.assertEqual(
            Match.objects.filter(
                knockout_tie=self.tie,
            ).count(),
            1,
        )


class KnockoutFixtureConstraintTests(KnockoutTestBase):

    def create_scheduled_fixture(self, leg):
        from django.utils import timezone

        return Match.objects.create(
            season=self.round.season,
            knockout_tie=self.tie,
            home_club=self.barcelona,
            away_club=self.real_madrid,
            kickoff=timezone.now(),
            leg=leg,
            status=Match.MatchStatus.SCHEDULED,
        )

    def test_database_rejects_duplicate_first_leg(self):
        from django.db import IntegrityError, transaction

        self.create_scheduled_fixture(leg=1)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_scheduled_fixture(leg=1)

        self.assertEqual(
            Match.objects.filter(
                knockout_tie=self.tie,
            ).count(),
            1,
        )

    def test_database_rejects_duplicate_second_leg(self):
        from django.db import IntegrityError, transaction

        self.round.tie_format = "TWO_LEGGED"
        self.round.save(update_fields=["tie_format"])

        self.create_scheduled_fixture(leg=2)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_scheduled_fixture(leg=2)

        self.assertEqual(
            Match.objects.filter(
                knockout_tie=self.tie,
            ).count(),
            1,
        )

    def test_database_rejects_missing_leg(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_scheduled_fixture(leg=None)

        self.assertFalse(
            Match.objects.filter(
                knockout_tie=self.tie,
            ).exists()
        )

    def test_database_rejects_invalid_leg(self):
        from django.db import IntegrityError, transaction

        for invalid_leg in (0, 3, 4):
            with self.subTest(leg=invalid_leg):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        self.create_scheduled_fixture(
                            leg=invalid_leg,
                        )

        self.assertFalse(
            Match.objects.filter(
                knockout_tie=self.tie,
            ).exists()
        )

    def test_database_allows_regular_fixture_without_leg(self):
        from django.utils import timezone

        match = Match.objects.create(
            league=self.league,
            home_club=self.barcelona,
            away_club=self.real_madrid,
            kickoff=timezone.now(),
            status=Match.MatchStatus.SCHEDULED,
        )

        self.assertIsNotNone(match.pk)
        self.assertIsNone(match.knockout_tie_id)
        self.assertIsNone(match.leg)


class KnockoutFixtureSerializerTests(KnockoutTestBase):

    def setUp(self):
        super().setUp()

        from django.utils import timezone

        for club in (self.barcelona, self.real_madrid):
            CompetitionEntry.objects.get_or_create(
                season=self.round.season,
                club=club,
            )

        self.payload = {
            "season": self.round.season_id,
            "knockout_tie": self.tie.pk,
            "home_club": self.barcelona.pk,
            "away_club": self.real_madrid.pk,
            "kickoff": timezone.now().isoformat(),
            "leg": 1,
            "status": "SCHEDULED",
        }

    def get_serializer(self, **overrides):
        from fixtures.serializers import MatchSerializer

        payload = self.payload.copy()
        payload.update(overrides)

        return MatchSerializer(data=payload)

    def test_valid_single_leg_fixture(self):
        serializer = self.get_serializer()

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )

    def test_missing_knockout_leg(self):
        serializer = self.get_serializer(leg=None)

        self.assertFalse(serializer.is_valid())
        self.assertIn("leg", serializer.errors)

    def test_invalid_knockout_leg(self):
        serializer = self.get_serializer(leg=3)

        self.assertFalse(serializer.is_valid())
        self.assertIn("leg", serializer.errors)

    def test_second_leg_rejected_for_single_leg_tie(self):
        serializer = self.get_serializer(
            leg=2,
            home_club=self.real_madrid.pk,
            away_club=self.barcelona.pk,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("leg", serializer.errors)

    def test_incorrect_knockout_club_order(self):
        serializer = self.get_serializer(
            home_club=self.real_madrid.pk,
            away_club=self.barcelona.pk,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("knockout_tie", serializer.errors)

    def test_missing_knockout_season(self):
        serializer = self.get_serializer(season=None)

        self.assertFalse(serializer.is_valid())
        self.assertIn("season", serializer.errors)

    def test_duplicate_knockout_leg(self):
        serializer = self.get_serializer()

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )
        serializer.save()

        duplicate = self.get_serializer()

        self.assertFalse(duplicate.is_valid())

    def test_leg_without_knockout_tie(self):
        serializer = self.get_serializer(
            knockout_tie=None,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("leg", serializer.errors)

    def test_valid_second_leg_fixture(self):
        self.round.tie_format = "TWO_LEGGED"
        self.round.save(update_fields=["tie_format"])

        serializer = self.get_serializer(
            leg=2,
            home_club=self.real_madrid.pk,
            away_club=self.barcelona.pk,
        )

        self.assertTrue(
            serializer.is_valid(),
            serializer.errors,
        )


class KnockoutAPIProtectionTests(KnockoutTestBase):

    def setUp(self):
        super().setUp()

        self.client = APIClient()

        for club in (self.barcelona, self.real_madrid):
            CompetitionEntry.objects.get_or_create(
                season=self.season,
                club=club,
            )

        self.payload = {
            "league": None,
            "home_club": self.barcelona.id,
            "away_club": self.real_madrid.id,
            "season": self.season.id,
            "knockout_tie": self.tie.id,
            "kickoff": "2027-02-17T20:00:00Z",
            "status": "SCHEDULED",
            "leg": 1,
        }

    def create_fixture(self):
        response = self.client.post(
            "/api/fixtures/",
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        return response.data["id"]

    def test_reject_create_for_completed_tie(self):
        self.tie.is_completed = True
        self.tie.winner = self.barcelona
        self.tie.save()

        response = self.client.post(
            "/api/fixtures/",
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.data,
        )

        self.assertIn("knockout_tie", response.data)

        self.assertFalse(
            Match.objects.filter(
                knockout_tie=self.tie
            ).exists()
        )

    def test_reject_fixture_detachment(self):
        match_id = self.create_fixture()

        response = self.client.patch(
            f"/api/fixtures/{match_id}/",
            {
                "knockout_tie": None,
                "leg": None,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.data,
        )

        self.assertIn("knockout_tie", response.data)

        match = Match.objects.get(pk=match_id)

        self.assertEqual(
            match.knockout_tie_id,
            self.tie.id,
        )

    def test_reject_fixture_reassignment(self):
        match_id = self.create_fixture()

        another_tie = KnockoutTie.objects.create(
            knockout_round=self.round,
            home_club=self.real_madrid,
            away_club=self.barcelona,
        )

        response = self.client.patch(
            f"/api/fixtures/{match_id}/",
            {
                "knockout_tie": another_tie.id,
                "home_club": self.real_madrid.id,
                "away_club": self.barcelona.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.data,
        )

        self.assertIn("knockout_tie", response.data)

        match = Match.objects.get(pk=match_id)

        self.assertEqual(
            match.knockout_tie_id,
            self.tie.id,
        )

    def test_allow_update_to_active_fixture(self):
        match_id = self.create_fixture()

        response = self.client.patch(
            f"/api/fixtures/{match_id}/",
            {"status": "POSTPONED"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data,
        )

        match = Match.objects.get(pk=match_id)

        self.assertEqual(match.status, "POSTPONED")

        self.tie.refresh_from_db()
        self.assertFalse(self.tie.is_completed)

    def test_allow_delete_from_active_tie(self):
        match_id = self.create_fixture()

        response = self.client.delete(
            f"/api/fixtures/{match_id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Match.objects.filter(pk=match_id).exists()
        )

        self.tie.refresh_from_db()
        self.assertFalse(self.tie.is_completed)

    def test_reject_duplicate_knockout_leg(self):
        self.create_fixture()

        response = self.client.post(
            "/api/fixtures/",
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.data,
        )

        self.assertEqual(
            Match.objects.filter(
                knockout_tie=self.tie,
                leg=1,
            ).count(),
            1,
        )



class KnockoutAPIConcurrencyTests(TransactionTestCase):

    def setUp(self):
        from datetime import date

        league = League.objects.create(
            name="La Liga",
            country="Spain",
        )

        barcelona = Club.objects.create(
            name="Barcelona",
            short_name="BAR",
            league=league,
            city="Barcelona",
            stadium_name="Camp Nou",
        )

        real_madrid = Club.objects.create(
            name="Real Madrid",
            short_name="RMA",
            league=league,
            city="Madrid",
            stadium_name="Santiago Bernabeu",
        )

        competition = Competition.objects.create(
            name="Champions League",
            competition_type="CONTINENTAL_CUP",
        )

        season = Season.objects.create(
            competition=competition,
            name="2026/27",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 6, 30),
        )

        knockout_round = KnockoutRound.objects.create(
            season=season,
            name="ROUND_OF_16",
            order=1,
            tie_format="SINGLE_LEG",
        )

        self.tie = KnockoutTie.objects.create(
            knockout_round=knockout_round,
            home_club=barcelona,
            away_club=real_madrid,
        )

        for club in (barcelona, real_madrid):
            CompetitionEntry.objects.create(
                season=season,
                club=club,
            )

        self.payload = {
            "league": None,
            "home_club": barcelona.id,
            "away_club": real_madrid.id,
            "season": season.id,
            "knockout_tie": self.tie.id,
            "kickoff": "2027-02-17T20:00:00Z",
            "status": "SCHEDULED",
            "leg": 1,
        }

    def test_concurrent_duplicate_fixture_creation(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from unittest.mock import patch
        from fixtures.views import MatchViewSet

        barrier = Barrier(2)
        original_create = MatchViewSet.perform_create

        def synchronized_create(view, serializer):
            barrier.wait(timeout=10)
            return original_create(view, serializer)

        def create_fixture():
            try:
                client = APIClient()

                response = client.post(
                    "/api/fixtures/",
                    self.payload.copy(),
                    format="json",
                )

                return response.status_code

            finally:
                connections.close_all()

        with patch.object(
            MatchViewSet,
            "perform_create",
            synchronized_create,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(create_fixture)
                second = executor.submit(create_fixture)

                results = [
                    first.result(timeout=30),
                    second.result(timeout=30),
                ]

        self.assertCountEqual(
            results,
            [
                status.HTTP_201_CREATED,
                status.HTTP_400_BAD_REQUEST,
            ],
        )

        self.assertEqual(
            Match.objects.filter(
                knockout_tie=self.tie,
                leg=1,
            ).count(),
            1,
        )

        self.tie.refresh_from_db()
        self.assertFalse(self.tie.is_completed)


    def test_concurrent_result_submissions(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from unittest.mock import patch
        from fixtures.views import MatchViewSet

        response = APIClient().post(
            "/api/fixtures/",
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        match_id = response.data["id"]

        barrier = Barrier(2)
        original_update = MatchViewSet.perform_update

        def synchronized_update(view, serializer):
            barrier.wait(timeout=10)
            return original_update(view, serializer)

        def submit_result(home_score, away_score):
            try:
                client = APIClient()

                response = client.patch(
                    f"/api/fixtures/{match_id}/",
                    {
                        "status": "FINISHED",
                        "home_score": home_score,
                        "away_score": away_score,
                    },
                    format="json",
                )

                return (
                    response.status_code,
                    home_score,
                    away_score,
                )

            finally:
                connections.close_all()

        with patch.object(
            MatchViewSet,
            "perform_update",
            synchronized_update,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(
                    submit_result, 2, 1
                )

                second = executor.submit(
                    submit_result, 0, 3
                )

                results = [
                    first.result(timeout=30),
                    second.result(timeout=30),
                ]

        self.assertCountEqual(
            [result[0] for result in results],
            [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
            ],
        )

        accepted_result = next(
            result for result in results
            if result[0] == status.HTTP_200_OK
        )

        match = Match.objects.get(pk=match_id)

        self.tie.refresh_from_db()

        self.assertTrue(self.tie.is_completed)

        self.assertEqual(match.status, "FINISHED")

        self.assertEqual(
            match.home_score,
            accepted_result[1],
        )

        self.assertEqual(
            match.away_score,
            accepted_result[2],
        )

        expected_winner = (
            self.tie.home_club
            if match.home_score > match.away_score
            else self.tie.away_club
        )

        self.assertEqual(
            self.tie.winner,
            expected_winner,
        )


    def test_concurrent_result_update_and_deletion(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from unittest.mock import patch
        from fixtures.views import MatchViewSet

        response = APIClient().post(
            "/api/fixtures/",
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        match_id = response.data["id"]

        barrier = Barrier(2)

        original_update = MatchViewSet.perform_update
        original_destroy = MatchViewSet.perform_destroy

        def synchronized_update(view, serializer):
            barrier.wait(timeout=10)
            return original_update(view, serializer)

        def synchronized_destroy(view, instance):
            barrier.wait(timeout=10)
            return original_destroy(view, instance)

        def update_fixture():
            try:
                response = APIClient().patch(
                    f"/api/fixtures/{match_id}/",
                    {
                        "status": "FINISHED",
                        "home_score": 2,
                        "away_score": 1,
                    },
                    format="json",
                )

                return response.status_code

            finally:
                connections.close_all()

        def delete_fixture():
            try:
                response = APIClient().delete(
                    f"/api/fixtures/{match_id}/"
                )

                return response.status_code

            finally:
                connections.close_all()

        with patch.object(
            MatchViewSet,
            "perform_update",
            synchronized_update,
        ), patch.object(
            MatchViewSet,
            "perform_destroy",
            synchronized_destroy,
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                update_future = executor.submit(update_fixture)
                delete_future = executor.submit(delete_fixture)

                update_status = update_future.result(timeout=30)
                delete_status = delete_future.result(timeout=30)

        self.tie.refresh_from_db()

        if update_status == status.HTTP_200_OK:
            self.assertEqual(
                delete_status,
                status.HTTP_400_BAD_REQUEST,
            )

            match = Match.objects.get(pk=match_id)

            self.assertEqual(match.status, "FINISHED")
            self.assertEqual(match.home_score, 2)
            self.assertEqual(match.away_score, 1)

            self.assertTrue(self.tie.is_completed)
            self.assertEqual(
                self.tie.winner,
                self.tie.home_club,
            )

        else:
            self.assertEqual(
                update_status,
                status.HTTP_404_NOT_FOUND,
            )

            self.assertEqual(
                delete_status,
                status.HTTP_204_NO_CONTENT,
            )

            self.assertFalse(
                Match.objects.filter(pk=match_id).exists()
            )

            self.assertFalse(self.tie.is_completed)
            self.assertIsNone(self.tie.winner)



class KnockoutProgressionFixtureTests(KnockoutTestBase):

    def setUp(self):
        super().setUp()

        from datetime import datetime, timezone

        self.kickoff = datetime(
            2027, 4, 6, 20, 0,
            tzinfo=timezone.utc,
        )

        self.next_round = KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        self.create_match(
            self.barcelona,
            self.real_madrid,
            2,
            0,
        )

        complete_knockout_tie(self.tie)

        self.arsenal = Club.objects.create(
            name="Arsenal",
            short_name="ARS",
            league=self.league,
            city="London",
            stadium_name="Emirates Stadium",
        )

        self.liverpool = Club.objects.create(
            name="Liverpool",
            short_name="LIV",
            league=self.league,
            city="Liverpool",
            stadium_name="Anfield",
        )

        KnockoutTie.objects.create(
            knockout_round=self.round,
            home_club=self.arsenal,
            away_club=self.liverpool,
            winner=self.arsenal,
            is_completed=True,
        )

        for club in (
            self.barcelona,
            self.real_madrid,
            self.arsenal,
            self.liverpool,
        ):
            CompetitionEntry.objects.get_or_create(
                season=self.season,
                club=club,
            )

    def test_progression_without_kickoff(self):
        from competitions.knockout import progress_knockout_round

        ties = progress_knockout_round(self.round)

        self.assertEqual(len(ties), 1)

        self.assertFalse(
            Match.objects.filter(
                knockout_tie__knockout_round=self.next_round,
            ).exists()
        )

    def test_progression_generates_single_leg_fixture(self):
        from competitions.knockout import progress_knockout_round

        self.next_round.tie_format = "SINGLE_LEG"
        self.next_round.save(update_fields=["tie_format"])

        ties = progress_knockout_round(
            self.round,
            first_kickoff=self.kickoff,
        )

        self.assertEqual(len(ties), 1)

        fixtures = Match.objects.filter(
            knockout_tie=ties[0],
        )

        self.assertEqual(fixtures.count(), 1)

        match = fixtures.get()

        self.assertEqual(match.home_club, self.barcelona)
        self.assertEqual(match.away_club, self.arsenal)
        self.assertEqual(match.season, self.season)
        self.assertEqual(match.leg, 1)
        self.assertEqual(match.kickoff, self.kickoff)
        self.assertEqual(match.status, "SCHEDULED")
        self.assertIsNone(match.home_score)
        self.assertIsNone(match.away_score)

    def test_progression_generates_two_legged_fixtures(self):
        from datetime import timedelta
        from competitions.knockout import progress_knockout_round

        ties = progress_knockout_round(
            self.round,
            first_kickoff=self.kickoff,
            days_between_legs=7,
        )

        self.assertEqual(len(ties), 1)

        fixtures = list(
            Match.objects.filter(
                knockout_tie=ties[0],
            ).order_by("leg")
        )

        self.assertEqual(len(fixtures), 2)

        first_leg, second_leg = fixtures

        self.assertEqual(first_leg.leg, 1)
        self.assertEqual(second_leg.leg, 2)

        self.assertEqual(first_leg.home_club, self.barcelona)
        self.assertEqual(first_leg.away_club, self.arsenal)

        self.assertEqual(second_leg.home_club, self.arsenal)
        self.assertEqual(second_leg.away_club, self.barcelona)

        self.assertEqual(first_leg.kickoff, self.kickoff)

        self.assertEqual(
            second_leg.kickoff,
            self.kickoff + timedelta(days=7),
        )

        for match in fixtures:
            self.assertEqual(match.status, "SCHEDULED")
            self.assertEqual(match.season, self.season)
            self.assertIsNone(match.home_score)
            self.assertIsNone(match.away_score)

    def test_progression_rolls_back_on_fixture_failure(self):
        from competitions.knockout import progress_knockout_round

        with self.assertRaisesMessage(
            ValueError,
            "Days between legs must be at least 1.",
        ):
            progress_knockout_round(
                self.round,
                first_kickoff=self.kickoff,
                days_between_legs=0,
            )

        self.assertFalse(
            KnockoutTie.objects.filter(
                knockout_round=self.next_round,
            ).exists()
        )

        self.assertFalse(
            Match.objects.filter(
                knockout_tie__knockout_round=self.next_round,
            ).exists()
        )

        self.tie.refresh_from_db()

        self.assertTrue(self.tie.is_completed)
        self.assertEqual(self.tie.winner, self.barcelona)



class KnockoutProgressionSchedulingAPITests(KnockoutTestBase):

    def setUp(self):
        super().setUp()

        from django.contrib.auth import get_user_model

        self.client = APIClient()

        staff_user = get_user_model().objects.create_user(
            username="scheduling_admin",
            password="TestPassword123!",
            is_staff=True,
        )

        self.client.force_login(staff_user)

        self.next_round = KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        self.create_match(
            self.barcelona,
            self.real_madrid,
            2,
            0,
        )

        complete_knockout_tie(self.tie)

        self.arsenal = Club.objects.create(
            name="Arsenal",
            short_name="ARS",
            league=self.league,
            city="London",
            stadium_name="Emirates Stadium",
        )

        self.liverpool = Club.objects.create(
            name="Liverpool",
            short_name="LIV",
            league=self.league,
            city="Liverpool",
            stadium_name="Anfield",
        )

        KnockoutTie.objects.create(
            knockout_round=self.round,
            home_club=self.arsenal,
            away_club=self.liverpool,
            winner=self.arsenal,
            is_completed=True,
        )

        for club in (
            self.barcelona,
            self.real_madrid,
            self.arsenal,
            self.liverpool,
        ):
            CompetitionEntry.objects.get_or_create(
                season=self.season,
                club=club,
            )

        self.url = (
            f"/api/knockout-rounds/{self.round.id}/progress/"
        )

        self.payload = {
            "first_kickoff": "2027-04-06T20:00:00Z",
            "days_between_legs": 7,
        }

    def assert_no_progression(self):
        self.assertFalse(
            KnockoutTie.objects.filter(
                knockout_round=self.next_round,
            ).exists()
        )

        self.assertFalse(
            Match.objects.filter(
                knockout_tie__knockout_round=self.next_round,
            ).exists()
        )

    def test_api_generates_two_legged_fixtures(self):
        from datetime import timedelta, datetime, timezone

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        tie = KnockoutTie.objects.get(
            knockout_round=self.next_round,
        )

        fixtures = list(
            Match.objects.filter(
                knockout_tie=tie,
            ).order_by("leg")
        )

        self.assertEqual(len(fixtures), 2)

        first_leg, second_leg = fixtures

        self.assertEqual(first_leg.leg, 1)
        self.assertEqual(second_leg.leg, 2)

        self.assertEqual(first_leg.home_club, self.barcelona)
        self.assertEqual(first_leg.away_club, self.arsenal)

        self.assertEqual(second_leg.home_club, self.arsenal)
        self.assertEqual(second_leg.away_club, self.barcelona)

        self.assertEqual(
            first_leg.kickoff,
            datetime(2027, 4, 6, 20, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(
            second_leg.kickoff,
            first_leg.kickoff + timedelta(days=7),
        )

        for match in fixtures:
            self.assertEqual(match.status, "SCHEDULED")
            self.assertEqual(match.season, self.season)

    def test_api_generates_single_leg_fixture(self):
        self.next_round.tie_format = "SINGLE_LEG"
        self.next_round.save(update_fields=["tie_format"])

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        fixtures = Match.objects.filter(
            knockout_tie__knockout_round=self.next_round,
        )

        self.assertEqual(fixtures.count(), 1)
        self.assertEqual(fixtures.get().leg, 1)

    def test_api_progression_without_scheduling(self):
        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        self.assertEqual(
            KnockoutTie.objects.filter(
                knockout_round=self.next_round,
            ).count(),
            1,
        )

        self.assertFalse(
            Match.objects.filter(
                knockout_tie__knockout_round=self.next_round,
            ).exists()
        )

    def test_api_rejects_invalid_kickoff(self):
        response = self.client.post(
            self.url,
            {
                "first_kickoff": "invalid-date",
                "days_between_legs": 7,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("first_kickoff", response.data)
        self.assert_no_progression()

    def test_api_rejects_invalid_leg_interval(self):
        for interval in (0, -1, 366):
            with self.subTest(interval=interval):
                response = self.client.post(
                    self.url,
                    {
                        "first_kickoff": self.payload["first_kickoff"],
                        "days_between_legs": interval,
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )

                self.assertIn(
                    "days_between_legs",
                    response.data,
                )

                self.assert_no_progression()

    def test_api_rejects_interval_without_kickoff(self):
        response = self.client.post(
            self.url,
            {"days_between_legs": 7},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("first_kickoff", response.data)
        self.assert_no_progression()

    def test_api_uses_default_leg_interval(self):
        from datetime import timedelta

        response = self.client.post(
            self.url,
            {
                "first_kickoff": self.payload["first_kickoff"],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )

        fixtures = list(
            Match.objects.filter(
                knockout_tie__knockout_round=self.next_round,
            ).order_by("leg")
        )

        self.assertEqual(len(fixtures), 2)

        self.assertEqual(
            fixtures[1].kickoff - fixtures[0].kickoff,
            timedelta(days=7),
        )



class KnockoutMultiTieRollbackTests(KnockoutTestBase):

    def setUp(self):
        super().setUp()

        from datetime import datetime, timezone

        self.kickoff = datetime(
            2027, 4, 6, 20, 0,
            tzinfo=timezone.utc,
        )

        self.next_round = KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        self.create_match(
            self.barcelona,
            self.real_madrid,
            2,
            0,
        )

        complete_knockout_tie(self.tie)

        club_pairs = [
            ("Arsenal", "ARS", "Liverpool", "LIV"),
            ("Bayern Munich", "BAY", "Borussia Dortmund", "BVB"),
            ("Inter Milan", "INT", "AC Milan", "ACM"),
        ]

        for home_name, home_short, away_name, away_short in club_pairs:

            home_club = Club.objects.create(
                name=home_name,
                short_name=home_short,
                league=self.league,
                city="Test City",
                stadium_name="Test Stadium",
            )

            away_club = Club.objects.create(
                name=away_name,
                short_name=away_short,
                league=self.league,
                city="Test City",
                stadium_name="Test Stadium",
            )

            KnockoutTie.objects.create(
                knockout_round=self.round,
                home_club=home_club,
                away_club=away_club,
                winner=home_club,
                is_completed=True,
            )

        for tie in KnockoutTie.objects.filter(
            knockout_round=self.round,
        ):
            for club in (tie.home_club, tie.away_club):
                CompetitionEntry.objects.get_or_create(
                    season=self.season,
                    club=club,
                )

    def test_multi_tie_fixture_generation_rollback(self):
        from unittest.mock import patch
        from competitions.knockout import progress_knockout_round
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        original_ties = list(
            KnockoutTie.objects.filter(
                knockout_round=self.round,
            ).order_by("id").values(
                "id",
                "winner_id",
                "is_completed",
            )
        )

        original_match_count = Match.objects.count()

        generated_ties = []

        def simulate_generation_failure(
            tie,
            first_kickoff,
            days_between_legs=7,
        ):
            if generated_ties:
                self.assertEqual(
                    Match.objects.filter(
                        knockout_tie__knockout_round=self.next_round,
                    ).count(),
                    2,
                )

                raise ValueError(
                    "Simulated second tie fixture generation failure."
                )

            fixtures = generate_knockout_fixtures(
                tie=tie,
                first_kickoff=first_kickoff,
                days_between_legs=days_between_legs,
            )

            generated_ties.append(tie.pk)

            return fixtures

        with patch(
            "competitions.knockout.generate_knockout_fixtures",
            side_effect=simulate_generation_failure,
        ) as mocked_generation:

            with self.assertRaisesMessage(
                ValueError,
                "Simulated second tie fixture generation failure.",
            ):
                progress_knockout_round(
                    self.round,
                    first_kickoff=self.kickoff,
                    days_between_legs=7,
                )

            self.assertEqual(mocked_generation.call_count, 2)

        self.assertEqual(len(generated_ties), 1)

        self.assertFalse(
            KnockoutTie.objects.filter(
                knockout_round=self.next_round,
            ).exists()
        )

        self.assertFalse(
            Match.objects.filter(
                knockout_tie__knockout_round=self.next_round,
            ).exists()
        )

        self.assertEqual(
            Match.objects.count(),
            original_match_count,
        )

        remaining_ties = list(
            KnockoutTie.objects.filter(
                knockout_round=self.round,
            ).order_by("id").values(
                "id",
                "winner_id",
                "is_completed",
            )
        )

        self.assertEqual(remaining_ties, original_ties)



class FullKnockoutTournamentTests(KnockoutTestBase):

    def setUp(self):
        super().setUp()

        from datetime import datetime, timezone

        self.kickoff = datetime(
            2027, 2, 16, 20, 0,
            tzinfo=timezone.utc,
        )

        self.round.tie_format = "TWO_LEGGED"
        self.round.save(update_fields=["tie_format"])

        self.quarter_final = KnockoutRound.objects.create(
            season=self.season,
            name="QUARTER_FINAL",
            order=2,
            tie_format="TWO_LEGGED",
        )

        self.semi_final = KnockoutRound.objects.create(
            season=self.season,
            name="SEMI_FINAL",
            order=3,
            tie_format="TWO_LEGGED",
        )

        self.final = KnockoutRound.objects.create(
            season=self.season,
            name="FINAL",
            order=4,
            tie_format="SINGLE_LEG",
        )

        self.clubs = [
            self.barcelona,
            self.real_madrid,
        ]

        club_details = [
            ("Arsenal", "ARS"),
            ("Liverpool", "LIV"),
            ("Manchester City", "MCI"),
            ("Manchester United", "MUN"),
            ("Bayern Munich", "BAY"),
            ("Borussia Dortmund", "BVB"),
            ("Inter Milan", "INT"),
            ("AC Milan", "ACM"),
            ("Juventus", "JUV"),
            ("Paris Saint-Germain", "PSG"),
            ("Atletico Madrid", "ATM"),
            ("Benfica", "BEN"),
            ("Porto", "POR"),
            ("Ajax", "AJA"),
        ]

        for name, short_name in club_details:
            club = Club.objects.create(
                name=name,
                short_name=short_name,
                league=self.league,
                city="Test City",
                stadium_name="Test Stadium",
            )

            self.clubs.append(club)

        for club in self.clubs:
            CompetitionEntry.objects.get_or_create(
                season=self.season,
                club=club,
            )

        for index in range(2, len(self.clubs), 2):
            KnockoutTie.objects.create(
                knockout_round=self.round,
                home_club=self.clubs[index],
                away_club=self.clubs[index + 1],
            )

    def complete_round(self, knockout_round):
        ties = list(
            KnockoutTie.objects.filter(
                knockout_round=knockout_round,
            ).order_by("id")
        )

        winners = []

        for tie in ties:
            fixtures = list(
                Match.objects.filter(
                    knockout_tie=tie,
                ).order_by("leg")
            )

            expected_count = (
                2 if knockout_round.tie_format == "TWO_LEGGED"
                else 1
            )

            self.assertEqual(len(fixtures), expected_count)

            for match in fixtures:
                self.assertEqual(match.status, "SCHEDULED")

                if match.home_club_id == tie.home_club_id:
                    match.home_score = 2
                    match.away_score = 0
                else:
                    match.home_score = 1
                    match.away_score = 1

                match.status = "FINISHED"

                match.save(update_fields=[
                    "home_score",
                    "away_score",
                    "status",
                ])

                complete_knockout_tie(tie)
                tie.refresh_from_db()

                if expected_count == 2 and match.leg == 1:
                    self.assertFalse(tie.is_completed)
                    self.assertIsNone(tie.winner)

            self.assertTrue(tie.is_completed)
            self.assertEqual(tie.winner, tie.home_club)

            winners.append(tie.winner_id)

        return winners

    def assert_round_structure(
        self,
        knockout_round,
        expected_ties,
        expected_fixtures,
        qualified_clubs,
    ):
        ties = KnockoutTie.objects.filter(
            knockout_round=knockout_round,
        )

        self.assertEqual(ties.count(), expected_ties)

        fixtures = Match.objects.filter(
            knockout_tie__knockout_round=knockout_round,
        )

        self.assertEqual(
            fixtures.count(),
            expected_fixtures,
        )

        participants = []

        for tie in ties:
            participants.extend([
                tie.home_club_id,
                tie.away_club_id,
            ])

            self.assertFalse(tie.is_completed)
            self.assertIsNone(tie.winner)

        self.assertCountEqual(
            participants,
            qualified_clubs,
        )

        self.assertEqual(
            len(participants),
            len(set(participants)),
        )

    def test_full_knockout_tournament_progression(self):
        from datetime import timedelta
        from competitions.knockout import (
            progress_knockout_round,
        )
        from competitions.fixture_generation import (
            generate_knockout_fixtures,
        )

        # Round of 16
        for tie in KnockoutTie.objects.filter(
            knockout_round=self.round,
        ):
            generate_knockout_fixtures(
                tie=tie,
                first_kickoff=self.kickoff,
                days_between_legs=7,
            )

        self.assert_round_structure(
            self.round,
            expected_ties=8,
            expected_fixtures=16,
            qualified_clubs=[
                club.id for club in self.clubs
            ],
        )

        round_of_16_winners = self.complete_round(
            self.round,
        )

        self.assertEqual(len(round_of_16_winners), 8)

        # Quarter-finals
        progress_knockout_round(
            self.round,
            first_kickoff=self.kickoff + timedelta(days=49),
            days_between_legs=7,
        )

        self.assert_round_structure(
            self.quarter_final,
            expected_ties=4,
            expected_fixtures=8,
            qualified_clubs=round_of_16_winners,
        )

        quarter_final_winners = self.complete_round(
            self.quarter_final,
        )

        self.assertEqual(len(quarter_final_winners), 4)

        # Semi-finals
        progress_knockout_round(
            self.quarter_final,
            first_kickoff=self.kickoff + timedelta(days=77),
            days_between_legs=7,
        )

        self.assert_round_structure(
            self.semi_final,
            expected_ties=2,
            expected_fixtures=4,
            qualified_clubs=quarter_final_winners,
        )

        semi_final_winners = self.complete_round(
            self.semi_final,
        )

        self.assertEqual(len(semi_final_winners), 2)

        # Final
        progress_knockout_round(
            self.semi_final,
            first_kickoff=self.kickoff + timedelta(days=109),
        )

        self.assert_round_structure(
            self.final,
            expected_ties=1,
            expected_fixtures=1,
            qualified_clubs=semi_final_winners,
        )

        final_winners = self.complete_round(self.final)

        self.assertEqual(len(final_winners), 1)
        self.assertEqual(
            final_winners[0],
            self.barcelona.id,
        )

        final_tie = KnockoutTie.objects.get(
            knockout_round=self.final,
        )

        self.assertTrue(final_tie.is_completed)
        self.assertEqual(final_tie.winner, self.barcelona)

        # Verify entire tournament
        tournament_ties = KnockoutTie.objects.filter(
            knockout_round__season=self.season,
        )

        tournament_fixtures = Match.objects.filter(
            knockout_tie__knockout_round__season=self.season,
        )

        self.assertEqual(tournament_ties.count(), 15)
        self.assertEqual(tournament_fixtures.count(), 29)

        self.assertEqual(
            tournament_ties.filter(is_completed=True).count(),
            15,
        )

        self.assertEqual(
            tournament_fixtures.filter(status="FINISHED").count(),
            29,
        )
