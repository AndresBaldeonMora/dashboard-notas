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
OUTPUT_HTML_FILE = "dashboard_final.html"
NOTA_APROBATORIA = 11


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


def calcular_kpis(df: pd.DataFrame) -> dict:
    """Calcula KPIs considerando promedio por alumno (no por registro)."""
    promedio_por_alumno = df.groupby("Alumno")["PFINAL"].mean()
    total_alumnos = len(promedio_por_alumno)
    promedio_general = df["PFINAL"].mean()
    aprobados = int((promedio_por_alumno >= NOTA_APROBATORIA).sum())
    desaprobados = int((promedio_por_alumno < NOTA_APROBATORIA).sum())

    return {
        "total_alumnos": int(total_alumnos),
        "promedio_general": f"{promedio_general:.2f}",
        "aprobados": aprobados,
        "desaprobados": desaprobados,
    }


def preparar_datos_tabla(df: pd.DataFrame) -> str:
    df_desaprobados = df[df["PFINAL"] < NOTA_APROBATORIA][["Curso", "Alumno", "PFINAL"]]
    datos_agrupados = {curso: grupo.to_dict("records") for curso, grupo in df_desaprobados.groupby("Curso")}
    return json.dumps(datos_agrupados)


def preparar_datos_grafico(df: pd.DataFrame) -> dict:
    conteo = (
        df[df["PFINAL"] < NOTA_APROBATORIA]
        .groupby("Curso")["Alumno"]
        .count()
        .sort_values(ascending=False)
        .head(10)
    )
    return {"labels": list(conteo.index), "values": list(conteo.values)}


def generar_dashboard_html() -> str:
    data_por_csv = {}

    for csv_file in CSV_FILES:
        try:
            df = cargar_y_limpiar_datos(csv_file)
            kpis = calcular_kpis(df)
            datos_tabla_json = preparar_datos_tabla(df)
            grafico = preparar_datos_grafico(df)
            kpis = {k: (int(v) if isinstance(v, (np.int64, np.int32)) else v) for k, v in kpis.items()}
            data_por_csv[csv_file] = {
                "kpis": kpis,
                "datos": json.loads(datos_tabla_json),
                "grafico": grafico
            }
        except Exception as e:
            print(f"⚠️ Error procesando {csv_file}: {e}")

    data_json_global = json.dumps(data_por_csv, default=lambda o: int(o) if isinstance(o, (np.integer, int, float)) else str(o))

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard Académico</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {{
    --bg:#f8fafc; --card:#fff; --text:#1e293b; --muted:#64748b;
    --primary:#2563eb; --border:#e2e8f0; --danger:#dc2626;
}}
body {{
    margin:0; font-family:Inter,sans-serif; background:var(--bg); color:var(--text);
}}
header {{
    background:var(--card); padding:20px; border-bottom:1px solid var(--border);
}}
main {{ padding:24px; }}
select {{
    padding:8px 12px; border-radius:6px; border:1px solid var(--border);
}}
.stats {{
    display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
    gap:12px; margin:20px 0;
}}
.card {{
    background:var(--card); border:1px solid var(--border); border-radius:10px;
    padding:12px 16px;
}}
.card h3 {{ margin:0; font-size:14px; color:var(--muted); }}
.card .num {{ font-size:26px; font-weight:700; }}
canvas {{
    width:100% !important; max-height:400px;
}}
table {{
    width:100%; border-collapse:collapse; margin-top:10px;
}}
th,td {{ padding:10px; border-bottom:1px solid var(--border); text-align:left; }}
th {{ background:#f1f5f9; }}
td.nota-desaprobada {{ color:var(--danger); font-weight:600; }}
.no-data {{ color:var(--muted); text-align:center; padding:20px; }}
</style>
</head>
<body>
<header>
    <h1>📊 Dashboard de Notas Académicas</h1>
    <p>Selecciona el archivo CSV a analizar:</p>
    <select id="archivo-select">
        <option value="">-- Selecciona un archivo --</option>
        {''.join([f'<option value="{f}">{f}</option>' for f in CSV_FILES])}
    </select>
</header>

<main>
    <section class="stats" id="kpi-container"></section>
    <section>
        <canvas id="grafico-desaprobados"></canvas>
    </section>
    <section>
        <label for="curso-select"><b>Filtrar por curso:</b></label>
        <select id="curso-select"></select>
        <div id="tabla-container"></div>
    </section>
</main>

<script>
const DATA = {data_json_global};
let chart = null;

const archivoSelect = document.getElementById("archivo-select");
const cursoSelect = document.getElementById("curso-select");
const tablaContainer = document.getElementById("tabla-container");
const kpiContainer = document.getElementById("kpi-container");
const ctx = document.getElementById("grafico-desaprobados").getContext("2d");

archivoSelect.addEventListener("change", e => {{
    const file = e.target.value;
    if (!file) return;
    mostrarKpis(file);
    llenarCursos(file);
    dibujarGrafico(file);
    tablaContainer.innerHTML = "";
}});

function mostrarKpis(file) {{
    const k = DATA[file].kpis;
    kpiContainer.innerHTML = `
        <div class="card"><h3>Promedio General</h3><div class="num">${{k.promedio_general}}</div></div>
        <div class="card"><h3>Total Alumnos</h3><div class="num">${{k.total_alumnos}}</div></div>
        <div class="card"><h3>Alumnos Aprobados</h3><div class="num">${{k.aprobados}}</div></div>
        <div class="card"><h3>Alumnos Desaprobados</h3><div class="num">${{k.desaprobados}}</div></div>`;
}}

function llenarCursos(file) {{
    const cursos = Object.keys(DATA[file].datos);
    cursoSelect.innerHTML = '<option value="">-- Selecciona un curso --</option>' + cursos.map(c => `<option>${{c}}</option>`).join('');
    cursoSelect.onchange = e => mostrarTabla(file, e.target.value);
}}

function mostrarTabla(file, curso) {{
    const alumnos = DATA[file].datos[curso];
    if (!alumnos || alumnos.length === 0) {{
        tablaContainer.innerHTML = '<div class="no-data">No hay desaprobados en este curso.</div>';
        return;
    }}
    let html = '<table><thead><tr><th>Alumno</th><th>Nota Final</th></tr></thead><tbody>';
    alumnos.forEach(a => {{
        html += `<tr><td>${{a.Alumno}}</td><td class="nota-desaprobada">${{a.PFINAL}}</td></tr>`;
    }});
    tablaContainer.innerHTML = html + '</tbody></table>';
}}

function dibujarGrafico(file) {{
    const g = DATA[file].grafico;
    if (chart) chart.destroy();
    chart = new Chart(ctx, {{
        type: "bar",
        data: {{
            labels: g.labels,
            datasets: [{{
                label: "Cantidad de Desaprobados",
                data: g.values,
                backgroundColor: "#ef4444"
            }}]
        }},
        options: {{
            plugins: {{
                legend: {{ display: false }},
                title: {{
                    display: true,
                    text: "Top 10 cursos con más desaprobados"
                }}
            }},
            scales: {{
                y: {{ beginAtZero: true }}
            }}
        }}
    }});
}}
</script>
</body>
</html>
"""


def main():
    print("Generando dashboard HTML con KPIs reales de alumnos...")
    html = generar_dashboard_html()
    with open(OUTPUT_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Dashboard generado: {OUTPUT_HTML_FILE}")


if __name__ == "__main__":
    main()
