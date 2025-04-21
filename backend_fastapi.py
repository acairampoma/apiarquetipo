from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import zipfile
import io
import os

app = FastAPI()

# CORS middleware para permitir peticiones desde cualquier origen (desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    # 2. Descomprimir y modificar el ZIP
    in_memory = io.BytesIO(zip_base)
    with zipfile.ZipFile(in_memory, "r") as zin:
        out_memory = io.BytesIO()
        with zipfile.ZipFile(out_memory, "w") as zout:
            pom_xml_path = f"{carpeta}pom.xml"
            contract_path = f"{carpeta}src/main/resources/contract/{contrato.filename}"
            contract_data = await contrato.read()
            for item in zin.infolist():
                file_data = zin.read(item.filename)
                if item.filename == pom_xml_path:
                    # Modificar el pom.xml para insertar el plugin antes de </plugins>
                    pom_content = file_data.decode("utf-8")
                    plugin_xml = f"""
            <plugin>
              <groupId>org.openapitools</groupId>
              <artifactId>openapi-generator-maven-plugin</artifactId>
              <version>6.2.0</version>
              <executions>
                <execution>
                  <goals>
                    <goal>generate</goal>
                  </goals>
                  <configuration>
                    <inputSpec>${{project.basedir}}/src/main/resources/contract/{contrato.filename}</inputSpec>
                    <generatorName>spring</generatorName>
                    <apiPackage>com.worldreactive.api</apiPackage>
                    <modelPackage>com.worldreactive.model</modelPackage>
                    <configOptions>
                      <interfaceOnly>true</interfaceOnly>
                      <useSpringBoot3>false</useSpringBoot3>
                      <delegatePattern>true</delegatePattern>
                      <apiNameSuffix>Delegate</apiNameSuffix>
                    </configOptions>
                  </configuration>
                </execution>
              </executions>
            </plugin>
"""
                    import re
                    # Busca </plugins> robustamente (permitiendo espacios/saltos de línea)
                    plugins_close = re.search(r"</plugins>\s*", pom_content, re.IGNORECASE)
                    if plugins_close:
                        idx = plugins_close.start()
                        pom_content = pom_content[:idx] + plugin_xml + pom_content[idx:]
                    else:
                        # fallback: inserta antes de </build>
                        build_close = re.search(r"</build>\s*", pom_content, re.IGNORECASE)
                        if build_close:
                            idx = build_close.start()
                            pom_content = pom_content[:idx] + plugin_xml + pom_content[idx:]
                        else:
                            # Si no hay, agrega al final
                            pom_content += plugin_xml
                    zout.writestr(item, pom_content.encode("utf-8"))
                else:
                    zout.writestr(item, file_data)
            # Agregar el contrato
            zout.writestr(contract_path, contract_data)
    out_memory.seek(0)
    return StreamingResponse(out_memory, media_type="application/zip", headers={"Content-Disposition": f"attachment;filename=proyecto.zip"})
