"""Independently checks V5 source TIFF layers and quantifies scores sensitivity."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import rasterio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'07_rasters_sensibilidad_V5';D=ROOT/'03_resultados';F=ROOT/'04_figuras'
def rd(name):
    with rasterio.open(R/name) as h:
        z=h.read().astype(float); meta=dict(crs=str(h.crs),count=h.count,rows=h.height,cols=h.width,nodata=h.nodata,transform=str(h.transform))
    return z,meta
orig,meta=rd('PCA7_V5_ESPACIAL_RECOMENDADO_7B.tif')
mod,m2=rd('PCA7_V5_COPULA_ORIGINAL_LIKE_7B.tif')
where,_=rd('V5_PROCEDENCIA_1_OBSERVADO_2_3KM_3_6KM_4_10KM_5_LEJOS.tif')
sc_a,_=rd('V5_FDE_PUNTAJE_ESPACIAL_SIN_RUIDO.tif')
sc_b,_=rd('V5_FDE_PUNTAJE_COPULA_SIN_RUIDO.tif')
iqr,_=rd('V5_ESPACIAL_FDE_IQR.tif')
frac,_=rd('V5_ESPACIAL_FRACCION_PUNTAJE_MAYOR_070.tif')
assert meta['count']==7 and m2['count']==7 and meta['crs']=='EPSG:3579' and orig.shape==(7,110,118)
mask=(where[0]==1)
assert int(mask.sum())==763
assert np.max(np.abs((orig-mod)[:,mask])) <1e-5
metrics=[]
for i in range(7):
 a=np.abs(orig[i]-mod[i]);metrics.append(dict(banda=f'PC{i+1}',MAE_diferencia_entre_versiones=float(np.mean(a)),P95_diferencia_entre_versiones=float(np.quantile(a,.95)),
            max_cambio_en_celdas_originales=float(np.max(a[mask]))))
pd.DataFrame(metrics).to_csv(D/'EFECTO_RECONSTRUCCION_POR_BANDA.csv',index=False)
a=sc_a[0];b=sc_b[0];cha=(a>=.7)!=(b>=.7)
allrows={
    'celdas_totales':a.size,'celdas_originales_sin_alteracion':int(mask.sum()),
    'proporcion_celdas_estimadas':float(1-mask.mean()),
    'media_cambio_absoluto_puntaje':float(np.mean(abs(a-b))),
    'p95_cambio_absoluto_puntaje':float(np.quantile(abs(a-b),.95)),
    'celdas_cambian_categoria_umbral_0_70':int(cha.sum()),
    'fraccion_cambian_categoria_umbral_0_70':float(cha.mean()),
    'celdas_cambian_categoria_dentro_originales':int(np.sum(cha&mask)),
    'IQR_modelo_original_perturbaciones_median':float(np.median(iqr)),
    'IQR_modelo_original_perturbaciones_p90':float(np.quantile(iqr,.9)),
    'porcentaje_incertidumbre_alta_IQR_gt_0_3':float(np.mean(iqr>.3)),
    'puntajes_sin_calibrar':True,
    'correlacion_espacial_verdadera_con_TIFF_original':'no verificable: TIFF auténtico no proporcionado',
    'celda_m':1200,'celda_m_origen':'inferido, artículo 1100',
    'procedencia_celdas':dict(zip([str(int(v)) for v in np.unique(where)], [int((where==v).sum()) for v in np.unique(where)]))}
(D/'AUDITORIA_EFECTO_RASTER_V5.json').write_text(json.dumps(allrows,indent=2,ensure_ascii=False),encoding='utf-8')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(1,3,figsize=(14,4.8))
imgs=[a,b,np.abs(a-b)];titles=['FDE-FT sobre PCA espacial V5','FDE-FT sobre PCA multivariante V5','Cambio absoluto del puntaje']
for ax,arr,title in zip(axs,imgs,titles):
 im=ax.imshow(arr,cmap='RdYlGn_r' if 'Cambio' not in title else 'magma',vmin=0,vmax=1 if 'Cambio' not in title else .5,interpolation='nearest')
 ax.set_title(title,fontsize=10);ax.set_xticks([]);ax.set_yticks([]);fig.colorbar(im,ax=ax,fraction=.046,pad=.04)
fig.suptitle('Sensibilidad del puntaje mineral a reconstrucción PCA (celdas 110 × 118)',fontweight='bold');fig.tight_layout()
fig.savefig(F/'06_MAPAS_SENSIBILIDAD_RECONSTRUCCION_V5.png',dpi=180,bbox_inches='tight');plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(10.7,4.5))
axs[0].hist(np.abs(a-b).ravel(),bins=45,color='#0f766e',alpha=.85);axs[0].set(xlabel='Cambio absoluto FDE-FT',ylabel='Celdas',title='Magnitud del cambio por reconstrucción')
axs[1].hist(iqr.ravel(),bins=45,color='#7c3aed',alpha=.85);axs[1].set(xlabel='IQR del puntaje (40 realizaciones)',ylabel='Celdas',title='Dispersión del puntaje por incertidumbre PCA')
for ax in axs:ax.grid(axis='y',alpha=.15)
fig.tight_layout();fig.savefig(F/'07_DISTRIBUCIONES_INCERTIDUMBRE_Y_CAMBIO.png',dpi=180,bbox_inches='tight');plt.close(fig)
print(json.dumps(allrows,indent=2,ensure_ascii=False))
