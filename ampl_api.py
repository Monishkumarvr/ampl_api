from fastapi import FastAPI, Request
from amplpy import AMPL, modules
import tempfile

app = FastAPI()

@app.on_event("startup")
def install_solver():
    modules.install("coin")  # Installs IPOPT on startup

@app.post("/solve")
async def solve_ampl_model(request: Request):
    model_text = await request.body()
    model_str = model_text.decode("utf-8")

    # Save model to temporary file
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".mod") as tmp:
        tmp.write(model_str)
        tmp_path = tmp.name

    ampl = AMPL()
    ampl.read(tmp_path)
    ampl.option["solver"] = "ipopt"

    result = {}
    try:
        ampl.solve()
        result["status"] = ampl.get_value("solve_result")
        result["variables"] = {
            k: v.value() for k, v in ampl.get_variables()
        }
        result["objective"] = ampl.get_value("z") if ampl.is_defined("z") else None
    except Exception as e:
        result["error"] = str(e)

    return result