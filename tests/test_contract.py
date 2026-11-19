# TRAP-15
# TRAP-07
# TRAP-06
from app.modules.m2_contract.rules import *
from app.errors import BusinessError
from app.numbers import number
from decimal import Decimal
import pytest

def test_contract_unit():
    assert measure("１,０００","ug/L")[0]==1

def test_contract_censored():
    assert measure("<0.001","mg/L")== (Decimal("0.001"),True)

def test_contract_sentinel():
    with pytest.raises(BusinessError):measure("N/A","mg/L")

def test_contract_negative():
    with pytest.raises(BusinessError):measure("-1","mg/L")

def test_contract_latest():
    assert latest([{"id":"a","batch":"b","analyte":"Pb","rev":1},{"id":"a","batch":"b","analyte":"Pb","rev":2}])[0]["rev"]==2

def test_contract_sample(result):
    assert len(result["effective"])==40

def test_contract_invalid(result):
    assert any(r["reason"]=="UNIT" for r in result["quarantine"])
def test_same_sample_id_different_analytes_kept(sample):
    from app.pipeline import run
    extra='\n'.join(line.replace(',Pb,',',As,') for line in sample.splitlines()[1:] if ',Pb,' in line)
    r=run(sample+'\n'+extra+'\n')
    assert len(r['effective'])==80
    assert {x['analyte'] for x in r['effective']}=={'Pb','As'}
