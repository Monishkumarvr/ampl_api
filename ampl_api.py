from fastapi import FastAPI, Request
from amplpy import AMPL, modules
import tempfile

app = FastAPI()

@app.on_event("startup")
def install_solver():
    modules.install("coin")  # Installs IPOPT solver for AMPL

@app.post("/solve")
async def solve_ampl_model(request: Request):
    model_text = await request.body()
    model_str = model_text.decode("utf-8")

    # Save model to a temporary .mod file
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".mod", delete=False) as f:
        f.write(model_str)
        model_file = f.name

    ampl = AMPL()
    ampl.read(model_file)
    ampl.option["solver"] = "ipopt"

    result = {}
    try:
        ampl.solve()
        result["status"] = ampl.get_value("solve_result")
        result["variables"] = {
            k: v.value() for k, v in ampl.get_variables()
        }
        if ampl.is_defined("z"):
            result["objective"] = ampl.get_value("z")
    except Exception as e:
        result["error"] = str(e)

    return result