from app.modules.m3_parallel.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_parallel_zero():
    assert pair_check(Decimal(0),Decimal(0))["status"]=="PASS"

def test_parallel_absolute():
    assert pair_check(Decimal("0.001"),Decimal("0.002"))["status"]=="PASS"

def test_parallel_relative():
    assert pair_check(Decimal("0.01"),Decimal("0.02"))["status"]=="PAIR_FAIL"

def test_parallel_censored():
    assert pair_check(Decimal(0),Decimal(1),censored=True)["status"]=="CENSORED_REVIEW"

def test_parallel_sample(result):
    assert len(result["parallel"])==10

def test_parallel_sample_fail(result):
    assert any(r["status"]=="PAIR_FAIL" for r in result["parallel"])

def test_parallel_method(result):
    assert any(r["method"]=="绝对差mg/L" for r in result["parallel"])