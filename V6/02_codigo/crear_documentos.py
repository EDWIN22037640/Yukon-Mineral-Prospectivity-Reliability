"""Creates scientific audit report and first full paper draft from computed CSV/JSON; no fabricated metrics."""
from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_ROW_HEIGHT_RULE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pandas as pd, json, os, numpy as np
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'03_resultados';F=ROOT/'04_figuras';O=ROOT/'05_informe';O.mkdir(exist_ok=True)
au=json.loads((R/'AUDITORIA_INVENTARIO.json').read_text(encoding='utf-8'))
rv=json.loads((R/'AUDITORIA_EFECTO_RASTER_V5.json').read_text(encoding='utf-8'))
metrics=pd.read_csv(R/'RESULTADOS_COMPARACION_CONSOLIDADA.csv'); b=pd.read_csv(R/'IC95_BOOTSTRAP_BLOQUES_CONTRASTES.csv')
external=pd.read_csv(R/'DIAGNOSTICO_MODELO_PUBLICADO_MUESTRA_EXTERNA.csv');fold=pd.read_csv(R/'AUDITORIA_PARTICIONES_Y_DISTANCIAS.csv')
# Colors
NAVY=RGBColor(17,39,66);TEAL=RGBColor(11,110,113);GRAY=RGBColor(81,96,111)
LIGHT='E9F3F4';LIGHTBLUE='E9EFF5';WHITE='FFFFFF'
def table_shade(cell,fill):
    tcPr=cell._tc.get_or_add_tcPr();sh=OxmlElement('w:shd');sh.set(qn('w:fill'),fill);tcPr.append(sh)
def cant_split(row):
    trPr=row._tr.get_or_add_trPr();item=OxmlElement('w:cantSplit');trPr.append(item)
def setup(doc,small=False):
    sec=doc.sections[0];sec.page_height=Cm(29.7);sec.page_width=Cm(21)
    sec.top_margin=Cm(2.3);sec.bottom_margin=Cm(2.0);sec.left_margin=Cm(2.5);sec.right_margin=Cm(2.3)
    st=doc.styles['Normal'];st.font.name='Aptos';st.font.size=Pt(9.7 if small else 10.2);st.font.color.rgb=NAVY
    st.paragraph_format.space_after=Pt(6);st.paragraph_format.line_spacing=1.15
    for name,sz in [('Title',20),('Heading 1',13.6),('Heading 2',11.4)]:
        s=doc.styles[name];s.font.name='Aptos Display';s.font.size=Pt(sz);s.font.bold=True;s.font.color.rgb=TEAL if name!='Title' else NAVY
        s.paragraph_format.space_before=Pt(14 if name!='Title' else 0);s.paragraph_format.space_after=Pt(5)
        s.paragraph_format.keep_with_next=True
    if 'Caption' not in [s.name for s in doc.styles]:doc.styles.add_style('Caption',WD_STYLE_TYPE.PARAGRAPH)
    s=doc.styles['Caption'];s.font.name='Aptos';s.font.size=Pt(8.3);s.font.italic=True;s.font.color.rgb=GRAY
    s.paragraph_format.space_after=Pt(7)
    header=sec.header.paragraphs[0];header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    run=header.add_run('YUKÓN  |  CIERRE METODOLÓGICO 2026');run.bold=True;run.font.size=Pt(7.8);run.font.color.rgb=GRAY
    foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.CENTER
    run=foot.add_run('Investigación reproducible · 27 octubre 2026  |  Página ');run.font.size=Pt(7.6);run.font.color.rgb=GRAY
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');foot._p.append(fld)
def title(doc,top,sub):
    p=doc.add_paragraph(style='Title');p.add_run(top)
    p=doc.add_paragraph(sub);p.style='Subtitle'
    p.paragraph_format.space_after=Pt(12)
def p(doc,text='',boldlead=None,style=None):
    pr=doc.add_paragraph(style=style)
    if boldlead:pr.add_run(boldlead).bold=True
    pr.add_run(text)
    return pr
def heading(doc,t,lv=1):doc.add_heading(t,level=lv)
def bullet(doc,txt):return doc.add_paragraph(txt,style='List Bullet')
def num(doc,txt):return doc.add_paragraph(txt,style='List Number')
def make_table(doc,cols,rows,widths=None,firstbold=True,size=8.25):
    tab=doc.add_table(rows=1,cols=len(cols));tab.style='Table Grid';tab.alignment=WD_TABLE_ALIGNMENT.CENTER
    for j,h in enumerate(cols):
        c=tab.rows[0].cells[j];c.text=str(h);table_shade(c,'183B50');c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for pr in c.paragraphs:
            for r in pr.runs:r.font.size=Pt(size);r.font.color.rgb=RGBColor(255,255,255);r.font.bold=True
    cant_split(tab.rows[0]);tab.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
    for i,row in enumerate(rows):
        cells=tab.add_row().cells;cant_split(tab.rows[-1]);
        for j,value in enumerate(row):
            cells[j].text=str(value)
            if i%2==1:table_shade(cells[j],'F2F6F8')
            cells[j].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for par in cells[j].paragraphs:
                par.paragraph_format.space_after=Pt(0)
                for rr in par.runs:
                    rr.font.size=Pt(size);rr.font.color.rgb=NAVY
                    if j==0 and firstbold:rr.bold=True
    if widths:
        for row in tab.rows:
            for cell,wi in zip(row.cells,widths):cell.width=Cm(wi)
    doc.add_paragraph().paragraph_format.space_after=Pt(1)
    return tab
def fig(doc,name,caption,width=15.6):
    path=F/name
    assert path.exists(),path
    pr=doc.add_paragraph();pr.alignment=WD_ALIGN_PARAGRAPH.CENTER
    pr.paragraph_format.space_after=Pt(2)
    pr.add_run().add_picture(str(path),width=Cm(width))
    doc.add_paragraph(caption,style='Caption')
def page(doc):doc.add_page_break()
def f3(x):return f'{x:.3f}'
def metric(pn,mo,col):return float(metrics[(metrics.protocolo==pn)&(metrics.modelo==mo)].iloc[0][col])

REPORT=Document();setup(REPORT)
title(REPORT,'AUDITORÍA DEFINITIVA DE LA INVESTIGACIÓN','Confiabilidad de modelos de aprendizaje automático para prospectividad mineral · Yukón, Canadá')
p(REPORT,'REPORTE DE CIERRE METODOLÓGICO · V6 · 27 de octubre de 2026',boldlead='ESTADO: ')
p(REPORT,'Alcance: auditoría integral de los datos publicados en 2024, comparación homogénea de tres algoritmos con particiones aleatorias y espaciales, evaluación de calibración y sensibilidad del ráster V5. El análisis principal utiliza exclusivamente firmas PCA originales con coordenadas válidas; no utiliza píxeles interpolados como muestras de entrenamiento o prueba.')
heading(REPORT,'Dictamen ejecutivo')
p(REPORT,'Los cinco objetivos pueden considerarse evaluados mediante análisis reproducibles y resultados verificables. No obstante, la validación externa geográficamente independiente y la reconstrucción exacta del ráster original permanecen imposibilitadas por las fuentes disponibles. Se puede redactar el artículo, pero no presentar estos vacíos como resueltos.')
make_table(REPORT,['Eje','Resultado verificable','Dictamen'],[
 ('Fuga de información','24/40 registros externos comparten firma PCA con entrenamiento; sin coordenadas externas','Cumplido con límite'),
 ('Comparación de algoritmos','RF, LR y FDE-FT; aleatoria, 20 km, 30 km y 30 km + buffer','Cumplido'),
 ('Incertidumbre y calibración','Brier, ECE10, bootstrap espacial de 1.800 réplicas y 40 simulaciones V5','Cumplido con alcance'),
 ('Reconstrucción PCA','Cambio de puntaje y reclasificación en 547/12.980 celdas; 763 anclas intactas','Cumplido como sensibilidad'),
 ('Robustez comparativa','Resultados dependientes de métrica y particiones; ningún ganador universal','Cumplido')],widths=[3.8,8.9,3.6],size=7.7)
heading(REPORT,'Hallazgos principales')
make_table(REPORT,['Indicador','Valor'],[
 ('Datos publicados','313 entrenamiento; 95 positivos y 218 negativos'),
 ('Registros únicos georreferenciados analizados','289: 71 positivos y 218 negativos'),
 ('Firma PCA repetida en entrenamiento','23 registros adicionales; todas positivas'),
 ('Registro inválido','1 coordenada (0, 0), excluida'),
 ('Validación externa 2024','40 registros; 24 coinciden en firma; 16 no coinciden (14 positivos, 2 negativos)'),
 ('Δ AUC RF, aleatoria − espacial 30 km',f3(metric('aleatoria','RF','AUC_medio')-metric('espacial30','RF','AUC_medio'))),
 ('Diferencia de categoría en cartografía V5','547 celdas (4,21 %), umbral de puntaje 0,70'),
 ('Celdas estimadas en PCA V5','12.217/12.980 (94,12 %)')],widths=[9.9,6.2],size=8.2)

heading(REPORT,'1. Integridad de los datos originales')
p(REPORT,'Se cotejaron 01_Train_VO.csv, 02_Train_PCA.csv y 04_Validation_Points.csv. Las 313 etiquetas de entrenamiento coinciden fila por fila entre las tablas X y PCA. Existen 13 grupos de firmas PCA repetidas que acumulan 23 filas excedentes, todas de clase positiva. Se descartó una ubicación (0,0); tras eliminar firmas redundantes, quedaron 289 ejemplos efectivos.')
p(REPORT,'En el conjunto externo, 24 de 40 filas se corresponden exactamente con una firma PCA del conjunto de entrenamiento (23 firmas distintas). Estas coincidencias conservan las mismas clases. Las 16 filas restantes incluyen solo 2 negativos, por lo que las métricas de ese subconjunto son inestables. Además, el CSV externo carece de coordenadas: no podemos verificar si las firmas coincidentes corresponden a los mismos lugares, píxeles o unidades geológicas.')
p(REPORT,'Importante: una coincidencia exacta en atributos prueba solapamiento de características, pero no demuestra por sí sola reutilización de los mismos sitios ni una actuación incorrecta de los autores.')
heading(REPORT,'2. Diseño reproducible de validación')
p(REPORT,'Comparación fuera de muestra con cinco particiones por réplica y dos réplicas por protocolo, aplicadas exactamente a los mismos 289 ejemplos. La alternativa aleatoria utiliza StratifiedKFold. Las espaciales agrupan ubicaciones en retículas de 20 y 30 km mediante StratifiedGroupKFold. El protocolo adicional de 30 km excluye del entrenamiento observaciones situadas a menos de 3 km de cualquier observación de prueba. Los parámetros del modelo se fijaron antes de evaluar; no se seleccionó el mejor umbral usando la prueba.')
p(REPORT,'Se evaluaron Random Forest (400 árboles, ponderación de clases), regresión logística con escalado ajustado exclusivamente en cada partición y FDE-FT con encoder original (7-100-8-6-4-2), pesos preentrenados importados de Keras y reajuste supervisado dentro de cada partición. El FDE-FT es una implementación adaptada en PyTorch (1.500 épocas); no reproduce exactamente el programa TensorFlow de 6.000 épocas de 2024.')
p(REPORT,'Distancia mínima entre entrenamiento y evaluación (mediana/descriptivo por fold): incluso en bloques de 30 km puede haber vecinos junto a los límites. La distancia mínima global entre folds fue de aproximadamente 1,20 km; con exclusión de 3 km subió por encima de 3,14 km. Los 30 km describen el tamaño del bloque, no una separación obligatoria entre todas las observaciones.')
fig(REPORT,'04_BLOQUES_Y_PUNTOS_ORIGINALES.png','Figura 1. Distribución de firmas PCA originales depuradas y esquema de bloques de 30 km; EPSG:3579.',width=13.0)

heading(REPORT,'3. Resultados definitivos de discriminación')
rows=[]
for m in ['RF','LR','FDE-FT']:
 rows.append((m,f3(metric('aleatoria',m,'AUC_medio')),f3(metric('espacial20',m,'AUC_medio')),
              f3(metric('espacial30',m,'AUC_medio')),f3(metric('espacial30_buffer3',m,'AUC_medio'))))
make_table(REPORT,['Modelo','AUC aleatoria','Esp. 20 km','Esp. 30 km','Esp. 30 km + buffer'],rows,size=7.75,widths=[3.1,3.1,3,3,4.2])
p(REPORT,'Las cifras corresponden a la media de dos evaluaciones OOF completas por protocolo; no son las métricas reportadas por Mantilla-Dulcey et al. (2024), porque se deduplicaron las muestras y se reentrenaron modelos con un procedimiento homogéneo.')
fig(REPORT,'01_AUC_PROTOCOLOS_TRES_MODELOS.png','Figura 2. AUC ROC comparativa (barras: promedio entre dos réplicas; líneas: desviación estándar entre réplicas).')
fig(REPORT,'02_ROC_CV_COMPARATIVO.png','Figura 3. Curvas ROC calculadas con predicciones fuera de muestra de la réplica primaria.')
heading(REPORT,'4. Intervalos de confianza y comparación entre modelos')
bs=b[b.tipo=='Diferencia AUC']
make_table(REPORT,['Contraste en réplica primaria','ΔAUC observado','IC 95 % bootstrap espacial'],[(
 'RF: aleatoria − espacial 30 km',f3(bs.iloc[0].estimacion),f'[{f3(bs.iloc[0].IC95_inf)}, {f3(bs.iloc[0].IC95_sup)}]'),
 ('FDE-FT − RF, espacial 30 km',f3(bs.iloc[1].estimacion),f'[{f3(bs.iloc[1].IC95_inf)}, {f3(bs.iloc[1].IC95_sup)}]'),
 ('RF: 30 km − 30 km + buffer',f3(bs.iloc[2].estimacion),f'[{f3(bs.iloc[2].IC95_inf)}, {f3(bs.iloc[2].IC95_sup)}]')],widths=[8,3.4,5.2],size=8)
p(REPORT,'Se utilizaron 1.800 remuestreos por grupos espaciales de 30 km manteniendo pares de predicciones. Los intervalos son exploratorios y condicionales a modelos ya entrenados; las dos réplicas de CV no constituyen experimentos independientes. La diferencia RF aleatoria–espacial fue positiva, pero el contraste FDE-FT frente a RF incluyó el cero: no se puede establecer superioridad estadística general de un algoritmo.')

heading(REPORT,'5. Calibración, sensibilidad y robustez')
rows=[]
for m in ['RF','LR','FDE-FT']:
 rows.append((m,f3(metric('espacial30',m,'Brier_medio')),f3(metric('espacial30',m,'ECE10_medio')),f3(metric('espacial30',m,'F1_medio')),f3(metric('espacial30',m,'sensibilidad_media'))))
make_table(REPORT,['Modelo','Brier ↓','ECE10 ↓','F1 ↑','Recall ↑'],rows,size=8.1,widths=[4,3,3,3,3])
p(REPORT,'Random Forest registra el menor Brier y ECE10 en esta configuración; FDE-FT logra mayor sensibilidad. ECE10 es sensible al número de intervalos y al tamaño muestral. El Brier combina discriminación y calibración y no debe interpretarse como una prueba aislada de calibración; también se presentan diagramas de confiabilidad.')
fig(REPORT,'03_CALIBRACION_BRIER.png','Figura 4. Frecuencia observada de ocurrencias según el puntaje previsto en validación OOF; las cifras Brier se indican en cada panel.')
heading(REPORT,'5.1. Comprobación adicional: calibración interna sin fuga de información',2)
p(REPORT,'Se realizó una segunda prueba con cinco bloques espaciales de 30 km. Dentro de cada entrenamiento externo se reservaron grupos espaciales distintos para ajustar una sigmoide de Platt. Las predicciones del bloque de prueba externo nunca participaron en ese ajuste. Se comparó el mismo modelo base, con entrenamiento reducido idéntico, antes y después de la calibración.')
make_table(REPORT,['Modelo','Brier bruto','Brier Platt','AUC bruto','AUC Platt'],[
 ('RF','0,150','0,160','0,777','0,756'),('LR','0,179','0,171','0,771','0,719'),
 ('FDE-FT','0,186','0,163','0,761','0,753')],size=7.8,widths=[4,3.1,3.1,3.1,3.1])
p(REPORT,'La calibración no produjo mejoras universales: redujo Brier en LR y FDE-FT, pero lo incrementó en RF; además, redujo AUC y sensibilidad a umbral 0,5 en este protocolo. El resultado refuerza que calibrar requiere prueba interna honesta y revisar el objetivo de uso, en vez de elegir un posprocesamiento por su apariencia visual.')
fig(REPORT,'08_CALIBRACION_PLATT_ESPACIAL_ANIDADA.png','Figura 5. Calibración sigmoide aprendida con datos internos espacialmente separados; resultados sobre grupos de prueba excluidos.',width=15.4)
fig(REPORT,'05_PRECISION_RECALL.png','Figura 6. Curvas precisión–sensibilidad con prevalencia muestral de 71/289 = 24,6 %.')

heading(REPORT,'6. Efecto de la reconstrucción PCA V5')
p(REPORT,f'Se verificaron las siete bandas GeoTIFF en EPSG:3579 (110 × 118 celdas). Las 763 celdas con valores originales mantienen la misma firma PCA en ambas reconstrucciones. Las {rv["celdas_totales"]-rv["celdas_originales_sin_alteracion"]:,} celdas restantes son estimaciones, equivalentes al 94,12 % del mapa. El ráster original 02_PCA.tif continúa sin recuperarse. La resolución inferida de 1.200 m difiere de los 1.100 m declarados en la publicación.')
p(REPORT,f'La comparación de puntajes FDE-FT entre la versión espacial y la corregida multivariantemente produjo cambio absoluto medio de {rv["media_cambio_absoluto_puntaje"]:.3f} y percentil 95 de {rv["p95_cambio_absoluto_puntaje"]:.3f}; {rv["celdas_cambian_categoria_umbral_0_70"]} celdas ({100*rv["fraccion_cambian_categoria_umbral_0_70"]:.2f} %) cambiaron de lado del umbral 0,70. La incertidumbre de entrada en 40 realizaciones se reflejó en un IQR mediano de puntaje {rv["IQR_modelo_original_perturbaciones_median"]:.3f}.')
p(REPORT,'La V5 mejora la similitud de distribuciones y correlaciones frente a perfiles originales sin coordenadas, pero eso NO demuestra mayor coincidencia geográfica. Ningún puntaje ráster se interpreta como probabilidad calibrada de descubrir un depósito.')
fig(REPORT,'06_MAPAS_SENSIBILIDAD_RECONSTRUCCION_V5.png','Figura 7. Puntajes FDE-FT por escenario de reconstrucción y diferencias absolutas. Los mapas usan coordenadas de la cuadrícula reconstruida, no la cartografía original completa.')

heading(REPORT,'7. Decisión sobre los cinco objetivos')
make_table(REPORT,['Objetivo específico','Estado verificable'],[
 ('1. Solapamiento y dependencia','Resuelto en atributos del entrenamiento y validación; no verificable geográficamente para los 40 externos.'),
 ('2. Validación aleatoria–espacial','Resuelto con tres algoritmos y cuatro protocolos homogéneos.'),
 ('3. Incertidumbre y estabilidad','Resuelto con AUC bootstrap, diagnósticos Brier/ECE y simulaciones de entrada; límites de independencia explícitos.'),
 ('4. Efecto de reconstrucción','Resuelto como sensibilidad: diferencias PCA, puntajes y 547 cambios de categoría.'),
 ('5. Modelos más robustos','Resuelto por criterio: RF mejor AUC medio y Brier; FDE-FT mejor recall; no superioridad universal.')],widths=[5.3,11.2],size=7.9)
heading(REPORT,'8. Limitaciones irrenunciables')
for x in [
 'La muestra externa no tiene coordenadas y 24/40 registros reproducen firmas del entrenamiento. No se presenta como validación espacial independiente.',
 'La submuestra externa sin coincidencias tiene únicamente 2 negativos; las métricas por subconjunto tienen elevada varianza.',
 'El encoder FDE-FT original fue preentrenado con covariables de la región completa; su uso es compatible con un protocolo transductivo, no con independencia de adquisición absoluta.',
 'Los bloques espaciales se diseñaron como sensibilidad 20/30 km; aún deben justificarse frente al alcance de autocorrelación geológica empírica si se exigiera extrapolación operacional.',
 'El 94,12 % de la cartografía PCA es interpolado y las celdas no equivalen a observaciones de campo; se usaron únicamente para sensibilidad.',
 'Los puntos negativos incluyen ubicaciones seleccionadas; las etiquetas no representan todas las áreas efectivamente verificadas como estériles. Tampoco son probabilidades de reservas.'
 ]:bullet(REPORT,x)
heading(REPORT,'9. Conclusión y alcance de publicación')
p(REPORT,'Se completaron los experimentos necesarios para responder las cinco preguntas metodológicas, con trazabilidad en archivos originales, predicciones fuera de muestra, remuestreo espacial y diagnóstico de sensibilidad. La tesis central —que la evaluación aleatoria produce puntajes más altos que la espacial en esta base— cuenta con respaldo experimental. Sin embargo, la ausencia de un conjunto externo espacialmente independiente y del ráster auténtico impide declarar validación universal o precisión geológica absoluta. El manuscrito científico puede elaborarse y someterse a revisión interna rigurosa antes de seleccionar revista.')
page(REPORT)
heading(REPORT,'Referencias principales')
for ref in [
 'Mantilla-Dulcey, A., Goyes-Peñafiel, P., Báez-Rodríguez, R., & Khurama, S. (2024). Porphyry-type mineral prospectivity mapping with imbalanced data via prior geological transfer learning. Gondwana Research, 136, 236–250. https://doi.org/10.1016/j.gr.2024.09.004',
 'Roberts, D. R., et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography, 40(8), 913–929. https://doi.org/10.1111/ecog.02881',
 'Valavi, R., Elith, J., Lahoz-Monfort, J. J., & Guillera-Arroita, G. (2019). blockCV: An R package for generating spatially or environmentally separated folds for k-fold cross-validation of species distribution models. Methods in Ecology and Evolution, 10(2), 225–232. https://doi.org/10.1111/2041-210X.13107',
 'Wang, Y., Khodadadzadeh, M., & Zurita-Milla, R. (2023). Spatial+: A new cross-validation method to evaluate geospatial machine learning models. International Journal of Applied Earth Observation and Geoinformation, 121, 103364. https://doi.org/10.1016/j.jag.2023.103364',
 'Repositorio fuente: https://github.com/Anagabrielamantilla/TransferProspectivityLearning'
 ]:p(REPORT,ref)
heading(REPORT,'Anexo. Evidencias y archivos auditables')
make_table(REPORT,['Recurso en el paquete','Contenido verificable'],[
 ('03_resultados/RESULTADOS_COMPARACION_CONSOLIDADA.csv','Cuatro protocolos × tres modelos × dos réplicas; AUC, F1, Brier, ECE10 y recall.'),
 ('03_resultados/PREDICCIONES_FUERA_DE_MUESTRA_TODAS.csv','6.936 predicciones fuera de muestra identificadas por fila, método y réplica.'),
 ('03_resultados/IC95_BOOTSTRAP_BLOQUES_CONTRASTES.csv','1.800 remuestreos condicionales por grupos espaciales de 30 km.'),
 ('03_resultados/RESULTADOS_CALIBRACION_ESPACIAL_ANIDADA.csv','Prueba interna de ajuste sigmoide sin utilizar los bloques de evaluación.'),
 ('03_resultados/AUDITORIA_EFECTO_RASTER_V5.json','12.980 celdas, 763 observadas; tasas de reclasificación verificadas.'),
 ('02_codigo/analisis_final.py','Implementación integral y reproducible; parámetros explícitos.')],widths=[8.2,8.1],size=7.5)
p(REPORT,'La reproducción se documenta en LEER_PRIMERO.md, EJECUCION_*.log y MANIFIESTO_SHA256.csv. Los datos y modelos originales mantienen su atribución al repositorio fuente y no deben redistribuirse públicamente sin revisar su licencia.')
REPORT.save(O/'Informe_Definitivo_Cierre_Objetivos_Yukon_V6.docx')

# Article draft
D=Document();setup(D,small=True)
title(D,'Evaluación de la confiabilidad de modelos de aprendizaje automático para la prospección mineral mediante validación espacial, detección de fuga de información y análisis de incertidumbre: caso Yukón, Canadá','Manuscrito científico · Versión de trabajo V1 · Resultados reproducidos el 27 de octubre de 2026')
p(D,'Autores, afiliaciones, declaraciones editoriales y formato de revista: por incorporar antes del envío.',boldlead='NOTA EDITORIAL. ')
heading(D,'Resumen')
p(D,'La validación aleatoria de modelos geoespaciales puede producir evaluaciones optimistas cuando hay dependencia espacial o firmas predictoras repetidas. Este estudio reevalúa la confiabilidad de modelos de prospección de sistemas tipo pórfido en Yukón, Canadá, utilizando los datos abiertos de Mantilla-Dulcey et al. (2024). Se auditaron 313 registros originales y 40 de validación, identificándose 23 registros redundantes en entrenamiento, una ubicación inválida y 24 registros externos con firmas PCA presentes en entrenamiento. La comparación principal utilizó 289 firmas únicas georreferenciadas (71 positivas, 218 negativas). Se evaluaron Random Forest, regresión logística y una red FDE-FT con encoder geológico original reentrenada en cada partición, mediante validación estratificada aleatoria, bloques espaciales de 20/30 km y bloques de 30 km con separación adicional de 3 km. En dos réplicas de cinco particiones, el AUC medio de Random Forest disminuyó de 0,862 (aleatoria) a 0,782 (30 km), y el de FDE-FT de 0,857 a 0,766. Un bootstrap espacial apareado produjo IC del 95 % [0,026; 0,141] para la diferencia de AUC aleatoria–espacial de Random Forest en una réplica. La calibración y el análisis de incertidumbre revelaron compensaciones entre modelos. Además, al modificar la reconstrucción PCA V5, 547 de 12.980 celdas cambiaron de clasificación respecto del umbral de puntaje 0,70. Los resultados respaldan la necesidad de validación espacial, auditorías de solapamiento y evaluación explícita de incertidumbre, sin atribuir precisión geológica certificada a superficies reconstruidas.')
p(D,'Palabras clave: prospectividad mineral; aprendizaje automático; validación espacial; fuga de información; FDE-FT; calibración; incertidumbre predictiva.')
heading(D,'Abstract')
p(D,'Random validation of geospatial models can yield optimistic estimates when spatial dependence and repeated predictor signatures are present. We reassessed the reliability of porphyry-type mineral prospectivity models in Yukon, Canada, using the open dataset of Mantilla-Dulcey et al. (2024). An audit of 313 training records and 40 external validation records identified 23 redundant training records, one invalid location, and 24 external rows whose PCA signatures also occurred in training. The main comparison involved 289 unique georeferenced signatures (71 positives, 218 negatives). Random Forest, logistic regression, and a fine-tuned FDE-FT network initialized from the authors’ pretrained geological encoder were evaluated using random stratified cross-validation, 20/30-km spatial blocks, and 30-km blocks with an additional 3-km exclusion buffer. Across two five-fold replications, mean Random Forest AUC declined from 0.862 (random) to 0.782 (30-km blocks), while FDE-FT declined from 0.857 to 0.766. A paired spatial-cluster bootstrap yielded a conditional 95% interval of [0.026, 0.141] for the Random Forest random-minus-spatial AUC difference in one replication. Calibration diagnostics and uncertainty analyses highlighted performance trade-offs. Changing the V5 PCA reconstruction altered the ≥0.70 score classification in 547 of 12,980 raster cells. The findings support spatially aware validation, explicit overlap auditing, and uncertainty analysis; reconstructed maps should not be treated as verified geologic observations.')
p(D,'Keywords: mineral prospectivity; machine learning; spatial cross-validation; information leakage; transfer learning; calibration; predictive uncertainty.')
heading(D,'1. Introducción')
p(D,'La cartografía de prospectividad mineral integra información geológica, geoquímica y geofísica para jerarquizar áreas de exploración. Los métodos de aprendizaje automático pueden aprovechar relaciones no lineales y evidencias continuas, pero las ocurrencias minerales constituyen eventos raros y espacialmente agrupados, de modo que la estimación del rendimiento predictivo depende de cómo se definan los conjuntos de entrenamiento y evaluación (Mantilla-Dulcey et al., 2024).')
p(D,'La validación aleatoria convencional supone una independencia entre observaciones que rara vez se cumple plenamente en bases de datos geocientíficas. En datos estructurados espacialmente, la proximidad de observaciones asignadas a grupos opuestos puede subestimar el error de predicción y favorecer conclusiones demasiado optimistas (Roberts et al., 2017; Valavi et al., 2019). Los métodos de partición espacial y los esquemas que integran distancia y atributos se han propuesto para evaluar mejor la capacidad de generalización regional (Wang et al., 2023).')
p(D,'Mantilla-Dulcey et al. (2024) desarrollaron un modelo de transferencia de aprendizaje geológico para prospección tipo pórfido en Yukón. Los autores publicaron los CSV y pesos neuronales, lo que ofrece una oportunidad excepcional para reexaminar la independencia de las etiquetas, la estabilidad del rendimiento y la incertidumbre inducida por reconstrucciones espaciales. Un análisis crítico exige distinguir la capacidad de discriminar puntos etiquetados de la probabilidad real de hallar un yacimiento económicamente viable.')
p(D,'El objetivo de este trabajo fue evaluar el efecto de la dependencia y el solapamiento de atributos sobre la fiabilidad de los modelos de prospección, comparar protocolos aleatorios y espaciales para tres algoritmos y cuantificar la sensibilidad del puntaje mineral a la incertidumbre de las covariables reconstruidas. Se planteó como hipótesis que el rendimiento estimado disminuiría cuando las particiones impidieran la proximidad espacial entre entrenamiento y evaluación.')
heading(D,'2. Materiales y métodos')
heading(D,'2.1. Datos y control de calidad',2)
p(D,'Se utilizaron 01_Train_VO.csv, 02_Train_PCA.csv y 04_Validation_Points.csv, publicados en TransferProspectivityLearning. Las variables PC1–PC7 se obtuvieron mediante un análisis de componentes principales aplicado por los autores a siete predictores originales (campo magnético y atributos geoquímicos). La tabla de entrenamiento contiene 313 registros (95 ocurrencias y 218 no ocurrencias); la validación publicada contiene 40 (20 y 20). Los registros de entrenamiento cuentan con coordenadas proyectadas; los de validación no tienen coordenadas en su CSV.')
p(D,'Se detectaron firmas PCA exactamente repetidas usando los siete valores publicados. Se eliminó una coordenada nula (0,0), se conservó una observación por firma de predictores y se obtuvo un conjunto único de 289 filas: 71 positivas y 218 negativas. Las observaciones no ocurrencia se interpretaron como etiquetas de referencia de la base original, no como certificaciones de esterilidad regional. Se registró explícitamente el solapamiento de firmas con los puntos externos.')
heading(D,'2.2. Modelos y protocolos de validación',2)
p(D,'Se implementó Random Forest (400 árboles; mínimos de dos casos por hoja; ponderación de clase), regresión logística con estandarización calculada únicamente sobre el conjunto de entrenamiento y un clasificador FDE-FT con topología 7-100-8-6-4-2-1. El encoder neuronal recibió pesos originales de un autoencoder no supervisado; la última capa se inicializó y todo el clasificador se reajustó mediante pérdida binaria ponderada durante 1.500 épocas dentro de cada partición. Se empleó PyTorch para el reajuste; este procedimiento constituye una adaptación trazable, no una réplica exacta del calendario de optimización TensorFlow publicado.')
p(D,'Se compararon cuatro estrategias: cinco particiones estratificadas aleatorias; cinco particiones agrupadas por retícula de 20 km; agrupación por retícula de 30 km; y agrupación de 30 km con exclusión de muestras de entrenamiento situadas a menos de 3 km de los puntos de prueba. Cada estrategia tuvo dos réplicas con desplazamientos de cuadrícula y semillas fijadas; las comparaciones entre algoritmos conservaron las mismas observaciones en cada réplica. Se estimaron AUC ROC, precisión media (AP), F1, sensibilidad, precisión positiva, exactitud equilibrada, Brier y error esperado de calibración en diez intervalos (ECE10).')
heading(D,'2.3. Inferencia y diagnóstico de incertidumbre',2)
p(D,'Los contrastes exploratorios de AUC se cuantificaron mediante 1.800 remuestreos apareados de grupos espaciales de 30 km sobre las predicciones fuera de muestra de la réplica principal. Se informaron percentiles del 2,5 % y 97,5 %. Al reutilizarse las predicciones OOF y al no ser independientes las réplicas de validación cruzada, estos intervalos no se interpretaron como pruebas confirmatorias de independencia total. Los puntajes de clasificación tampoco se asumieron probabilidades poblacionales calibradas.')
heading(D,'2.4. Sensibilidad de datos PCA reconstruidos',2)
p(D,'Se emplearon dos GeoTIFF V5 de siete bandas (predicción espacial y perfil multivariante), derivados de 763 firmas PCA georreferenciadas y 3.000 perfiles adicionales sin coordenadas. Se verificó el sistema EPSG:3579 y que las 763 celdas con firmas originales conservaran sus valores. Para cada celda se compararon dos puntajes del FDE-FT original y el cambio de estado al umbral 0,70. La V5 se utilizó exclusivamente como análisis de sensibilidad cartográfica, ya que no se obtuvo el ráster 02_PCA.tif auténtico.')
heading(D,'3. Resultados')
heading(D,'3.1. Solapamiento de datos y disponibilidad real de prueba externa',2)
p(D,'Las 313 filas de entrenamiento contenían 23 registros excedentes de firmas PCA repetidas, pertenecientes todos a la clase positiva. Entre los 40 registros del archivo externo, 24 compartían exactamente una firma PCA con el entrenamiento, pero las coordenadas no estuvieron disponibles. El subconjunto restante quedó reducido a 16 casos, 14 positivos y solo 2 negativos. Por ello, los resultados del conjunto externo original no pueden interpretarse como validación espacial independiente libre de solapamiento de atributos.')
p(D,'A modo diagnóstico y sin reutilizarlo como métrica de los modelos reentrenados, el archivo FDE-FT original ya ajustado obtuvo AUC = 0,928 en los 40 registros, AUC = 1,000 en las 24 firmas coincidentes y AUC = 0,679 en las 16 restantes. El último valor tiene gran incertidumbre por el reducido número de negativos.')
heading(D,'3.2. Variación del desempeño según el protocolo',2)
rows=[]
for m in ['RF','LR','FDE-FT']:
 rows.append((m,f3(metric('aleatoria',m,'AUC_medio')),f3(metric('espacial20',m,'AUC_medio')),f3(metric('espacial30',m,'AUC_medio')),f3(metric('espacial30_buffer3',m,'AUC_medio'))))
make_table(D,['Algoritmo','Aleatoria','20 km','30 km','30 km + 3 km'],rows,size=7.8,widths=[3.5,3,3,3,4.0])
p(D,'La reducción media de AUC al pasar de aleatoria a espacial de 30 km fue 0,080 para Random Forest, 0,049 para regresión logística y 0,091 para FDE-FT. Las diferencias se conservaron al aplicar bloques de 20 km, si bien la magnitud cambió. En la réplica primaria el contraste apareado RF aleatoria–espacial 30 km fue 0,0818, con IC bootstrap condicional del 95 % [0,0255; 0,1406].')
fig(D,'01_AUC_PROTOCOLOS_TRES_MODELOS.png','Figura 1. AUC media con dispersión entre réplicas para cada algoritmo y protocolo.',width=15.4)
heading(D,'3.3. Calibración y estabilidad entre modelos',2)
rows=[]
for m in ['RF','LR','FDE-FT']:
 rows.append((m,f3(metric('espacial30',m,'Brier_medio')),f3(metric('espacial30',m,'ECE10_medio')),f3(metric('espacial30',m,'F1_medio')),f3(metric('espacial30',m,'sensibilidad_media'))))
make_table(D,['Modelo','Brier','ECE10','F1','Recall'],rows,size=8.1,widths=[4,3,3,3,3])
p(D,'Random Forest mostró menor Brier (0,147) y ECE10 (0,073) en bloques de 30 km; FDE-FT registró mayor sensibilidad (0,704) y F1 (0,572). La diferencia de AUC FDE-FT menos RF, calculada en la réplica primaria, fue 0,0167 con IC bootstrap exploratorio de −0,0678 a 0,0752. El intervalo cruza cero, de manera que los resultados no sostienen superioridad universal de ninguno de los dos métodos.')
fig(D,'03_CALIBRACION_BRIER.png','Figura 2. Diagrama de calibración en cinco intervalos con mínimo de cinco casos por intervalo.',width=15.5)
p(D,'Como prueba adicional, se ajustó una sigmoide de calibración en grupos internos de entrenamiento separados espacialmente, sin emplear el bloque externo de prueba. Esta prueba no coincidió necesariamente con la precisión discriminativa: el Brier de FDE-FT disminuyó de 0,186 a 0,163 y el de regresión logística de 0,179 a 0,171, mientras que el de Random Forest aumentó de 0,150 a 0,160. En los tres algoritmos descendió el AUC después del ajuste, lo que desaconseja una calibración universal sin verificar sus efectos.')
fig(D,'08_CALIBRACION_PLATT_ESPACIAL_ANIDADA.png','Figura 3. Calibración sigmoide entrenada sobre grupos internos y evaluada sin contaminación del bloque externo.',width=15.5)
heading(D,'3.4. Sensibilidad de cartografía PCA reconstruida',2)
p(D,f'Las reconstrucciones V5 preservaron 763 celdas originales y modelaron 12.217 celdas (94,12 %). El cambio absoluto medio entre puntajes espaciales y multivariantes fue {rv["media_cambio_absoluto_puntaje"]:.3f} (percentil 95 = {rv["p95_cambio_absoluto_puntaje"]:.3f}). Al umbral de puntaje 0,70, {rv["celdas_cambian_categoria_umbral_0_70"]} celdas cambiaron de categoría (4,21 %), sin que ocurriera ningún cambio entre las celdas con valores originales. El IQR mediano bajo 40 simulaciones perturbadas fue {rv["IQR_modelo_original_perturbaciones_median"]:.3f}.')
fig(D,'06_MAPAS_SENSIBILIDAD_RECONSTRUCCION_V5.png','Figura 4. Impacto de las reconstrucciones alternativas sobre los puntajes FDE-FT; no son probabilidades de un yacimiento comprobado.',width=15.5)
heading(D,'4. Discusión')
p(D,'La reducción del AUC en los protocolos espaciales es coherente con la literatura que advierte contra el uso acrítico de validación aleatoria para variables con autocorrelación geográfica (Roberts et al., 2017; Valavi et al., 2019). La magnitud observada está condicionada por la muestra disponible, su distribución no balanceada y la retícula utilizada, por lo que no constituye una cifra transferible a otros distritos minerales. Incluso con bloques de 30 km pueden persistir muestras cercanas a ambos lados de una frontera; el protocolo con exclusión adicional de 3 km investigó esa sensibilidad.')
p(D,'El solapamiento de firmas PCA entre el entrenamiento y los 40 registros externos amerita una interpretación prudente. La coincidencia perfecta de atributos puede resultar del muestreo de un mismo píxel o de observaciones físicamente relacionadas, pero el archivo externo carece de coordenadas para discernir estas posibilidades. La diferencia entre métricas del conjunto externo completo y del subconjunto sin coincidencias constituye un diagnóstico de sensibilidad, no una demostración concluyente de fuga intencional o de error del artículo base.')
p(D,'Los modelos mostraron compensaciones: Random Forest logró mejor discriminación media y menor pérdida cuadrática de puntajes en bloques de 30 km, mientras FDE-FT favoreció la recuperación de ocurrencias. Esta diferencia de objetivos es relevante en exploración, donde el costo de omitir zonas promisorias puede ser distinto del de investigar falsos positivos. Ni el AUC ni el Brier por sí solos resumen la utilidad operacional sin datos de costos, prevalencia y validaciones de campo.')
p(D,'Los experimentos de reconstrucción V5 añaden una segunda fuente de incertidumbre: no basta con conocer la variación estadística de un clasificador si gran parte de sus covariables de entrada se estiman desde una superficie incompleta. La conservación exacta de 763 celdas y el registro de 547 cambios de categoría permiten separar evidencia genuina y modelización, aunque la verdadera correspondencia cartográfica seguirá siendo desconocida hasta recuperar el ráster original o regenerar las capas desde las fuentes geocientíficas primarias.')
heading(D,'5. Conclusiones')
for txt in [
 'El rendimiento de los tres clasificadores disminuyó al sustituir validación aleatoria por agrupación espacial de 30 km, lo que apoya la hipótesis de estimaciones optimistas bajo particiones aleatorias en este conjunto.',
 'Se verificó solapamiento exacto de atributos en 24 de los 40 registros de evaluación externa; la ausencia de coordenadas impide establecer su coincidencia geográfica real.',
 'La selección del algoritmo depende de la métrica: Random Forest presentó menor Brier y mayor AUC media espacial, mientras FDE-FT logró mayor sensibilidad; el contraste de AUC entre ambos no fue concluyente.',
 'La incertidumbre de reconstrucción PCA no es despreciable: un cambio de perfil alteró la categoría de puntaje en 547 celdas de la cuadrícula, sin modificar los valores originales disponibles.',
 'Los resultados justifican reportar particiones y buffers espaciales, auditorías de atributos, curvas de calibración e incertidumbre de entrada antes de interpretar mapas de prospectividad mineral.'
 ]:num(D,txt)
heading(D,'6. Limitaciones y reproducibilidad')
p(D,'Esta investigación utiliza registros de presencia/no presencia preseleccionados; no puede inferir directamente la prevalencia de depósitos en toda la región. La muestra externa no dispone de coordenadas y el TIFF PCA original no se ha recuperado. El reajuste FDE-FT utiliza un encoder preentrenado sobre covariables regionales completas, de naturaleza potencialmente transductiva. La versión espacial V5 es inferida y no sustituye información geológica de campo. Los intervalos bootstrap son descriptivos de la estabilidad condicional de los puntajes OOF y no de la totalidad de procesos de selección y entrenamiento. Estos límites se mantienen explícitos al interpretar las conclusiones.')
p(D,'Todos los datos fuente, scripts, configuraciones fijas, predicciones fuera de muestra, auditorías de particiones, tablas de resultados y gráficos se proporcionan en el paquete “YUKON_CIERRE_CIENTIFICO_V6”. Los pesos H5 son archivos originales publicados por Mantilla-Dulcey y colaboradores; revisar la licencia de redistribución del repositorio al enviar material suplementario a una revista.')
heading(D,'Referencias')
for ref in [
 'Mantilla-Dulcey, A., Goyes-Peñafiel, P., Báez-Rodríguez, R., & Khurama, S. (2024). Porphyry-type mineral prospectivity mapping with imbalanced data via prior geological transfer learning. Gondwana Research, 136, 236–250. https://doi.org/10.1016/j.gr.2024.09.004',
 'Roberts, D. R., Bahn, V., Ciuti, S., et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography, 40(8), 913–929. https://doi.org/10.1111/ecog.02881',
 'Valavi, R., Elith, J., Lahoz-Monfort, J. J., & Guillera-Arroita, G. (2019). blockCV: An R package for generating spatially or environmentally separated folds for k-fold cross-validation of species distribution models. Methods in Ecology and Evolution, 10(2), 225–232. https://doi.org/10.1111/2041-210X.13107',
 'Wang, Y., Khodadadzadeh, M., & Zurita-Milla, R. (2023). Spatial+: A new cross-validation method to evaluate geospatial machine learning models. International Journal of Applied Earth Observation and Geoinformation, 121, 103364. https://doi.org/10.1016/j.jag.2023.103364',
 'Mantilla-Dulcey et al. (2024). Repositorio original de datos y código. https://github.com/Anagabrielamantilla/TransferProspectivityLearning'
 ]:p(D,ref)
D.save(O/'Manuscrito_Cientifico_Yukon_V1.docx')
print('Documents saved', [p.name for p in O.glob('*.docx')])
