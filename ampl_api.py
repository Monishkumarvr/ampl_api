from fastapi import FastAPI
from pydantic import BaseModel
from amplpy import AMPL, modules
import tempfile

app = FastAPI()

@app.on_event("startup")
def install_solver():
    modules.install("coin")          # IPOPT

# ---------- request schema ----------
class ModelRequest(BaseModel):
    model: str                       # AMPL text

@app.post("/solve")
def solve_ampl_model(req: ModelRequest):
    model_str = req.model            # ← plain AMPL text

    # save to temp file
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".mod", delete=False) as f:
        f.write(model_str)
        modfile = f.name

    ampl = AMPL()
    ampl.read(modfile)
    ampl.option["solver"] = "ipopt"

    out = {}
    try:
        ampl.solve()
        out["status"] = ampl.get_value("solve_result")
        out["variables"]   = {k: v.value()   for k, v in ampl.get_variables()}
        out["constraints"] = {k: c.body()    for k, c in ampl.get_constraints()}
        out["variables"].update({k: p.value() for k, p in ampl.get_parameters()})

        # objective (z or first objective)
        try:
            out["total_cost"] = ampl.get_value("z")
        except RuntimeError:
            name = next(iter(ampl.get_objectives().keys()), None)
            out["total_cost"] = ampl.get_value(name) if name else None
    except Exception as e:
        out["status"] = "error"
        out["error"]  = str(e)
    return out