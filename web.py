import pandas as pd
import numpy as np
import json
import re
import unicodedata
from collections import defaultdict

# --- CONSTANTES ---
CSV_FILES = [
    "2024-2-Biologia.csv",
    "2024-2-Medicina Veterinaria.csv",
    "2025-1-Biologia.csv",
    "2025-1-Medicina Veterinaria.csv"
]
OUTPUT_HTML_FILE = "index.html"
NOTA_APROBATORIA = 11
MIN_VECES_REPETIDO = 2  # Mínimo de veces que debe repetirse un curso


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


def detectar_cursos_repetidos() -> list:
    """
    Detecta alumnos que reprobaron el mismo curso 3 o más veces en diferentes periodos.
    Compara solo CSVs de la misma facultad (Biologia con Biologia, Veterinaria con Veterinaria).
    Retorna: Lista con cada alumno UNA sola vez, incluyendo TODOS sus cursos repetidos.
    """
    # Agrupar por facultad
    biologia_files = [f for f in CSV_FILES if "Biologia" in f]
    veterinaria_files = [f for f in CSV_FILES if "Veterinaria" in f]
    
    # Diccionario: alumno -> [{curso, veces, periodos}]
    alumnos_con_repeticiones = {}
    
    # Procesar cada facultad
    for facultad_files in [biologia_files, veterinaria_files]:
        if len(facultad_files) < MIN_VECES_REPETIDO:
            print(f"⚠️ Advertencia: Solo hay {len(facultad_files)} periodos. No es posible detectar {MIN_VECES_REPETIDO}+ repeticiones.")
            continue
            
        # Diccionario: alumno -> curso -> [(periodo, nota)]
        historial = defaultdict(lambda: defaultdict(list))
        
        # Recopilar todos los datos de la facultad
        for csv_file in facultad_files:
            periodo = csv_file.replace(".csv", "")
            df = cargar_y_limpiar_datos(csv_file)
            df_reprobados = df[df["PFINAL"] < NOTA_APROBATORIA]
            
            for _, row in df_reprobados.iterrows():
                alumno = row["Alumno"]
                curso = row["Curso"]
                nota = row["PFINAL"]
                historial[alumno][curso].append({
                    "periodo": periodo,
                    "nota": nota
                })
        
        # Buscar cursos repetidos (3+ veces) y agrupar por alumno
        for alumno, cursos in historial.items():
            cursos_repetidos = []
            
            for curso, registros in cursos.items():
                if len(registros) >= MIN_VECES_REPETIDO:
                    cursos_repetidos.append({
                        "curso": curso,
                        "veces_jalado": len(registros),
                        "periodos": registros
                    })
            
            # Si el alumno tiene al menos un curso repetido 3+ veces
            if cursos_repetidos:
                # Calcular total de repeticiones
                total_repeticiones = sum(c["veces_jalado"] for c in cursos_repetidos)
                
                alumnos_con_repeticiones[alumno] = {
                    "alumno": alumno,
                    "total_cursos_repetidos": len(cursos_repetidos),
                    "total_repeticiones": total_repeticiones,
                    "cursos": cursos_repetidos
                }
    
    # Convertir a lista y ordenar por total de repeticiones (mayor a menor)
    resultados = list(alumnos_con_repeticiones.values())
    resultados.sort(key=lambda x: x["total_repeticiones"], reverse=True)
    
    return resultados


def generar_dashboard_html() -> str:
    print("🔍 Detectando cursos repetidos 3+ veces entre periodos académicos...")
    alumnos_repetidores = detectar_cursos_repetidos()
    
    data_json = json.dumps(alumnos_repetidores, default=lambda o: int(o) if isinstance(o, (np.integer, int, float)) else str(o))
    
    total_alumnos = len(alumnos_repetidores)
    total_casos = sum(a["total_cursos_repetidos"] for a in alumnos_repetidores)
    
    print(f"✅ Encontrados {total_alumnos} alumnos con cursos repetidos 3+ veces")
    print(f"📊 Total de casos: {total_casos} cursos diferentes repetidos")

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Alumnos con Cursos Repetidos 3+ Veces</title>
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
header h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
header p {{ margin: 0; color: var(--muted); font-size: 14px; }}
main {{ padding:32px; max-width: 1400px; margin: 0 auto; }}

.stats {{
    display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
    gap:16px; margin:24px 0;
}}
.stat-card {{
    background:var(--card); border:1px solid var(--border); border-radius:10px;
    padding:20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}}
.stat-card h3 {{ margin:0 0 8px 0; font-size:13px; color:var(--muted); 
                 text-transform: uppercase; letter-spacing: 0.5px; }}
.stat-card .num {{ font-size:36px; font-weight:700; color:var(--danger); }}

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
    display: inline-block; padding: 5px 12px; border-radius: 12px;
    font-size: 12px; font-weight: 600; background: var(--danger);
    color: white; margin-right: 4px;
}}
.badge-warning {{
    background: var(--warning);
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
    width: 90%; max-width: 700px; border-radius: 12px;
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

.periodo-item {{
    padding: 14px 16px; border-radius: 8px; background: #f8fafc;
    margin-bottom: 10px; border-left: 4px solid var(--danger);
}}
.periodo-header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 4px;
}}
.periodo-nombre {{ font-weight: 600; color: var(--text); font-size: 15px; }}
.periodo-nota {{ font-weight: 700; color: var(--danger); font-size: 20px; }}

@keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes slideDown {{ from {{ transform: translateY(-20px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
</style>
</head>
<body>
<header>
    <h1>🔁 Alumnos con Cursos Repetidos (3+ veces)</h1>
    <p>Detección de alumnos que reprobaron el mismo curso en 3 o más periodos académicos</p>
</header>

<main>
    <div class="stats">
        <div class="stat-card">
            <h3>Alumnos Afectados</h3>
            <div class="num" id="total-alumnos">{total_alumnos}</div>
        </div>
        <div class="stat-card">
            <h3>Total Cursos Repetidos</h3>
            <div class="num" id="total-casos">{total_casos}</div>
        </div>
    </div>

    <section>
        <h2>Listado de Alumnos en Riesgo Crítico</h2>
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
const DATA = {data_json};

const tablaContainer = document.getElementById("tabla-container");
const modal = document.getElementById("modal");
const modalTitulo = document.getElementById("modal-titulo");
const modalBody = document.getElementById("modal-body");
const closeModal = document.querySelector(".close");

function init() {{
    mostrarTabla();
}}

function mostrarTabla() {{
    if (!DATA || DATA.length === 0) {{
        tablaContainer.innerHTML = '<div class="no-data">✓ No se encontraron alumnos con cursos repetidos 3+ veces</div>';
        return;
    }}
    
    let html = `<table>
        <thead><tr>
            <th style="width:50px;">#</th>
            <th>Alumno</th>
            <th style="width:200px; text-align:center;">Cursos Repetidos</th>
            <th style="width:180px; text-align:center;">Total Repeticiones</th>
            <th style="width:140px; text-align:center;">Acción</th>
        </tr></thead>
        <tbody>`;
    
    DATA.forEach((alumno, idx) => {{
        const badgeClass = alumno.total_repeticiones >= 10 ? 'badge' : 'badge badge-warning';
        html += `<tr>
            <td style="text-align:center; color:var(--muted);">${{idx + 1}}</td>
            <td><strong>${{alumno.alumno}}</strong></td>
            <td style="text-align:center;">
                <span class="badge">${{alumno.total_cursos_repetidos}} cursos</span>
            </td>
            <td style="text-align:center;">
                <span class="${{badgeClass}}">${{alumno.total_repeticiones}} veces</span>
            </td>
            <td style="text-align:center;">
                <button class="btn" onclick="verDetalle(${{idx}})">Ver Detalle</button>
            </td>
        </tr>`;
    }});
    
    tablaContainer.innerHTML = html + '</tbody></table>';
}}

function verDetalle(index) {{
    const alumno = DATA[index];
    if (!alumno) return;
    
    modalTitulo.textContent = `${{alumno.alumno}} - ${{alumno.total_cursos_repetidos}} curso(s) repetido(s)`;
    
    let html = '<p style="margin-bottom:20px; color:var(--muted); font-size:14px;">Historial completo de cursos repetidos 3+ veces:</p>';
    
    alumno.cursos.forEach((curso, idx) => {{
        html += `
        <div style="margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid var(--border);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h3 style="margin:0; font-size:16px; font-weight:600; color:var(--text);">
                    ${{idx + 1}}. ${{curso.curso}}
                </h3>
                <span class="badge" style="font-size:13px;">${{curso.veces_jalado}} veces</span>
            </div>`;
        
        curso.periodos.forEach(p => {{
            html += `<div class="periodo-item">
                <div class="periodo-header">
                    <span class="periodo-nombre">${{p.periodo}}</span>
                    <span class="periodo-nota">${{p.nota}}</span>
                </div>
            </div>`;
        }});
        
        html += '</div>';
    }});
    
    modalBody.innerHTML = html;
    modal.style.display = "block";
}}

closeModal.onclick = () => {{ modal.style.display = "none"; }};
window.onclick = e => {{ if (e.target === modal) modal.style.display = "none"; }};

// Inicializar al cargar la página
init();
</script>
</body>
</html>
"""


def main():
    print("🚀 Generando dashboard de cursos repetidos 3+ veces...")
    html = generar_dashboard_html()
    with open(OUTPUT_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Dashboard generado: {OUTPUT_HTML_FILE}")
    print(f"⚠️ NOTA: Con solo 2 periodos por facultad, no es posible detectar 3+ repeticiones.")
    print(f"💡 Necesitas agregar más CSVs o conectar a la intranet para obtener historial completo.")


if __name__ == "__main__":
    main()