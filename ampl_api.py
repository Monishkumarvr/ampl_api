from fastapi import FastAPI, Request
from amplpy import AMPL, modules
import tempfile

app = FastAPI()

@app.on_event("startup")
def install_solver():
    modules.install("coin")  # Ensure IPOPT is installed

@app.post("/solve")
async def solve_ampl_model(request: Request):
    model_text = await request.body()
    model_str = model_text.decode("utf-8")

    # Save the AMPL model to a temporary file
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".mod", delete=False) as f:
        f.write(model_str)
        model_file = f.name

    ampl = AMPL()
    ampl.read(model_file)
    ampl.option["solver"] = "ipopt"
    ampl.option["solution_round"] = 3
    ampl.option["print_level"] = 12

    ampl_output = {}

    try:
        ampl.solve()
        if ampl.get_value("solve_result") == "solved":
            ampl_output["status"] = "solved"

            # Decision variables
            ampl_output["variables"] = {
                k: v.value() for k, v in ampl.get_variables()
            }

            # Constraints
            ampl_output["constraints"] = {
                k: v.body() for k, v in ampl.get_constraints()
            }

            # Parameters
            ampl_output["variables"].update({
                k: v.value() for k, v in ampl.get_parameters()
            })

            # Total cost (objective) if defined
            try:
                ampl_output["total_cost"] = ampl.get_value("z")
            except RuntimeError:
                try:
                    # Fallback to first available objective
                    obj = list(ampl.get_objectives().values())[0]
                    ampl_output["total_cost"] = obj.get().value()
                except:
                    ampl_output["total_cost"] = None
        else:
            ampl_output["status"] = ampl.get_value("solve_result")
            ampl_output["error"] = "AMPL solve did not result in status 'solved'"

    except Exception as e:
        ampl_output["status"] = "error"
        ampl_output["error"] = str(e)

    return ampl_output