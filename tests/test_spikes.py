# TRAP-10
from app.modules.m4_spikes.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_spike_background():
    assert recovery(Decimal("0.003"),Decimal("0.013"),Decimal("0.01"))==100

def test_spike_zero():
    with pytest.raises(ValueError):recovery(Decimal(1),Decimal(2),Decimal(0))

def test_spike_low():
    assert recovery(Decimal(1),Decimal(1),Decimal(1))==0

def test_spike_boundary():
    assert recovery(Decimal(1),Decimal("1.8"),Decimal(1))==80

def test_spike_sample(result):
    assert len(result["recoveries"])==10

def test_spike_sample_exact(result):
    assert Decimal(result["recoveries"][0]["recovery_pct"])==100

def test_spike_sample_pass(result):
    assert all(r["status"]=="PASS" for r in result["recoveries"])