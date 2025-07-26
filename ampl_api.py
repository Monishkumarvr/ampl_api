from fastapi import FastAPI, Request
from amplpy import AMPL, modules
import tempfile

app = FastAPI()

@app.on_event("startup")
def install_solver():
    modules.install("coin")          # IPOPT

@app.post("/solve")
async def solve_ampl_model(request: Request):
    model_bytes = await request.body()
    model_str   = model_bytes.decode("utf-8")

    with tempfile.NamedTemporaryFile(mode="w+", suffix=".mod", delete=False) as f:
        f.write(model_str)
        model_file = f.name

    ampl = AMPL()
    ampl.read(model_file)
    ampl.option["solver"]         = "ipopt"
    ampl.option["solution_round"] = 3
    ampl.option["print_level"]    = 12

    out = {}
    try:
        ampl.solve()
        out["status"] = ampl.get_value("solve_result")

        # decision variables
        out["variables"] = {k: v.value() for k, v in ampl.get_variables()}

        # constraints (raw bodies – can be changed to .dual() etc. if you prefer)
        out["constraints"] = {k: c.body() for k, c in ampl.get_constraints()}

        # parameters
        out["variables"].update({k: p.value() for k, p in ampl.get_parameters()})

        # objective / total cost
        try:
            out["total_cost"] = ampl.get_value("z")          # if a z exists
        except RuntimeError:
            objectives = ampl.get_objectives()
            first_obj  = next(iter(objectives), None)
            out["total_cost"] = first_obj.get().value() if first_obj else None

    except Exception as e:
        out["status"] = "error"
        out["error"]  = str(e)

    return out