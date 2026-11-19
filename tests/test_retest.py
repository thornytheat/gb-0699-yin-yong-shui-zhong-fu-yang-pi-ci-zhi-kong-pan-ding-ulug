# TRAP-26
from app.modules.m7_retest.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_retest_version():
    assert next_version(1,2)==2

def test_retest_stale():
    with pytest.raises(ValueError):next_version(2,2)

def test_retest_backward():
    with pytest.raises(ValueError):next_version(2,1)

def test_retest_large():
    assert next_version(100,102)==102

def test_retest_sample(result):
    assert len(result["final"])==20

def test_retest_increment(result):
    assert all(r["required_version"]>r["current_version"] for r in result["final"])

def test_retest_batch(result):
    assert {r["batch"] for r in result["final"]}=={"B02"}