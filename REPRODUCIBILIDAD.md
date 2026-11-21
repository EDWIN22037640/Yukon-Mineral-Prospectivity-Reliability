# Alcance real de la reproducibilidad

## Estado comprobado en la revisión
1. **Inventario:** existen programas de construcción V5 y sus insumos intermedios V4; V6 conserva los scripts de aprendizaje, calibración, auditoría, predicciones, resultados y rasteres de sensibilidad.
2. **Archivos origen:** CSV y pesos `.h5` originales se excluyen de la publicación; deben obtenerse desde la fuente y copiarse localmente con `scripts/preparar_fuentes_originales.py`.
3. **Dependencias:** V5 tiene `requirements.txt` con rangos mínimos; V6 no tenía ese archivo en el ZIP original y se incorporó uno de referencia, inferido de las importaciones. No es un entorno original congelado.
4. **Particiones:** hay resúmenes por fold y predicciones por fila; no se identificó una matriz completa de pertenencia individual de observación a cada partición de entrenamiento/prueba que permita auditar sin recrearlas.
5. **Sensibilidad V5:** se incluye el generador, 40 realizaciones por reconstrucción y productos GeoTIFF; sin `02_PCA.tif` no puede reproducirse todo el procesamiento fuente ni afirmarse exactitud espacial.
6. **Pruebas:** `scripts/verificar_resultados_guardados.py` comprueba coherencia interna de OOF, AUC y rásteres. No equivale a reejecutar los experimentos.

## Ejecución propuesta

Descargar el ZIP del repositorio fuente, realizar el bootstrap local y activar un entorno separado para V5 y V6. No subir directorios `01_fuentes` a GitHub.

V5, desde la carpeta `V5`:

```bash
python -m pip install -r requirements.txt
python 02_codigo/construir_v5.py
python 02_codigo/verificar_v5.py
python 02_codigo/cartografia_qgis.py
python 02_codigo/crear_informe_v5.py
```

V6, desde la carpeta `V6` (otro entorno):

```bash
python -m pip install -r requirements.txt
python 02_codigo/analisis_final.py
python 02_codigo/calibracion_espacial_anidada.py
python 02_codigo/auditar_sensibilidad_v5.py
python 02_codigo/crear_documentos.py
python 02_codigo/verificar_entregables.py
```

El programa principal V6 incluye modos de ejecución/agrupación controlados por variables de entorno para el script `REPRODUCIR_WINDOWS.bat`. El costo de reentrenamiento puede ser considerable. Se deben guardar logs de ejecución y comparar SHA-256/estadísticos finales para afirmar una reproducción idéntica.

### Diagnóstico geoestadístico adicional

El script `diagnostico_autocorrelacion/diagnostico_autocorrelacion_Yukon.py` utiliza un ZIP V6 completo original con `01_fuentes/` instalado. No ejecutar sobre el ZIP del repositorio actual, porque se eliminaron los archivos originales por permisos. Para crear un ZIP local completo después de recuperar las fuentes, comprimir la carpeta `V6/` con prefijo `YUKON_CIERRE_CIENTIFICO_V6/` y ejecutar:

```bash
python diagnostico_autocorrelacion/diagnostico_autocorrelacion_Yukon.py --source ruta/al/V6_completo_local.zip --output resultados_variogramas
```

Los alcances efectivos estimados son exploratorios y no prueban que 20 o 30 km eliminen toda autocorrelación.

## Limitaciones técnicas todavía abiertas

- Entorno Python exacto de las corridas originales, sistema operativo y versiones de librerías por fijar.
- Reejecución completa desde cero no comprobada de manera independiente.
- Matriz de pertenencia individuo→fold de todas las particiones no aportada como producto explícito.
- Falta `02_PCA.tif` del estudio fuente.
- Permisos de redistribución de insumos y derivados sujetos a confirmación.

**Nunca afirmar que el código original fuente, las nuevas reconstrucciones o la validación externa geográfica han sido reproducidos en su totalidad sin estas comprobaciones.**
