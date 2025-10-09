import PyPDF2
import pandas as pd
import re

def limpiar_nombre(nombre):
    """
    Limpia el campo de nombre eliminando códigos, números, puntos y espacios extra.
    """
    # Eliminar números y puntos
    nombre_limpio = re.sub(r'\d+|\.', '', nombre)
    # Eliminar número inicial tipo '2 ' o '05 '
    nombre_limpio = re.sub(r'^[0-9]+\s+', '', nombre_limpio)
    # Quitar espacios múltiples
    nombre_limpio = re.sub(r'\s+', ' ', nombre_limpio).strip()
    # Asegurar que quede en formato "APELLIDOS, NOMBRES"
    return nombre_limpio

def extraer_datos_evaluaciones(pdf_path):
    """
    Extrae información de cursos, alumnos y notas finales del PDF de evaluaciones
    """
    datos_completos = []
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            
            # Buscar el nombre del curso
            curso_match = re.search(r'ASIGNATURA:\s*\[[\d]+\]\s*-\s*[\w-]+\s*-\s*(.+?)\s+GRUPO:', text)
            if curso_match:
                nombre_curso = curso_match.group(1).strip()
            else:
                nombre_curso = "Desconocido"
            
            # Dividir el texto en líneas
            lineas = text.split('\n')
            
            for linea in lineas:
                # Buscar código de estudiante (8 a 10 dígitos)
                codigo_match = re.search(r'\d{8,10}', linea)
                if codigo_match:
                    # Buscar nota final (último número de 2 dígitos o 99)
                    pfinal_match = re.search(r'(\d{2})\s*$', linea)
                    if pfinal_match:
                        pfinal = pfinal_match.group(1)
                        
                        # Extraer todo el texto entre el código y la nota
                        # Esto es el "nombre completo" con basura incluida
                        nombre_raw = linea[codigo_match.end():pfinal_match.start()].strip()
                        
                        # Limpiar el nombre
                        nombre = limpiar_nombre(nombre_raw)
                        
                        # Agregar al listado
                        datos_completos.append({
                            'Curso': nombre_curso,
                            'Nombre': nombre,
                            'PFinal': pfinal
                        })
    
    return datos_completos


def guardar_csv(datos, output_path='notas_estudiantes.csv'):
    """
    Guarda los datos extraídos en un archivo CSV
    """
    df = pd.DataFrame(datos)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Archivo CSV guardado exitosamente en: {output_path}")
    print(f"Total de registros: {len(df)}")
    print(f"\nPrimeras filas:")
    print(df.head(10))


if __name__ == "__main__":
    pdf_path = '2024-2-BIOLOGIA.pdf'
    
    print("Extrayendo datos del PDF y limpiando nombres...")
    datos = extraer_datos_evaluaciones(pdf_path)
    
    guardar_csv(datos)
    
    df = pd.DataFrame(datos)
    print(f"\n--- Estadísticas ---")
    print(f"Total de cursos: {df['Curso'].nunique()}")
    print(f"Total de estudiantes: {len(df)}")
    print(f"\nCursos encontrados:")
    print(df['Curso'].value_counts())
