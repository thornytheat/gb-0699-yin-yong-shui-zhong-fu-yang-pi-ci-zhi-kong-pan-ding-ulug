from app.modules.m5_blanks.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_blank_equal():
    assert blank_check(Decimal("0.001"),Decimal("0.001"))=="PASS"

def test_blank_over():
    assert blank_check(Decimal("0.0011"),Decimal("0.001"))=="BLANK_FAIL"

def test_blank_limited():
    assert blank_check(Decimal("0.002"),Decimal("0.001"),True)=="CENSORED_REVIEW"

def test_blank_below():
    assert blank_check(Decimal("0.0005"),Decimal("0.001"),True)=="PASS"

def test_blank_sample(result):
    assert len(result["blank_checks"])==10

def test_blank_sample_fail(result):
    assert sum(r["status"]=="BLANK_FAIL" for r in result["blank_checks"])==1

def test_blank_sample_mdl(result):
    assert {r["mdl"] for r in result["blank_checks"]}=={"0.001"}