def execute(text):
    from app.pipeline import run
    result = run(text)
    return {"module": 8, "report": result["reports"][7], "quarantine": result["quarantine"],
            "balance": result["balance"]}
