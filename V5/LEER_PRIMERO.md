> **Nota sobre esta copia para publicación:** se retiraron los CSV y pesos originales de terceros y el subdirectorio de código de referencia V4 mientras se verifica su licencia/procedencia. Para ejecución V5, instale las entradas originales localmente mediante `../scripts/preparar_fuentes_originales.py`; los rásteres V4 derivados y el código propio V5 permanecen incluidos. La reproducción integral desde las capas primarias continúa pendiente.

# YUKÓN · PCA V5 | Versión superior con control estadístico, error espacial y sensibilidad FDE-FT

**Fecha:** 27/10/2026  
**Área:** Yukón, Canadá · EPSG:3579 · 118 columnas × 110 filas × 7 PC  
**Geometría:** 1.200 m/píxel **inferidos** de los CSV, no del ráster fuente. El artículo menciona 1.100 m.  
**Estado:** los GeoTIFF y las dos capas del GeoPackage se verificaron programáticamente.

## Qué se mejoró realmente

1. La V4 ajustaba distribuciones PC individuales; **V5 añade corrección de dependencia conjunta** por rangos gaussianos y transporte de correlación sobre las celdas inferidas. Las 763 celdas con PC auténticos del repositorio quedan intactas.
2. Del conjunto reservado de 607 perfiles PCA, 26 coincidían con firmas georreferenciadas originales. **El contraste principal V5 usa los otros 581**, manteniendo la comparación libre de esas coincidencias exactas.
3. Se incorporó **estimación adaptativa del radio de error P90** por cada banda, con entrenamiento/calibración/evaluación por cinco bloques de datos. Su cobertura media empírica fue 90,19 %, no una garantía estadística para áreas nuevas.
4. Se ejecutaron **40 realizaciones espaciales correlacionadas y condicionadas en las anclas** para examinar sensibilidad de la red original FDE-FT; se incluyen percentiles e IQR del puntaje y fracción de realizaciones que exceden 0,70.
5. Mapas con leyenda comparable a las figuras del artículo (verde–amarillo–rojo), puntos reales, norte, escala, CSV de auditoría, PDF/Word, código y GeoPackage.

### Contrastación con 581 perfiles originales reservados sin coincidencias georreferenciadas

| Distancia / diagnóstico | V4 perfil | V5 cópula | Interpretación |
|---|---:|---:|---|
| KS medio de las siete PC | 0,037266 | 0,037265 | Sin cambio práctico |
| Wasserstein-1 promedio normalizado | 0,066190 | 0,063663 | Disminuye ≈3,8 % |
| Diferencia entre matrices de correlación (Frobenius) | 0,967203 | 0,731069 | Disminuye ≈24,4 % |
| Wasserstein por proyecciones 7D | 0,091317 | 0,085485 | Disminuye ≈6,4 % |

**Clave:** estas métricas son de **fidelidad estadística**, no de coincidencia geográfica con un ráster auténtico que aún no se ha localizado. La prueba de 581 perfiles no confirma la posición de los píxeles.

## Archivos para abrir en QGIS

| Archivo | Uso correcto |
|---|---|
| `03_GeoTIFF_QGIS/PCA7_V5_ESPACIAL_RECOMENDADO_7B.tif` | **Mapa principal** para análisis de localización. Conserva íntegro el estimador V4 espacial; no se afirma mejora geográfica artificial. |
| `03_GeoTIFF_QGIS/PCA7_V5_COPULA_ORIGINAL_LIKE_7B.tif` | Reconstrucción con correlaciones PC más parecidas a la referencia de 3.000 perfiles sin coordenadas; útil para análisis de sensibilidad. |
| `03_GeoTIFF_QGIS/PCA7_V5_SOLO_SOPORTE_CERCANO_7B.tif` | Versión espacial sobre **1.372 celdas** del filtro conservador; fuera del filtro es NoData, no “ausencia de mineral”. |
| `03_GeoTIFF_QGIS/V5_RADIO_ERROR_90_EMPIRICO_7B.tif` | Un valor de radio de error absoluto por banda y celda (diagnóstico aproximado). |
| `03_GeoTIFF_QGIS/V5_PCA_REALIZACION_PLAUSIBLE_7B.tif` | Una realización simulada condicionada, **no** un nuevo mapa de observaciones verdaderas. |
| `03_GeoTIFF_QGIS/V5_INDICE_RIESGO_INTERPOLACION.tif` | Error normalizado medio de las siete bandas. |
| `03_GeoTIFF_QGIS/V5_ESPACIAL_FDE_MEDIANA.tif` | Mediana del puntaje del clasificador original FDE-FT bajo 40 perturbaciones. |
| `03_GeoTIFF_QGIS/V5_ESPACIAL_FDE_IQR.tif` | Dispersión de puntaje asociada a la incertidumbre de entrada. |
| `03_GeoTIFF_QGIS/V5_ESPACIAL_FRACCION_PUNTAJE_MAYOR_070.tif` | Fracción de simulaciones con puntaje FDE ≥0,70. **No es probabilidad de yacimiento.** |
| `03_GeoTIFF_QGIS/V5_PUNTOS_GEOLOGICOS_REALES.gpkg` | Capas `PCA_763_CELDAS` y `ENTRENAMIENTO_312` con CRS auténtico de los registros. |

Los rásteres contienen siete bandas denominadas **PC1, PC2, PC3, PC4, PC5, PC6 y PC7** en el orden natural de QGIS. La reconstrucción aplica valor NoData −9999 a las celdas que no pasan el filtro de soporte.

### Informe y figuras

- `06_informe/Informe_Tecnico_Yukon_PCA_V5_Superior.docx` · reporte profesional editable de seis páginas.
- `06_informe/Informe_Tecnico_Yukon_PCA_V5_Superior.pdf` · mismo reporte en PDF.
- `05_figuras/06_CARTOGRAFIA_COMO_ARTICULO_PROSPECTIVIDAD.png` y `.pdf` · lámina de prospectividad con estilo cercano al artículo, **sin líneas de fallas inventadas**.
- `05_figuras/01_ATLAS_COMPARATIVO_7_BANDAS_V4_V5.png` · lámina de siete componentes.
- `05_figuras/02_EVIDENCIA_DISTANCIA_Y_ERROR_90.png` · soporte original y distancias.
- `05_figuras/03_TEST_RESERVADO_MULTIVARIANTE.png` · prueba estricta 581 perfiles.
- `05_figuras/04_VALIDACION_INTERVALOS_ESPACIALES.png` · cobertura y anchura empírica.
- `05_figuras/05_INCERTIDUMBRE_DEL_PUNTAJE_FDE.png` · sensibilidad de FDE-FT.

## Reproducir en Windows

Instalar [Python](https://www.python.org/) y QGIS; desde PowerShell dentro de esta carpeta:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python 02_codigo\construir_v5.py
python 02_codigo\cartografia_qgis.py
python 02_codigo\verificar_v5.py
python 02_codigo\crear_informe_v5.py
```

Los GeoTIFF V4 y sus predicciones espacialmente fuera de muestra (`oof_preds.csv`) son **insumos intermedios incluidos en esta carpeta** para reproducir la etapa V5 con independencia de descargas externas. El código V4 se adjunta como referencia metodológica de la etapa previa y para reproducir desde datos crudos debe ejecutarse dentro de la estructura V4 original.

### Control de calidad y trazabilidad

- GeoTIFF siete bandas, dimensiones 110 × 118, CRS EPSG:3579: **validado**.
- 763 celdas auténticas de PC georreferenciadas sin modificación numérica, salvo redondeo a float32: **validado**.
- Las 12.217 celdas restantes (94,12 % del área) son modeladas: **no medirlas ni tratarlas como observaciones**.
- Conjunto externo PCA: 3.000 registros. Particiones agrupadas por firma exacta de 1.799/594/607. **26 perfiles de prueba con firma presente en datos georreferenciados se excluyen del contraste estricto (581)**.
- Cobertura empírica V5 adaptativa media: 90,19 %. PC6 = 87,68 % (**por debajo de 90 %**): ver `04_validacion/RESUMEN_COBERTURA_INTERVALOS_90.csv`.
- Restricción de uso: detección de patrones metodológicos para tesis/artículos; **no planificar perforación ni presupuestar reservas sobre estas superficies**.
- `04_validacion/CONTROL_CALIDAD_FINAL_V5.json`, `04_validacion/METADATOS_V5_AUDITABLE.json` y `MANIFIESTO_SHA256.csv` facilitan auditoría.

## Limitaciones que NO se eliminaron

**No se ha recuperado el archivo `02_PCA.tif` original.** La V5 no es una réplica píxel a píxel ni puede certificar que zonas nuevas sean depósitos. Su similitud multivariante se refiere a distribuciones de puntos sin ubicación. La georreferenciación de 1.200 m es inferida y difiere de la resolución de 1.100 m descrita por la publicación. Los intervalos no tienen garantías formales bajo dependencia espacial y las 40 simulaciones representan un escenario de error, no todos los procesos geológicos posibles. Los valores superiores a 0,7 son puntajes del modelo, no probabilidades calibradas de ocurrencia.

El servicio oficial de [fallas geológicas de Yukón](https://open.yukon.ca/data/faults) está identificado, pero no se pudo incorporar una descarga GIS verificable en este paquete. Por ello no se dibujaron fallas ficticias para imitar figuras.

## Citas y términos de uso

- Mantilla-Dulcey, A., Goyes-Peñafiel, P., Báez-Rodríguez, R., & Khurama, S. (2024). *Porphyry-type mineral prospectivity mapping with imbalanced data via prior geological transfer learning*. **Gondwana Research, 136**, 236–250. DOI: https://doi.org/10.1016/j.gr.2024.09.004
- Código, datos y pesos originales de los autores: https://github.com/Anagabrielamantilla/TransferProspectivityLearning
- Repositorio geológico oficial: https://data.geology.gov.yk.ca/

Respetar las licencias y atribución de los datos/códigos originales y revisar restricciones antes de redistribuir esta versión derivada públicamente.
