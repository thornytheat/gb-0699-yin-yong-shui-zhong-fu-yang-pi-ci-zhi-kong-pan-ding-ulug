# TRAP-14
# TRAP-02
from app.modules.m1_samples.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_sample_rows(result):
    assert len(result["raw"])==43

def test_sample_bom(sample):
    from app.reader import read_rows
    rows,_,_=read_rows("\ufeff"+sample,FIELDS)
    assert rows[0]["id"]=="001S"

def test_sample_conflict(result):
    assert any(r["reason"]=="VERSION_CONFLICT" for r in result["quarantine"])

def test_sample_missing(result):
    assert any(r["reason"]=="MISSING" for r in result["quarantine"])

def test_sample_empty():
    with pytest.raises(BusinessError):read_rows("",FIELDS)

def test_sample_header():
    with pytest.raises(BusinessError):read_rows(",".join(FIELDS),FIELDS)

def test_sample_id(result):
    assert result["raw"][0]["id"].startswith("00")