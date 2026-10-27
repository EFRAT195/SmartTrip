import pytest

from tools import check_trip


def test_trip_within_limits():
    attractions = [
        {"duration": 1.0, "price": 20},
        {"duration": 1.5, "price": 30},
    ]
    result = check_trip(attractions, max_hours=3, max_budget=60)
    assert result == {
        "valid": True,
        "total_hours": 2.5,
        "total_price": 50,
        "time_exceeded": False,
        "budget_exceeded": False,
    }


def test_trip_exceeds_time():
    attractions = [{"duration": 3, "price": 10}]
    result = check_trip(attractions, max_hours=2, max_budget=50)
    assert result["valid"] is False
    assert result["time_exceeded"] is True
    assert result["budget_exceeded"] is False


def test_trip_exceeds_budget():
    attractions = [{"duration": 1, "price": 100}]
    result = check_trip(attractions, max_hours=2, max_budget=80)
    assert result["valid"] is False
    assert result["time_exceeded"] is False
    assert result["budget_exceeded"] is True


def test_trip_exceeds_both_limits():
    attractions = [{"duration": 4, "price": 120}]
    result = check_trip(attractions, max_hours=2, max_budget=80)
    assert result["valid"] is False
    assert result["time_exceeded"] is True
    assert result["budget_exceeded"] is True


def test_trip_exactly_at_limits():
    attractions = [
        {"duration": 1, "price": 40},
        {"duration": 2, "price": 60},
    ]
    result = check_trip(attractions, max_hours=3, max_budget=100)
    assert result["valid"] is True
    assert result["total_hours"] == 3
    assert result["total_price"] == 100
    assert result["time_exceeded"] is False
    assert result["budget_exceeded"] is False
