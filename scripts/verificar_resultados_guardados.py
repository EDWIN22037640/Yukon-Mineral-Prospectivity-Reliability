#!/usr/bin/env python3
"""Comprobación de coherencia de archivos publicados SIN reentrenamiento."""
from pathlib import Path
import numpy as np, pandas as pd, rasterio, json
from sklearn.metrics import roc_auc_score
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'V6'/'03_resultados'
p=pd.read_csv(R/'PREDICCIONES_FUERA_DE_MUESTRA_TODAS.csv')
assert len(p)==6936, f'Filas OOF inesperadas: {len(p)}'
assert p['id_unico'].nunique()==289
assert p.groupby(['protocolo','modelo','replica']).size().eq(289).all()
met=pd.read_csv(R/'METRICAS_OOF_POR_REPLICA.csv')
for row in met.itertuples():
  z=p[(p.protocolo==row.protocolo)&(p.modelo==row.modelo)&(p.replica==row.replica)]
  auc=roc_auc_score(z.verdad,z.puntaje)
  assert abs(auc-row.AUC)<1e-8, (row.protocolo,row.modelo,row.replica,auc,row.AUC)
con=pd.read_csv(R/'RESULTADOS_COMPARACION_CONSOLIDADA.csv')
for row in con.itertuples():
  z=met[(met.protocolo==row.protocolo)&(met.modelo==row.modelo)]
  assert len(z)==2
  assert abs(z.AUC.mean()-row.AUC_medio)<1e-8
G=ROOT/'V6'/'07_rasters_sensibilidad_V5'
with rasterio.open(G/'V5_FDE_PUNTAJE_ESPACIAL_SIN_RUIDO.tif') as ds: a=ds.read(1)
with rasterio.open(G/'V5_FDE_PUNTAJE_COPULA_SIN_RUIDO.tif') as ds: b=ds.read(1)
with rasterio.open(G/'V5_ESPACIAL_FDE_IQR.tif') as ds: iqr=ds.read(1)
with rasterio.open(G/'V5_PROCEDENCIA_1_OBSERVADO_2_3KM_3_6KM_4_10KM_5_LEJOS.tif') as ds: proc=ds.read(1)
assert a.size==12980 and b.shape==a.shape and iqr.shape==a.shape
assert np.sum(proc==1)==763
assert np.sum((a>=.7)!=(b>=.7))==547
assert np.isclose(np.abs(a-b).mean(),.0449959498501152,atol=1e-6)
assert np.isclose(np.median(iqr),.16759847849607468,atol=1e-6)
print('VALIDACIÓN DOCUMENTAL CORRECTA: 6936 OOF, 289 firmas, AUC por réplica, 12980 celdas, 763 anclas, 547 cambios, 0,045 de diferencia media, 0,168 de IQR mediano.')
print('ALCANCE: esto NO prueba reproducción íntegra ni reentrenamiento exitoso.')
