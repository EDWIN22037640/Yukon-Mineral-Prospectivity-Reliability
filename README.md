# Evaluación de la confiabilidad de modelos de prospectividad mineral en Yukón, Canadá

Código y productos derivados de un **reanálisis científico** sobre validación espacial, auditoría de posibles fugas de información y sensibilidad cartográfica PCA. El proyecto utiliza datos y pesos publicados por **Mantilla-Dulcey et al. (2024)**; los procedimientos V5 y V6 se desarrollaron en la investigación que acompaña el manuscrito para JAMM.

**Estado del repositorio:** Material científico disponible públicamente. La documentación y los procedimientos se encuentran en revisión para establecer una versión estable. La reproducción integral del estudio aún no ha sido verificada de manera independiente.

## Contenido

| Carpeta | Función | Reproducción documentada |
|---|---|---|
| `V5/02_codigo/` | Construcción de reconstrucciones V5, simulaciones y auditoría cartográfica | Requiere datos fuente instalados localmente y rasters intermedios V4 incluidos. |
| `V5/03_GeoTIFF_QGIS/` | Superficies y productos geoespaciales intermedios/derivados | Comparación cartográfica; no es el GeoTIFF original del estudio fuente. |
| `V5/04_validacion/` | Diagnósticos de fidelidad estadística y sensibilidad | Referencia de 3.000 perfiles PCA y subconjunto de 581 sin coincidencias exactas. |
| `V6/02_codigo/` | Validación de modelos, calibración, auditoría y gráficos | Requiere CSV y modelos originales obtenidos localmente. |
| `V6/03_resultados/` | Predicciones fuera de muestra y resúmenes de particiones | 6.936 predicciones sobre 289 firmas georreferenciadas. |
| `V6/06_reproducibilidad/` | Registros de ejecución y resúmenes intermedios | No contiene una matriz completa explícita de asignación individuo→partición para todos los casos. |
| `V6/07_rasters_sensibilidad_V5/` | Insumos cartográficos reutilizados por V6 | Dos reconstrucciones, puntajes e incertidumbre cartográfica. |
| `diagnostico_autocorrelacion/` | Semivariogramas de PC1–PC7 y comprobaciones de sensibilidad | Análisis adicional asociado a la respuesta al revisor. |
| `figuras_manuscrito/` | Figuras finales corregidas para el manuscrito | Representaciones derivadas de resultados y predicciones del proyecto. |

## Procedencia de los datos originales

Los CSV de entrenamiento, evaluación, preentrenamiento, perfiles PCA auxiliares y los modelos `.h5` provienen de:

- [TransferProspectivityLearning](https://github.com/Anagabrielamantilla/TransferProspectivityLearning), de Mantilla-Dulcey et al.
- Referencia: Mantilla-Dulcey, A., Goyes-Peñafiel, P., Báez-Rodríguez, R., & Khurama, S. (2024). *Porphyry-type mineral prospectivity mapping with imbalanced data via prior geological transfer learning*. *Gondwana Research*, 136, 236–250. https://doi.org/10.1016/j.gr.2024.09.004

**Los CSV y pesos originales NO se duplican en este repositorio**: la copia fuente revisada no contiene un archivo de licencia explícito que habilite inequívocamente su redistribución. Para reproducir localmente, descargue el ZIP del repositorio original y ejecute:

```bash
python scripts/preparar_fuentes_originales.py /ruta/al/TransferProspectivityLearning-main.zip
```

Los archivos recuperados se colocan en `V5/01_fuentes/` y `V6/01_fuentes/`; `.gitignore` evita publicarlos accidentalmente.

## Entorno y ejecución

Se recomienda crear un entorno virtual independiente para cada etapa. Las dependencias de V5 corresponden al `requirements.txt` suministrado con V5; las de V6 se reconstruyeron mediante inspección de importaciones y **no son un archivo de versiones fijadas originalmente**.

```bash
# Desde V5
python -m pip install -r requirements.txt
python 02_codigo/construir_v5.py
python 02_codigo/verificar_v5.py

# Desde V6 (otro entorno)
python -m pip install -r requirements.txt
python 02_codigo/analisis_final.py
python 02_codigo/calibracion_espacial_anidada.py
python 02_codigo/auditar_sensibilidad_v5.py
python 02_codigo/verificar_entregables.py
```

`V6/REPRODUCIR_WINDOWS.bat` fue preservado y ahora encuentra un `requirements.txt` de referencia. **El reentrenamiento íntegro de V5/V6 no se ha vuelto a ejecutar aquí**; compare siempre las nuevas salidas con los resultados entregados y documente el entorno exacto.

Puede comprobar la coherencia de los resultados guardados **sin reentrenar**:

```bash
python scripts/verificar_resultados_guardados.py
```

Para los semivariogramas, el script `diagnostico_autocorrelacion_Yukon.py` de la carpeta de autocorrelación acepta un ZIP V6 con los datos fuente reinstalados; véase `REPRODUCIBILIDAD.md`.

## Límites de interpretación

- La reconstrucción PCA no equivale a recuperar el ráster primario `02_PCA.tif` ni valida ubicaciones geológicas nuevas.
- Los 3.000 perfiles `013_Random.csv` carecen de coordenadas; sus pruebas evalúan similitud estadística, no exactitud geográfica.
- Las 763 celdas ancladas se conservan y las 12.217 restantes son reconstruidas.
- El análisis sobre 289 observaciones usa protocolos aleatorio, bloques de 20 km, bloques de 30 km y bloques de 30 km con exclusión de 3 km.
- Los 1.800 remuestreos por bloques son condicionales a las predicciones OOF guardadas; no reentrenan los modelos.
- Antes de uso para prospección real se requiere verificación geológica independiente.

## Permisos y citación

Los archivos originales siguen siendo propiedad intelectual de sus respectivos titulares. **No se declara una licencia general** para este conjunto mixto mientras no se verifiquen permisos sobre código y datos derivados. Ver `PROCEDENCIA_Y_LICENCIAS.md` y `REPRODUCIBILIDAD.md`.

El enlace de este repositorio puede citarse como recurso de software/materiales; una publicación específica en **Releases** fijará la versión utilizada en la revisión del artículo. GitHub no genera por sí mismo un DOI.
