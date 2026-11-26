# Knockout Tournament Management

## 1. Overview

Milestone 3E introduces knockout tournament management
to the Football Hub backend.

The implementation supports single-leg and two-legged
knockout competitions, automatic winner determination,
round progression and fixture generation.

## 2. Supported Knockout Rounds

| Round | Identifier |
|-------|------------|
| Preliminary Round | PRELIMINARY |
| Round of 64 | ROUND_OF_64 |
| Round of 32 | ROUND_OF_32 |
| Round of 16 | ROUND_OF_16 |
| Quarter-finals | QUARTER_FINAL |
| Semi-finals | SEMI_FINAL |
| Final | FINAL |

Each round supports one of the following formats:

- SINGLE_LEG
- TWO_LEGGED

## 3. Data Models

### KnockoutRound

Defines a knockout stage within a competition season.

Key fields:

- season
- name
- order
- tie_format

Round names and ordering must be unique within a season.

### KnockoutTie

Represents a contest between two participating clubs.

Key fields:

- knockout_round
- home_club
- away_club
- winner
- is_completed

### Match

Stores individual fixtures associated with knockout ties.

Relevant fields:

- season
- knockout_tie
- home_club
- away_club
- leg
- kickoff
- status
- home_score
- away_score
- home_penalties
- away_penalties

Database constraints prevent duplicate legs and invalid
leg numbers for knockout fixtures.

## 4. Service Layer

### competitions/knockout.py

Responsibilities:

- Calculate aggregate scores.
- Determine knockout tie winners.
- Evaluate penalty shootout results.
- Complete knockout ties.
- Progress completed knockout rounds.
- Prevent duplicate round progression.

### competitions/fixture_generation.py

Responsibilities:

- Generate scheduled knockout fixtures.
- Generate one fixture for single-leg ties.
- Generate two fixtures for two-legged ties.
- Reverse home and away clubs for the second leg.
- Apply configurable scheduling intervals.
- Prevent duplicate fixture generation.

## 5. Winner Determination

### Single-Leg Ties

The winner is determined from the completed match score.

If the match is drawn, valid penalty shootout results
can determine the winner.

### Two-Legged Ties

The winner is determined using aggregate scores across
both completed fixtures.

If aggregate scores are equal, valid penalty shootout
results from the deciding leg can determine the winner.

A tie remains incomplete until a winner can be determined.

## 6. Round Progression

The progression service performs the following operations:

1. Lock the current knockout round.
2. Retrieve its knockout ties.
3. Verify that every tie is completed.
4. Validate the recorded winners.
5. Identify the next configured knockout round.
6. Prevent duplicate progression.
7. Pair qualifying clubs.
8. Create next-round knockout ties.
9. Generate fixtures when scheduling is requested.
10. Commit the database transaction.

If fixture generation fails, newly created ties and
fixtures are rolled back.

## 7. REST API

### List Knockout Rounds

    GET /api/knockout-rounds/

### Retrieve Knockout Round

    GET /api/knockout-rounds/{id}/

### Progress Knockout Round

    POST /api/knockout-rounds/{id}/progress/

The knockout round endpoints require staff permissions.

### Progression Without Scheduling

Request body:

    {}

Creates the next-round knockout ties without fixtures.

### Progression With Scheduling

Request body:

    {
        "first_kickoff": "2027-04-06T20:00:00Z",
        "days_between_legs": 7
    }

Scheduling parameters:

| Parameter | Description |
|-----------|-------------|
| first_kickoff | Initial fixture kickoff datetime |
| days_between_legs | Interval between first and second legs |

The default interval is seven days.

The API accepts intervals between 1 and 365 days.

### Response Status Codes

| Status | Description |
|--------|-------------|
| 201 | Round progressed successfully |
| 400 | Invalid request or progression rejected |
| 401/403 | Authentication or permission failure |
| 404 | Knockout round not found |

## 8. Data Integrity and Concurrency

The implementation uses:

- Django atomic database transactions.
- PostgreSQL row-level locking.
- Database uniqueness constraints.
- Database check constraints.
- Serializer validation.
- Completed knockout fixture protection.
- Duplicate fixture prevention.

Concurrency tests cover simultaneous fixture creation,
result submission and fixture update/deletion scenarios.

## 9. Automated Testing

The following scenarios have been verified:

- Single-leg winner determination.
- Two-legged aggregate winner determination.
- Penalty shootout winner determination.
- Incomplete knockout ties.
- Automatic tie completion.
- Round progression.
- Duplicate progression prevention.
- Automatic fixture generation.
- Invalid fixture validation.
- Database constraints.
- API permissions.
- Concurrent fixture creation.
- Concurrent result submission.
- Concurrent fixture update and deletion.
- API scheduling validation.
- Transaction rollback.
- Multi-tie transaction rollback.
- Full knockout tournament progression.

## 10. Full Tournament Simulation

A complete Champions League-style knockout tournament
was simulated using synthetic match results.

| Round | Clubs | Ties | Fixtures |
|-------|-------|------|----------|
| Round of 16 | 16 | 8 | 16 |
| Quarter-finals | 8 | 4 | 8 |
| Semi-finals | 4 | 2 | 4 |
| Final | 2 | 1 | 1 |
| Total | - | 15 | 29 |

The simulation successfully determined a final winner.

All 15 knockout ties were completed and all 29 fixtures
were finished.

## 11. Final Verification Results

Verification date: 26 November 2026

| Check | Result |
|-------|--------|
| Full backend test suite | 87/87 passed |
| Test failures | 0 |
| Django system issues | 0 |
| Pending model migrations | None |
| Git whitespace validation | Passed |

## 12. Current Limitations and Future Enhancements

- Round progression requires an explicit service or API call.
- Knockout pairing follows the order of existing ties.
- Competition-specific seeding and draw rules are not implemented.
- Generated ties share the supplied initial kickoff time.
- Advanced fixture scheduling and conflict detection are not implemented.
- The tournament winner is stored in the final knockout tie.
- A separate tournament champion record is not implemented.
- Not every possible concurrency scenario has been tested.
- Concurrent deletion of a knockout tie requires further handling.
- The full tournament simulation tests the service and database
  layers rather than an entire HTTP-based tournament workflow.
- Frontend tournament bracket visualisation remains future work.

## 13. Milestone Status

Milestone 3E: Implementation and regression testing complete.

Documentation and version control finalisation are the
remaining milestone closure activities.
