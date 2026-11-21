from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd,rasterio,geopandas as gpd
R=Path(__file__).resolve().parents[1];G=R/'03_GeoTIFF_QGIS';V=R/'04_validacion'
pcs=[f'PC{i}' for i in range(1,8)]
files=['PCA7_V5_ESPACIAL_RECOMENDADO_7B.tif','PCA7_V5_COPULA_ORIGINAL_LIKE_7B.tif','PCA7_V5_SOLO_SOPORTE_CERCANO_7B.tif','V5_RADIO_ERROR_90_EMPIRICO_7B.tif','V5_PCA_REALIZACION_PLAUSIBLE_7B.tif']
with rasterio.open(G/'V5_PROCEDENCIA_1_OBSERVADO_2_3KM_3_6KM_4_10KM_5_LEJOS.tif') as ds: mask=(ds.read(1)==1).ravel();assert mask.sum()==763
with rasterio.open(G/files[0]) as ds:baseline=ds.read().reshape(7,-1).T;tr=ds.transform;crs=ds.crs.to_epsg();assert (ds.count,ds.width,ds.height)==(7,118,110);assert crs==3579 and tr.a==1200
P=pd.read_csv(V/'oof_preds.csv');Y=P[[f'{j}_OBS' for j in pcs]].to_numpy(float);assert (P.id_celda.values==np.flatnonzero(mask)).all()
res=[]
for fn in files:
 with rasterio.open(G/fn) as ds:
  arr=ds.read().reshape(7,-1).T
  finite=np.isfinite(arr)&(arr!=ds.nodata)
  assert (ds.count,ds.height,ds.width,ds.crs.to_epsg())==(7,110,118,3579)
  assert np.all(finite.sum(axis=0)>0)
  source_diff=float(np.max(np.abs(arr[mask]-Y))) if 'RADIO_ERROR' not in fn else None
  if 'RADIO_ERROR' in fn:assert np.all(arr[mask]==0)
  elif 'SOLO_SOPORTE' in fn:assert source_diff<5e-5
  else:assert source_diff<5e-5
  res.append(dict(archivo=fn,bandas=ds.count,pixeles_validos_por_banda=[int(z) for z in finite.sum(axis=0)],error_max_en_observados=source_diff))
with rasterio.open(G/'V5_MASCARA_SOPORTE_CERCANO_5DE7.tif') as ds:mask5=ds.read(1).astype(bool);assert mask5.sum()==1372
layers=gpd.list_layers(G/'V5_PUNTOS_GEOLOGICOS_REALES.gpkg')
assert set(layers.name)=={'PCA_763_CELDAS','ENTRENAMIENTO_312'}
assert len(gpd.read_file(G/'V5_PUNTOS_GEOLOGICOS_REALES.gpkg',layer='PCA_763_CELDAS'))==763
assert len(gpd.read_file(G/'V5_PUNTOS_GEOLOGICOS_REALES.gpkg',layer='ENTRENAMIENTO_312'))==312
s=pd.read_csv(V/'comparacion_test_581_SIN_COINCIDENCIAS.csv');assert len(s)==12
report=json.loads((V/'METADATOS_V5_AUDITABLE.json').read_text(encoding='utf8'));assert report['heldout_strict_n']==581 and report['overlap_excluded']==26
stat=dict(estado='VALIDADO',tif_central_7_bandas=True,anclas_exactas=763,interpoladas=12217,mascara_soporte_celdas=1372,capas_gpkg=layers.to_dict(orient='records'),tifs=res,test_estadistico_estricto=581,perfiles_excluidos_por_coincidencia=26,origen_raster_original='NO RECUPERADO')
(V/'CONTROL_CALIDAD_FINAL_V5.json').write_text(json.dumps(stat,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({k:v for k,v in stat.items() if k not in ('tifs','capas_gpkg')},indent=2))
