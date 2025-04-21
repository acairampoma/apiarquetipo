from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import requests, zipfile, io

app = FastAPI()

@app.post("/generar")
async def generar(arquetipo: str = Form(...), contrato: UploadFile = File(...)):
    # 1. Descargar ZIP base según arquetipo
    if arquetipo == "rest":
        url = "https://github.com/acairampoma/WorldReactiveRest/archive/refs/heads/main.zip"
        carpeta = "WorldReactiveRest-main/"
    else:
        url = "https://github.com/acairampoma/WorldReactiveProxy/archive/refs/heads/main.zip"
        carpeta = "WorldReactiveProxy-main/"
    zip_base = requests.get(url).content

    # 2. Descomprimir y agregar contrato
    in_memory = io.BytesIO(zip_base)
    with zipfile.ZipFile(in_memory, "r") as zin:
        out_memory = io.BytesIO()
        with zipfile.ZipFile(out_memory, "w") as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            # Agregar el contrato
            zout.writestr(f"{carpeta}src/main/resources/contract/{contrato.filename}", await contrato.read())
    out_memory.seek(0)
    return StreamingResponse(out_memory, media_type="application/zip", headers={"Content-Disposition": f"attachment;filename=proyecto.zip"})
