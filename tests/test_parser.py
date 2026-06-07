"""Tests for the GuessIt-based parser."""
import pytest
from mediamatch.core.parser import parse_name


def test_simple_movie():
    result = parse_name("The.Dark.Knight.2008.mkv")
    assert result.title == "The Dark Knight"
    assert result.year == 2008


def test_tv_show_with_episode():
    result = parse_name("Breaking.Bad.S01E01.Pilot.mkv")
    assert "Breaking" in result.title
    assert result.season == 1
    assert result.episode == 1


def test_movie_with_parentheses():
    result = parse_name("Inception (2010)")
    assert result.title == "Inception"
    assert result.year == 2010


def test_fallback_no_year():
    result = parse_name("Some Random Movie Title")
    assert result.title != ""
    assert result.year is None
