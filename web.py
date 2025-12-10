import pandas as pd
import numpy as np
import json
import re
import unicodedata
import os

# --- CONSTANTES ---
CSV_FILES = [
    "2024-2-Biologia.csv",
    "2024-2-Medicina Veterinaria.csv",
    "2025-1-Biologia.csv",
    "2025-1-Medicina Veterinaria.csv"
]
OUTPUT_HTML_FILE = "index.html"
NOTA_APROBATORIA = 11
MIN_CURSOS_JALADOS = 3  # Mínimo de cursos jalados para mostrar


def limpieza_agresiva(texto: str) -> str:
    texto = unicodedata.normalize("NFD", str(texto))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = texto.upper()
    texto = re.sub(r"[^A-Z\s]", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def cargar_y_limpiar_datos(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    col_alumno = next((c for c in df.columns if "alum" in c.lower() or "nombre" in c.lower()), "Nombre")
    col_curso = next((c for c in df.columns if "curso" in c.lower()), "Curso")
    col_pfinal = next((c for c in df.columns if "pfinal" in c.lower() or "nota" in c.lower()), "PFinal")

    df[col_alumno] = df[col_alumno].astype(str).apply(limpieza_agresiva)
    df[col_curso] = df[col_curso].astype(str).apply(lambda x: re.sub(r"^\d+\s*-\s*", "", x).strip())
    df[col_pfinal] = pd.to_numeric(df[col_pfinal], errors="coerce")

    df = df.rename(columns={col_alumno: "Alumno", col_curso: "Curso", col_pfinal: "PFINAL"})
    return df





def preparar_alumnos_criticos(df: pd.DataFrame) -> list:
    """Prepara lista de alumnos con 3 o más cursos desaprobados."""
    df_desaprobados = df[df["PFINAL"] < NOTA_APROBATORIA]
    
    # Contar cursos jalados por alumno
    conteo = df_desaprobados.groupby("Alumno").size()
    alumnos_criticos = conteo[conteo >= MIN_CURSOS_JALADOS].index.tolist()
    
    # Obtener detalles de cada alumno crítico
    resultado = []
    for alumno in alumnos_criticos:
        cursos_jalados = df_desaprobados[df_desaprobados["Alumno"] == alumno][["Curso", "PFINAL"]].to_dict("records")
        resultado.append({
            "nombre": alumno,
            "total_jalados": len(cursos_jalados),
            "cursos": cursos_jalados
        })
    
    # Ordenar por cantidad de cursos jalados (mayor a menor)
    resultado.sort(key=lambda x: x["total_jalados"], reverse=True)
    
    return resultado





def generar_dashboard_html() -> str:
    data_por_csv = {}

    for csv_file in CSV_FILES:
        try:
            df = cargar_y_limpiar_datos(csv_file)
            alumnos_criticos = preparar_alumnos_criticos(df)
            
            data_por_csv[csv_file] = {
                "alumnos_criticos": alumnos_criticos
            }
        except Exception as e:
            print(f"⚠️ Error procesando {csv_file}: {e}")

    data_json_global = json.dumps(data_por_csv, default=lambda o: int(o) if isinstance(o, (np.integer, int, float)) else str(o))

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Académico - Alumnos en Riesgo</title>
<style>
:root {{
    --bg:#f8fafc; --card:#fff; --text:#1e293b; --muted:#64748b;
    --primary:#2563eb; --border:#e2e8f0; --danger:#dc2626; --warning:#f59e0b;
}}
* {{ box-sizing: border-box; }}
body {{
    margin:0; font-family:Inter,sans-serif; background:var(--bg); color:var(--text);
}}
header {{
    background:var(--card); padding:24px; border-bottom:1px solid var(--border);
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}}
main {{ padding:32px; max-width: 1200px; margin: 0 auto; }}
select {{
    padding:10px 16px; border-radius:8px; border:1px solid var(--border);
    font-size: 15px; cursor: pointer; background: white;
    min-width: 300px; font-family: inherit;
}}
select:focus {{ outline: 2px solid var(--primary); outline-offset: 2px; border-color: var(--primary); }}
.stats {{
    display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
    gap:16px; margin:24px 0;
}}
.card {{
    background:var(--card); border:1px solid var(--border); border-radius:10px;
    padding:16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
table {{
    width:100%; border-collapse:collapse;
    background: var(--card); border-radius: 8px; overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
th,td {{ padding:14px 18px; text-align:left; }}
th {{ background:#f1f5f9; font-weight: 600; font-size: 13px; color: var(--muted); 
     text-transform: uppercase; letter-spacing: 0.5px; }}
td {{ border-bottom:1px solid var(--border); font-size: 14px; }}
tr:hover {{ background: #f8fafc; }}
tr:last-child td {{ border-bottom: none; }}
.badge {{
    display: inline-block; padding: 4px 10px; border-radius: 12px;
    font-size: 12px; font-weight: 600; background: var(--danger);
    color: white;
}}
.btn {{
    padding: 6px 14px; border-radius: 6px; border: none;
    background: var(--primary); color: white; cursor: pointer;
    font-size: 13px; font-weight: 500; transition: all 0.2s;
}}
.btn:hover {{ background: #1d4ed8; transform: translateY(-1px); }}
.no-data {{ color:var(--muted); text-align:center; padding:60px 20px; font-size: 15px; }}

section {{ margin-bottom: 40px; }}
section h2 {{ font-size: 22px; font-weight: 600; margin-bottom: 20px; color: var(--text); }}
/* Modal */
.modal {{
    display: none; position: fixed; z-index: 1000; left: 0; top: 0;
    width: 100%; height: 100%; background: rgba(0,0,0,0.5);
    animation: fadeIn 0.2s;
}}
.modal-content {{
    background: var(--card); margin: 5% auto; padding: 0;
    width: 90%; max-width: 600px; border-radius: 12px;
    box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);
    animation: slideDown 0.3s;
}}
.modal-header {{
    padding: 20px 24px; border-bottom: 1px solid var(--border);
    display: flex; justify-content: space-between; align-items: center;
}}
.modal-header h2 {{ margin: 0; font-size: 18px; font-weight: 600; }}
.close {{
    font-size: 28px; font-weight: 300; color: var(--muted);
    cursor: pointer; line-height: 1; transition: color 0.2s;
}}
.close:hover {{ color: var(--text); }}
.modal-body {{ padding: 24px; max-height: 60vh; overflow-y: auto; }}
.curso-item {{
    padding: 12px; border-radius: 8px; background: #f8fafc;
    margin-bottom: 8px; display: flex; justify-content: space-between;
    align-items: center;
}}
.curso-nombre {{ font-weight: 500; color: var(--text); }}
.curso-nota {{ font-weight: 700; color: var(--danger); font-size: 18px; }}

@keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes slideDown {{ from {{ transform: translateY(-20px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
</style>
</head>
<body>
<header>
    <h1>📊 Alumnos con 3 o más cursos desaprobados</h1>
    <select id="archivo-select" style="margin-top:16px;">
        <option value="">-- Selecciona un periodo académico --</option>
        {''.join([f'<option value="{f}">{f}</option>' for f in CSV_FILES])}
    </select>
</header>

<main>
    <section>
        <h2>Alumnos en Riesgo Académico (≥3 cursos jalados)</h2>
        <div id="tabla-container"></div>
    </section>
</main>

<!-- Modal -->
<div id="modal" class="modal">
    <div class="modal-content">
        <div class="modal-header">
            <h2 id="modal-titulo"></h2>
            <span class="close">&times;</span>
        </div>
        <div class="modal-body" id="modal-body"></div>
    </div>
</div>

<script>
const DATA = {data_json_global};

const archivoSelect = document.getElementById("archivo-select");
const tablaContainer = document.getElementById("tabla-container");
const modal = document.getElementById("modal");
const modalTitulo = document.getElementById("modal-titulo");
const modalBody = document.getElementById("modal-body");
const closeModal = document.querySelector(".close");

archivoSelect.addEventListener("change", e => {{
    const file = e.target.value;
    if (!file) {{
        tablaContainer.innerHTML = "";
        return;
    }}
    mostrarTabla(file);
}});

function mostrarTabla(file) {{
    const alumnos = DATA[file].alumnos_criticos;
    if (!alumnos || alumnos.length === 0) {{
        tablaContainer.innerHTML = '<div class="no-data">✓ No hay alumnos con 3 o más cursos desaprobados en este periodo</div>';
        return;
    }}
    let html = `<table>
        <thead><tr>
            <th style="width:60px;">#</th>
            <th>Alumno</th>
            <th style="width:180px; text-align:center;">Cursos Jalados</th>
            <th style="width:140px; text-align:center;">Acción</th>
        </tr></thead>
        <tbody>`;
    
    alumnos.forEach((a, idx) => {{
        html += `<tr>
            <td style="text-align:center; color:var(--muted);">${{idx + 1}}</td>
            <td>${{a.nombre}}</td>
            <td style="text-align:center;"><span class="badge">${{a.total_jalados}} cursos</span></td>
            <td style="text-align:center;"><button class="btn" onclick="verDetalle('${{a.nombre.replace(/'/g, "\\\\'")}}', '${{file}}')">Ver Detalle</button></td>
        </tr>`;
    }});
    
    tablaContainer.innerHTML = html + '</tbody></table>';
}}

function verDetalle(nombreAlumno, file) {{
    const alumno = DATA[file].alumnos_criticos.find(a => a.nombre === nombreAlumno);
    if (!alumno) return;
    
    modalTitulo.textContent = `${{alumno.nombre}} (${{alumno.total_jalados}} cursos jalados)`;
    
    let html = '';
    alumno.cursos.forEach(c => {{
        html += `<div class="curso-item">
            <span class="curso-nombre">${{c.Curso}}</span>
            <span class="curso-nota">${{c.PFINAL}}</span>
        </div>`;
    }});
    
    modalBody.innerHTML = html;
    modal.style.display = "block";
}}

closeModal.onclick = () => {{ modal.style.display = "none"; }};
window.onclick = e => {{ if (e.target === modal) modal.style.display = "none"; }};
</script>
</body>
</html>
"""


def main():
    print("🚀 Generando dashboard HTML con alumnos en riesgo académico...")
    html = generar_dashboard_html()
    with open(OUTPUT_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Dashboard generado: {OUTPUT_HTML_FILE}")
    print(f"📌 Mostrando solo alumnos con {MIN_CURSOS_JALADOS}+ cursos desaprobados")


if __name__ == "__main__":
    main()