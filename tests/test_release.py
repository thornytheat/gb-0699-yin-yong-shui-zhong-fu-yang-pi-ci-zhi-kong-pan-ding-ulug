# TRAP-19
from app.modules.m6_release.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_release_priority():
    assert verdict(["PAIR_FAIL","BLANK_FAIL"])=="BLANK_FAIL"

def test_release_order():
    assert verdict(["RECOVERY_FAIL","PAIR_FAIL"])==verdict(["PAIR_FAIL","RECOVERY_FAIL"])

def test_release_empty():
    assert verdict([])=="PASS"

def test_release_censored():
    assert verdict(["CENSORED_REVIEW"])=="CENSORED_REVIEW"

def test_release_sample(result):
    assert len(result["released"])==2

def test_release_blocked(result):
    assert result["blocked"] is True

def test_release_balance(result):
    assert result["balance"]=={"input":46,"accepted":40,"quarantined":5,"blank":1}