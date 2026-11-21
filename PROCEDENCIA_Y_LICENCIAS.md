# Procedencia, atribución y licencias

## Aportación del estudio
- Reconstrucción/ajuste cartográfico V5, auditorías, simulaciones y resultados derivados que el autor identifica como parte de su proyecto.
- Comparación de modelos, validación espacial, calibración y auditoría V6 que el autor identifica como parte de su proyecto.
- Diagnósticos adicionales sobre semivariogramas y comparaciones estadísticas desarrollados en la revisión del manuscrito.

## Materiales de terceros retirados del paquete GitHub
Se encontraron coincidencias exactas SHA-256 entre archivos de `01_fuentes` de V5/V6 y el repositorio fuente `TransferProspectivityLearning-main.zip`:
- 5 CSV y 1 modelo `.h5` en V5.
- 3 CSV y 2 modelos `.h5` en V6.
- El repositorio original revisado no contiene un archivo `LICENSE`/`COPYING`; que sea público o de acceso abierto no implica automáticamente permiso general de reutilización y redistribución de código/modelos.

Los archivos originales no están incluidos en este paquete; deben obtenerse por separado de https://github.com/Anagabrielamantilla/TransferProspectivityLearning. El script `scripts/preparar_fuentes_originales.py` instala solo copias locales descargadas por quien reproduce.

## Productos derivados
Los rasteres, CSV de resultados y figuras son productos derivados del análisis. Antes de publicarlos de forma abierta, el autor debe verificar los términos que rigen sus insumos originales y la posibilidad de redistribuir derivados. **Este paquete es un candidato de publicación**, no una certificación jurídica de licencias.

No se ha añadido licencia permisiva al conjunto hasta decidir los derechos sobre código propio y materiales derivados. Una licencia del código propio puede añadirse por separado sin atribuir derechos sobre recursos de terceros.

Se retiraron asimismo los archivos `perfiles_test_581_sin_coincidencias.csv` y `perfiles_test_26_excluidos_por_coincidencia.csv` de esta copia pública, por contener subconjuntos literales de perfiles de la fuente. Los resúmenes estadísticos se conservan. Para reproducir de nuevo esos subconjuntos, ejecutar `construir_v5.py` con las entradas originales obtenidas localmente.
