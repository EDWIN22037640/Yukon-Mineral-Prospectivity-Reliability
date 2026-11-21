from pathlib import Path
import os,json,math,statistics
import numpy as np,pandas as pd
from docx import Document
from docx.shared import Cm,Pt,Inches,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
R=Path(__file__).resolve().parents[1];OUT=R/'06_informe';OUT.mkdir(exist_ok=True)
VAL=R/'04_validacion';FIG=R/'05_figuras'
a=json.loads((VAL/'METADATOS_V5_AUDITABLE.json').read_text(encoding='utf-8'))
cov=pd.read_csv(VAL/'RESUMEN_COBERTURA_INTERVALOS_90.csv')
test=pd.read_csv(VAL/'comparacion_test_581_SIN_COINCIDENCIAS.csv')
get=lambda prod,key: float(test[(test.producto==prod)&(test.metrica==key)].valor.iloc[0])
ks0,ks1=get('V4_PERFIL','KS_medio'),get('V5_COPULA','KS_medio')
w0,w1=get('V4_PERFIL','W1_normalizado'),get('V5_COPULA','W1_normalizado')
c0,c1=get('V4_PERFIL','error_matriz_correlacion_Frob'),get('V5_COPULA','error_matriz_correlacion_Frob')
s0,s1=get('V4_PERFIL','W1_proyecciones'),get('V5_COPULA','W1_proyecciones')

navy=RGBColor(25,42,67); blue=RGBColor(18,87,133); green=RGBColor(36,113,91); gray=RGBColor(92,104,113)
doc=Document();section=doc.sections[0];section.page_height=Cm(29.7);section.page_width=Cm(21);section.top_margin=Cm(2.1);section.bottom_margin=Cm(1.95);section.left_margin=Cm(2.25);section.right_margin=Cm(2.05)
styles=doc.styles;normal=styles['Normal'];normal.font.name='Aptos';normal.font.size=Pt(9.2);normal.font.color.rgb=navy;normal.paragraph_format.space_after=Pt(5);normal.paragraph_format.line_spacing=1.16
for kind,size,before,after in [('Title',22,0,12),('Heading 1',14,12,6),('Heading 2',11,8,4),('Subtitle',11,5,10)]:
 sty=styles[kind];sty.font.name='Aptos Display' if kind in ('Title','Heading 1') else 'Aptos';sty.font.size=Pt(size);sty.font.bold=kind!='Subtitle';sty.font.color.rgb=blue if kind.startswith('Heading') else navy;sty.paragraph_format.space_before=Pt(before);sty.paragraph_format.space_after=Pt(after)

# utility
def p(text='',style=None,boldfirst=None):
 q=doc.add_paragraph(style=style)
 if boldfirst and text.startswith(boldfirst):q.add_run(boldfirst).bold=True;q.add_run(text[len(boldfirst):])
 else:q.add_run(str(text))
 return q

def table(headers,rows,widths=None):
 t=doc.add_table(rows=1,cols=len(headers));t.style='Light Shading Accent 1';t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=True
 for i,v in enumerate(headers):t.rows[0].cells[i].text=str(v)
 for row in rows:
  cells=t.add_row().cells
  for i,x in enumerate(row):cells[i].text=str(x)
 for cell in t.rows[0].cells:
  tcpr=cell._tc.get_or_add_tcPr();shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'123B5D');tcpr.append(shade)
  for par in cell.paragraphs:
   for run in par.runs:run.font.bold=True;run.font.color.rgb=RGBColor(255,255,255);run.font.size=Pt(8)
 for row in t.rows[1:]:
  for cell in row.cells:
   cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   for par in cell.paragraphs:
    for run in par.runs:run.font.size=Pt(8)
 doc.add_paragraph().paragraph_format.space_after=Pt(0)
 return t

def figure(file,caption,width=16.6):
 q=doc.add_paragraph();q.alignment=WD_ALIGN_PARAGRAPH.CENTER
 q.add_run().add_picture(str(FIG/file),width=Cm(width))
 q=doc.add_paragraph(caption);q.alignment=WD_ALIGN_PARAGRAPH.CENTER;q.style='Caption';
 for run in q.runs:run.font.italic=True;run.font.size=Pt(8);run.font.color.rgb=gray

def heading(t,level=1):doc.add_heading(t,level=level)

def breakpage():doc.add_page_break()

# footer number
footer=section.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run('YUKÓN PCA V5  |  Informe técnico de auditoría y reconstrucción  •  ')
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)

# cover
p('GEOCIENCIAS · INTELIGENCIA ARTIFICIAL · CARTOGRAFÍA RÁSTER').runs[0].font.color.rgb=green
p('INFORME TÉCNICO V5',style='Title')
p('Reconstrucción de componentes principales con control multivariante e incertidumbre espacial para el estudio de prospectividad mineral en Yukón',style='Subtitle')
p('27 de octubre de 2026  ·  Área de estudio: Yukón, Canadá  ·  EPSG:3579')
doc.add_paragraph()
table(['INDICADOR','RESULTADO','ALCANCE'],[
 ('12.980','Celdas del dominio','110 × 118; geometría inferida'),
 ('763','Celdas con PC auténticos','Valores originales recuperados del repositorio'),
 ('12.217','Celdas reconstruidas','94,12 % estimadas, no medidas'),
 ('3.000','Perfiles PCA adicionales','Sin coordenadas espaciales'),
 ('40','Realizaciones de incertidumbre','Simulación condicionada para sensibilidad FDE-FT')])
heading('Resumen ejecutivo')
p('La V5 amplía el análisis V4 mediante transporte de cópula gaussiana de siete dimensiones, evaluación estadística con 581 perfiles de prueba sin coincidencia con anclas georreferenciadas, radios de error empíricos calibrados por bloques y 40 realizaciones correlacionadas para analizar la sensibilidad del modelo neuronal FDE-FT. Se preservan exactamente los siete componentes en las 763 celdas georreferenciadas. El ráster espacial principal se mantiene deliberadamente igual a V4 porque no existe evidencia suficiente para proclamar una mejora de localización con una corrección de distribuciones.')
p('Resultado principal: el error Frobenius de la matriz de correlación baja de 0,9672 a 0,7311 (−24,4 %); Wasserstein por proyecciones baja de 0,0913 a 0,0855 (−6,4 %). El KS medio permanece aproximadamente en 0,0373. Estas métricas evalúan perfiles sin geolocalización y no prueban fidelidad píxel a píxel.')

heading('1. Datos y geometría')
p('Fuentes originales: 01_Train_VO.csv (313 registros), 02_Train_PCA.csv (313), 03_Train_Pretext.csv (550), 04_Validation_Points.csv (40) y 013_Random.csv (3.000 perfiles). Entre VO/PCA y PRETEXT hay 862 registros con coordenadas válidas, correspondientes a 763 celdas distintas. En su intersección no se detectaron firmas PC incompatibles en una misma celda.')
p('La cuadrícula reconstruida es 118 columnas × 110 filas, con celdas de 1.200 m, origen aproximado (159.050 E, 977.585 N) en NAD83(CSRS)/Yukon Albers (EPSG:3579). Esta geometría procede de la consistencia entre muestras y ráster de trabajo: no es metadato recuperado del 02_PCA.tif original. El artículo científico menciona resolución de 1.100 m; la discrepancia permanece abierta.')

heading('2. Protocolo de mejora V5')
heading('2.1. Dos nociones de fidelidad',2)
p('Fidelidad espacial: la superficie PCA V4 validada por bloques se conserva sin cambios como producto principal para análisis de localización. Fidelidad multivariante: la V5 mejora la correlación entre componentes de la capa ajustada a datos distribucionales sin coordenadas. Ninguna métrica estadística puede validar dónde se encuentran realmente las anomalías.')
heading('2.2. Corrección multivariante con anclas inalteradas',2)
p('Se transforman rangos de las siete bandas no observadas a puntajes gaussianos, se corrige su matriz de correlación hacia la referencia de entrenamiento y se devuelven los cuantiles a la escala PCA. Un factor de mezcla limitado se elige exclusivamente con el subconjunto de validación. De los 607 perfiles inicialmente reservados, se excluyen 26 que coinciden con datos georreferenciados conocidos: el análisis principal utiliza 581 perfiles no superpuestos. Las 763 celdas auténticas no participan en la modificación de sus valores.')
heading('2.3. Evaluación del error con particiones espaciales',2)
p('Para cada componente se modela el valor absoluto de residuales fuera de bloque V4 utilizando distancias a controles, densidad de observaciones y dispersión local. Se evalúa una semianchura adaptativa al 90 % mediante cinco bloques espaciales, con un bloque distinto para calibración en cada iteración. Las particiones espaciales no garantizan intercambiabilidad: los intervalos se describen como bandas de error empíricas y no como garantías conformales.')
heading('2.4. Propagación hacia el clasificador original',2)
p('Se generan 40 campos aleatorios espacial y multivariadamente correlacionados, cuya amplitud se escala por radios de error y se anula sobre observaciones auténticas. Se aplica a cada realización la red FDE-FT original del archivo autoencoder_fine.h5. Las frecuencias superiores a 0,70 expresan estabilidad del puntaje frente a perturbaciones modeladas, nunca probabilidad calibrada de yacimiento.')

heading('3. Resultados cuantitativos')
heading('3.1. Perfil estadístico independiente de coordenadas',2)
table(['Métrica sobre 581 perfiles de prueba depurados','V4','V5','Interpretación'],[
 ('KS medio',f'{ks0:.4f}',f'{ks1:.4f}','Sin cambio práctico'),
 ('Wasserstein-1 normalizado',f'{w0:.4f}',f'{w1:.4f}','Mejora discreta'),
 ('Error de correlación, norma Frobenius',f'{c0:.4f}',f'{c1:.4f}','Mejora de 24,4 %'),
 ('Wasserstein por proyecciones',f'{s0:.4f}',f'{s1:.4f}','Mejora de 6,4 %')])
figure('03_TEST_RESERVADO_MULTIVARIANTE.png','Figura 1. Contraste fuera de la muestra de calibración. Comparación con 581 perfiles del conjunto reservado sin coincidencia con las anclas georreferenciadas.',16)
breakpage()
heading('3.2. Cobertura empírica y restricción espacial',2)
rows=[]
for x in cov.itertuples():rows.append([x.banda, f'{x.R2_V4_OOF:.3f}',f'{100*x.cobertura_CQR_estimada:.1f} %',f'{x.anchura_median_CQR:.2f}'])
table(['Componente','R² V4 fuera de bloque','Cobertura adaptativa','Anchura mediana'],rows)
p(f'Cobertura media adaptativa: {100*cov.cobertura_CQR_estimada.mean():.1f} %, evaluada descriptivamente sobre 763 observaciones en cinco bloques. La máscara V5 de soporte cercano retiene {a["mask_cells"]:,.0f} celdas (incluye anclas). El umbral combina distancia de 3 km y radios estimados menores a una desviación estándar en, al menos, cinco de siete componentes; es heurístico, no un criterio de certeza.')
figure('04_VALIDACION_INTERVALOS_ESPACIALES.png','Figura 2. Cobertura y anchura de las bandas de error. Se presenta la comparación con un radio global constante.',16)

heading('4. Cartografía y sensibilidad mineral')
figure('06_CARTOGRAFIA_COMO_ARTICULO_PROSPECTIVIDAD.png','Figura 3. Comparación FDE-FT con el esquema cromático de prospectividad y ocurrencias de entrenamiento. Sin sobreponer fallas no verificadas.',16)
ens=a['ensemble']
p(f'Fracción del dominio con puntaje FDE-FT ≥ 0,70: {100*ens["fraccion_score_070_espacial_base"]:.2f} % con entrada espacial y {100*ens["fraccion_score_070_copula_base"]:.2f} % con entrada de perfil corregido. El cambio de {100*(ens["fraccion_score_070_copula_base"]-ens["fraccion_score_070_espacial_base"]):.2f} puntos porcentuales es sensibilidad a insumos reconstruidos, no descubrimiento de depósitos. La amplitud promedio P95−P05 del puntaje es {ens["desacuerdo_promedio_fde_espacial"]:.3f} con el escenario espacial.')
figure('02_EVIDENCIA_DISTANCIA_Y_ERROR_90.png','Figura 4. Trazabilidad de observaciones georreferenciadas, distancia y radio empírico de error para PC2 y PC5.',16)

heading('5. Reglas de interpretación para publicación')
for title,body in [
 ('No existe reproducción fiel del ráster fuente.','El archivo 02_PCA.tif de los autores sigue sin recuperarse. El 94,12 % de las celdas se estima por modelos. Es incorrecto describir estas salidas como el conjunto íntegro de datos del artículo original.'),
 ('Posición y distribución no son intercambiables.','Los 3.000 perfiles sin coordenadas pueden evaluar distribuciones y correlaciones; no identifican anomalías en el mapa. La V5 mejora la semejanza multivariante, pero no demuestra un incremento del acierto geográfico.'),
 ('Dependencia espacial y calibración.','La cobertura de 90,2 % es una frecuencia empírica descriptiva con validación por bloques, no una cobertura teórica garantizada. El diseño y los mismos datos disponibles pueden introducir dependencia residual.'),
 ('Geometría y fallas.','La grilla de 1.200 m es inferida; el artículo menciona 1.100 m. No se agregó ninguna estructura geológica ficticia. Puede descargarse cartografía oficial de fallas de Yukon Geological Survey y contrastar su edición antes de superponerla.')]:
 q=doc.add_paragraph();q.add_run(title+' ').bold=True;q.add_run(body)
breakpage()
heading('6. Archivos recomendados')
table(['Producto','Finalidad'],[
 ('PCA7_V5_ESPACIAL_RECOMENDADO_7B.tif','Análisis espacial: mantiene el modelo V4, sin afirmar aumento de precisión'),
 ('PCA7_V5_COPULA_ORIGINAL_LIKE_7B.tif','Similitud de los siete componentes en distribución y correlación'),
 ('V5_RADIO_ERROR_90_EMPIRICO_7B.tif','Mapas de error por banda condicionados a validación espacial'),
 ('PCA7_V5_SOLO_SOPORTE_CERCANO_7B.tif','Escenario conservador de 1.372 celdas'),
 ('V5_ESPACIAL_FDE_MEDIANA.tif / ...IQR.tif','Sensibilidad del modelo FDE-FT a 40 realizaciones'),
 ('V5_PUNTOS_GEOLOGICOS_REALES.gpkg','763 celdas originales y 312 puntos de entrenamiento con clase')])
heading('7. Reproducción y referencias')
p('Python 3.10 o posterior. Instalar requirements.txt; ejecutar python 02_codigo/construir_v5.py y después python 02_codigo/cartografia_qgis.py. El proyecto incluye los rásteres V4 y sus predicciones fuera de muestra como insumos intermedios; para reproducir desde cero la fase V4 se requiere su script correspondiente. Se proporciona inventario SHA256 de los archivos.')
p('Mantilla-Dulcey, A., Goyes-Peñafiel, P., Báez-Rodríguez, R., & Khurama, S. (2024). Porphyry-type mineral prospectivity mapping with imbalanced data via prior geological transfer learning. Gondwana Research, 136, 236–250. https://doi.org/10.1016/j.gr.2024.09.004')
p('Datos y modelos: https://github.com/Anagabrielamantilla/TransferProspectivityLearning. Cartografía geológica oficial de fallas (no incorporada en los rásteres): https://open.yukon.ca/data/faults')
p('Alcance: producto metodológico para investigación, NO cartografía validada para decisiones de inversión, perforación o estimación de reservas.')

out=OUT/'Informe_Tecnico_Yukon_PCA_V5_Superior.docx';doc.save(out)
print(out)
