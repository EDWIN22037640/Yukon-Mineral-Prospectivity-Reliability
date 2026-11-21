#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YUKON PCA V5: auditoría multivariante, intervalos espaciales y simulación condicionada.
No recupera el .tif original. No atribuir origen geológico a realizaciones simuladas.
Entradas: GeoTIFF V4 incluido; CSV originales; OOF espacial V4; pesos FDE autores.
Ejecutar desde cualquier directorio: python 02_codigo/construir_v5.py
"""
from __future__ import annotations
import hashlib, json, time, warnings
from pathlib import Path
import numpy as np, pandas as pd, rasterio, h5py
from scipy.stats import rankdata, norm, ks_2samp, wasserstein_distance
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
from scipy.spatial.distance import pdist, squareform
from sklearn.model_selection import GroupShuffleSplit
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
warnings.simplefilter('ignore',RuntimeWarning)
R=Path(__file__).resolve().parents[1]
INPUT=R/'01_fuentes'; GIS=R/'03_GeoTIFF_QGIS'; VAL=R/'04_validacion'; FIG=R/'05_figuras'
BANDS=[f'PC{i}' for i in range(1,8)]
for q in (GIS, VAL, FIG):q.mkdir(parents=True,exist_ok=True)
SEED=20261027; rng=np.random.default_rng(SEED)


def read_tif(p):
 with rasterio.open(p) as z:return z.read(),z.profile.copy(),z.transform,z.crs

def geotiff(name, data, profile, desc, comment, nodata=-9999.):
 arr=np.asarray(data)
 if arr.ndim==2:arr=arr[None,:,:]
 P=profile.copy();P.update(count=arr.shape[0],height=arr.shape[1],width=arr.shape[2],dtype='float32',nodata=nodata,compress='deflate',predictor=3,tiled=True,blockxsize=64,blockysize=64)
 path=GIS/name
 with rasterio.open(path,'w',**P) as ds:
  ds.write(arr.astype(np.float32))
  for i,k in enumerate(desc,1):ds.set_band_description(i,str(k))
  ds.update_tags(PRODUCTO_V5=comment, FUENTE='Mantilla-Dulcey et al. 2024; datos del repositorio original; derivados V5', OBSERVACIONES='763 valores PCA medidos/extraidos son exactos; demas celdas estimadas', RASTER_AUTENTICO='NO, no es 02_PCA.tif original', FECHA='2026-10-27')
 return str(path)


def reference_partition(A):
 signatures=[hashlib.sha256(r.tobytes()).hexdigest() for r in A]
 left,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=2026).split(A,groups=signatures))
 it,iv=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=1701).split(A[left],groups=np.asarray(signatures)[left]))
 return A[left[it]],A[left[iv]],A[test]


def corrs(A):
 return np.corrcoef(A,rowvar=False)


def sqrtm_robust(A,power):
 e,q=np.linalg.eigh((A+A.T)/2);return (q*np.maximum(e,1e-6)**power)@q.T


def copula_transport(A, obs, reference):
 """Low-displacement Gaussian-rank copula correction while freezing observed data."""
 v=A[~obs,:];n=len(v)
 Z=np.column_stack([norm.ppf((rankdata(v[:,j])-.5)/n) for j in range(7)])
 re=np.asarray(reference);m=len(re)
 Zr=np.column_stack([norm.ppf((rankdata(re[:,j])-.5)/m) for j in range(7)])
 target=Z@sqrtm_robust(corrs(Z),-.5)@sqrtm_robust(corrs(Zr),.5)
 correct=np.empty_like(v)
 for j in range(7):
  uq=(rankdata(target[:,j])-.5)/n
  correct[:,j]=np.interp(uq,(np.arange(m)+.5)/m,np.sort(re[:,j]))
 return correct


def copula_mix(base, observed, transported, lam):
 out=base.copy();out[~observed]=(1-lam)*base[~observed]+lam*transported
 assert np.array_equal(out[observed],base[observed]);return out


def sliced_w1(A,B,dirs,seed=314):
 rr=np.random.default_rng(seed);N=min(1800,len(A))
 m=min(1300,len(B));q=rr.choice(len(A),size=N,replace=False);s=rr.choice(len(B),size=m,replace=False)
 mu=np.mean(B,axis=0);sd=np.std(B,axis=0).clip(.05)
 za=(A[q]-mu)/sd;zb=(B[s]-mu)/sd
 return float(np.mean([wasserstein_distance(za@z,zb@z) for z in dirs]))


def eval_dist(A,ref,dirs):
 ks=float(np.mean([ks_2samp(A[:,j],ref[:,j]).statistic for j in range(7)]))
 w=float(np.mean([wasserstein_distance(A[:,j],ref[:,j])/max(.05,ref[:,j].std()) for j in range(7)]))
 cor=float(np.linalg.norm(corrs(A)-corrs(ref),'fro'))
 return dict(KS_medio=ks,W1_normalizado=w,error_matriz_correlacion_Frob=cor,W1_proyecciones=sliced_w1(A,ref,dirs))


def choose_transport(baseline,observed,reftrain,refval):
 raw=copula_transport(baseline,observed,reftrain)
 dirs=rng.normal(size=(40,7));dirs/=np.linalg.norm(dirs,axis=1)[:,None]
 scores=[]
 sd=reftrain.std(axis=0).clip(.05)
 for alpha in [0,.10,.20,.30,.40,.50]:
  cand=copula_mix(baseline,observed,raw,alpha)
  m=eval_dist(cand,refval,dirs)
  rms=np.sqrt(np.mean(((cand[~observed]-baseline[~observed])/sd)**2))
  # Objective fixed before viewing holdout test; distinguish stat likeness from spatial fidelity.
  loss=.6*m['W1_proyecciones']+.18*m['error_matriz_correlacion_Frob']+.15*m['KS_medio']+.07*m['W1_normalizado']+.1*rms
  scores.append(dict(peso_correccion=alpha,desplazamiento_RMS_normalizado=float(rms),criterio=float(loss),**m))
 dt=pd.DataFrame(scores);dt.to_csv(VAL/'seleccion_copula_solo_validacion.csv',index=False)
 best=dt.loc[dt.criterio.idxmin()]
 return copula_mix(baseline,observed,raw,float(best.peso_correccion)),dict(best),dirs


def features_from_controls(testxy, trainxy, ytrain):
 """Neighborhood features; labels only from training control points."""
 n=len(testxy);k=min(12,len(trainxy)); dist,idx=cKDTree(trainxy).query(testxy,k=k)
 if k==1:dist=dist[:,None];idx=idx[:,None]
 local=ytrain[idx]
 med=np.median(local,axis=1)
 mad=np.median(np.abs(local-med[:,None,:]),axis=1)*1.4826
 sd=np.std(local,axis=1)
 density=(dist<=3600).sum(axis=1)
 bs=np.column_stack([np.log1p(dist[:,0]/1000),np.log1p(dist[:,min(k-1,5)]/1000),np.log1p(dist[:,-1]/1000),density])
 return [np.column_stack([bs,sd[:,j],mad[:,j],np.abs(med[:,j]),np.abs(local[:,0,j]-med[:,j])]) for j in range(7)],dist[:,0],sd


def uncertainty_model(oof, obsxy, anchors_xy, source_y, queryxy, observed_mask, profile, spatial_base):
 folds=oof['outer_fold'].to_numpy(int)
 truth=np.column_stack([oof[f'{b}_OBS'] for b in BANDS])
 pred=np.column_stack([oof[f'{b}_V4'] for b in BANDS])
 errors=np.abs(truth-pred)
 n=len(oof);F=[np.zeros((n,8)) for _ in range(7)]
 for fold in np.unique(folds):
  test=folds==fold;train=~test
  feats,_,_=features_from_controls(obsxy[test],obsxy[train],truth[train])
  for j in range(7):F[j][test]=feats[j]
 mapF, mapdist, _=features_from_controls(queryxy,anchors_xy,source_y)
 params=dict(n_estimators=115,max_depth=2,min_samples_leaf=24,learning_rate=.05,loss='quantile',alpha=.90,subsample=.9)
 est=np.zeros((7,len(queryxy)))
 outtest=np.zeros_like(errors);globaltest=np.zeros_like(errors)
 rows=[]
 for j,b in enumerate(BANDS):
  for fold in np.unique(folds):
   tst=folds==fold;cal=folds==(fold%5+1);fit=(~tst)&(~cal)
   mdl=GradientBoostingRegressor(random_state=100+j,**params)
   mdl.fit(F[j][fit],errors[fit,j]); pcal=np.maximum(.01,mdl.predict(F[j][cal]));pt=np.maximum(.01,mdl.predict(F[j][tst]))
   # CQR-style margin from separate calibration fold. Spatial exchangeability NOT assumed.
   adj=max(0.,float(np.quantile(errors[cal,j]-pcal,.9,method='higher')))
   outtest[tst,j]=pt+adj
   globaltest[tst,j]=float(np.quantile(errors[cal,j],.9,method='higher'))
   rows.append(dict(banda=b,fold=int(fold),n_prueba=int(tst.sum()),
      margen_cqr=float(adj),cobertura_adaptativa=float(np.mean(errors[tst,j]<=outtest[tst,j])),
      cobertura_global=float(np.mean(errors[tst,j]<=globaltest[tst,j])),
      ancho_medio_adaptativo=float(2*np.mean(outtest[tst,j])),ancho_medio_global=float(2*np.mean(globaltest[tst,j]))))
  md=GradientBoostingRegressor(random_state=100+j,**params);md.fit(F[j],errors[:,j]);
  # Conservatively use mean CV calibration margin; no finite-sample coverage claim.
  margin=float(np.mean([row['margen_cqr'] for row in rows if row['banda']==b]))
  est[j]=np.maximum(.01,md.predict(mapF[j])+margin)
  est[j,observed_mask]=0
 cv=pd.DataFrame(rows);cv.to_csv(VAL/'cobertura_spatial_CQR_5_bloques.csv',index=False)
 summary=[]
 for j,b in enumerate(BANDS):
  summary.append(dict(banda=b,n_puntos=n,
    R2_V4_OOF=float(r2_score(truth[:,j],pred[:,j])),
    RMSE_V4_OOF=float(np.sqrt(np.mean((truth[:,j]-pred[:,j])**2))),
    cobertura_objetivo=0.9,
    cobertura_CQR_estimada=float(np.mean(errors[:,j]<=outtest[:,j])),
    cobertura_constante_estimada=float(np.mean(errors[:,j]<=globaltest[:,j])),
    anchura_median_CQR=float(np.median(outtest[:,j]*2)),
    anchura_median_constante=float(np.median(globaltest[:,j]*2)),
    area_celdas_fiables_cercanas=int(((est[j]<.75*np.std(source_y[:,j])) & (mapdist<=3000)).sum())))
 pd.DataFrame(summary).to_csv(VAL/'RESUMEN_COBERTURA_INTERVALOS_90.csv',index=False)
 geotiff('V5_RADIO_ERROR_90_EMPIRICO_7B.tif',est.reshape(7,profile['height'],profile['width']),profile,BANDS,
  'Semianchura error ~P90 adaptativa calibrada con bloques; validación empírica, NO intervalo teórico garantizado')
 np.savez_compressed(VAL/'residuales_y_rangos_validacion.npz',residual=truth-pred,abs_error=errors,out_test_radius=outtest,global_test_radius=globaltest,folds=folds)
 return est,mapdist,pred,truth,cv,pd.DataFrame(summary)


def original_fde(weights,arr):
 """Forward pass of the authors' Keras .h5 Dense/ReLU/Sigmoid model (no tensorflow required)."""
 xx=np.asarray(arr,dtype=np.float64)
 with h5py.File(weights,'r') as h:
  config=json.loads(h.attrs['model_config'])
  layers=[(v['name'],v['config']['activation']) for v in config['config']['layers'] if v['class_name']=='Dense']
  assert [x[0] for x in layers]==['dense','dense_1','dense_2','dense_3','dense_4','new']
  for name,activation in layers:
   group=h[f'model_weights/{name}/{name}'];xx=xx@group['kernel:0'][:]+group['bias:0'][:]
   if activation=='relu':xx=np.maximum(0,xx)
   elif activation=='sigmoid':xx=1/(1+np.exp(-np.clip(xx,-45,45)))
   else:raise ValueError('Unknown activation '+activation)
 return np.asarray(xx.ravel(),dtype=np.float32)


def simulate(spatial,stats,obs_mask,error90,xy,coords,weights,profile,nsim=40):
 H,W=profile['height'],profile['width'];n=H*W
 rr=np.random.default_rng(SEED);res=pd.read_csv(VAL/'oof_preds.csv')
 E=np.column_stack([res[f'{b}_OBS']-res[f'{b}_V4'] for b in BANDS]);Rcov=np.corrcoef(E,rowvar=False)
 chol=sqrtm_robust(Rcov,.5)
 distances=cKDTree(coords).query(xy)[0]
 # Smooth and condition stochastic perturbations to fade near exact anchors.
 taper=(1-np.exp(-((distances/2200.)**2))).reshape(H,W)
 ensemble_scores=[];sims_stats=[];sim_example=None
 sco_s0=original_fde(weights,spatial)
 sco_s1=original_fde(weights,stats)
 for t in range(nsim):
  noise=np.empty((7,H,W),dtype=float)
  for b in range(7):
   n0=rr.normal(size=(H,W));s=0.7*gaussian_filter(n0,1.4,mode='reflect')+0.3*gaussian_filter(n0,3.3,mode='reflect')
   noise[b]=(s-s.mean())/max(s.std(),1e-5)
  cor=(chol@noise.reshape(7,-1)).reshape(7,H,W)
  # Marginal P90/1.64485 approximately Gaussian scale, downweight long-range extrapolations by no means.
  perturb=(cor*error90.reshape(7,H,W)/1.64485*taper[None,:,:]).reshape(7,-1).T
  perturb[obs_mask,:]=0
  aa=spatial+perturb
  bb=stats+perturb
  if t==0:sim_example=bb.copy()
  for arr in (aa,bb):
   assert np.max(np.abs(arr[obs_mask]-spatial[obs_mask]))<1e-6
  ensemble_scores.append(original_fde(weights,aa))
  sims_stats.append(original_fde(weights,bb))
 P=np.asarray(ensemble_scores);S=np.asarray(sims_stats)
 def export(prefix,pred):
  q05,q50,q95=np.quantile(pred,[.05,.5,.95],axis=0)
  geotiff(prefix+'_FDE_P05.tif',q05.reshape(H,W),profile,['FDE_PERCENTIL_05'], 'Cola inferior FDE bajo ruido correlacionado condicionado a 763 observaciones')
  geotiff(prefix+'_FDE_MEDIANA.tif',q50.reshape(H,W),profile,['FDE_MEDIANA'], 'Mediana Monte Carlo, no probabilidad geológica calibrada')
  geotiff(prefix+'_FDE_P95.tif',q95.reshape(H,W),profile,['FDE_PERCENTIL_95'], 'Cola superior FDE bajo simulacion condicionada')
  geotiff(prefix+'_FDE_IQR.tif',(np.quantile(pred,.75,axis=0)-np.quantile(pred,.25,axis=0)).reshape(H,W),profile,['IQR_FDE'],'Rango intercuartílico del puntaje por simulación; no garantía predictiva')
  geotiff(prefix+'_FRACCION_PUNTAJE_MAYOR_070.tif',np.mean(pred>=.7,axis=0).reshape(H,W),profile,['FRACCION_SIMULACIONES_SUP_070'],'Frecuencia simulada puntaje FDE >= .70, NO probabilidad de yacimiento')
  return q50
 loc_m=export('V5_ESPACIAL',P);stat_m=export('V5_PERFIL',S)
 geotiff('V5_FDE_PUNTAJE_ESPACIAL_SIN_RUIDO.tif',sco_s0.reshape(H,W),profile,['FDE_FT_SCORE'],'Inferencia de pesos originales FDE sobre V4 espacial preservada')
 geotiff('V5_FDE_PUNTAJE_COPULA_SIN_RUIDO.tif',sco_s1.reshape(H,W),profile,['FDE_FT_SCORE'],'FDE sobre perfil estadístico copula V5, no mapa verificado')
 geotiff('V5_PCA_REALIZACION_PLAUSIBLE_7B.tif',sim_example.T.reshape(7,H,W),profile,BANDS,'Ejemplo singular de campo PCA simulado, no evidencia de depósito')
 qd=dict(nsim=nsim,seed=SEED,
       fraccion_score_070_espacial_base=float(np.mean(sco_s0>=.7)),
       fraccion_score_070_copula_base=float(np.mean(sco_s1>=.7)),
       fraccion_mediana_070_espacial=float(np.mean(loc_m>=.7)),
       fraccion_mediana_070_copula=float(np.mean(stat_m>=.7)),
       desacuerdo_promedio_fde_espacial=float(np.mean(np.quantile(P,.95,axis=0)-np.quantile(P,.05,axis=0))),
       desacuerdo_promedio_fde_copula=float(np.mean(np.quantile(S,.95,axis=0)-np.quantile(S,.05,axis=0))))
 (VAL/'resumen_ensamble_40.json').write_text(json.dumps(qd,indent=2,ensure_ascii=False),encoding='utf-8')
 return qd,(P,S)


def plot_outputs(base,stat,obsmask,distmap,error,summary,tests,cv,score,profile):
 H,W=profile['height'],profile['width'];ext=(159.05,159.05+W*1.2,977.585-H*1.2,977.585)
 # 7 PCA maps, comparable colormap V4 vs V5
 fig,axs=plt.subplots(7,3,figsize=(13,23),layout='constrained');
 for j,b in enumerate(BANDS):
  lo,hi=np.quantile(base[:,j],[.02,.98]); vmax=max(abs(lo),abs(hi))
  for ax,ar,name in zip(axs[j],(base[:,j],stat[:,j],stat[:,j]-base[:,j]),('Base espacial V4','V5 original-like (copula)','Diferencia V5−V4')):
   lim=vmax if name!='Diferencia V5−V4' else max(0.1,np.quantile(abs(stat[:,j]-base[:,j]),.99))
   im=ax.imshow(ar.reshape(H,W),cmap='RdBu_r',vmin=-lim,vmax=lim,extent=ext,interpolation='nearest')
   if j==0:ax.set_title(name,fontsize=11,weight='bold')
   if ax is axs[j,0]:ax.set_ylabel(b+' · Norte km',fontsize=9)
   if j==6:ax.set_xlabel('Este km')
   fig.colorbar(im,ax=ax,fraction=.045,pad=.01)
 fig.suptitle('Atlas PCA7 | similitud estadística ≠ equivalencia geográfica',fontsize=16,weight='bold')
 fig.savefig(FIG/'01_ATLAS_COMPARATIVO_7_BANDAS_V4_V5.png',dpi=150,bbox_inches='tight');plt.close(fig)
 # 4 maps
 fig,axs=plt.subplots(2,2,figsize=(13,10),layout='constrained')
 x=distmap.reshape(H,W)/1000
 for ax,a,tit,cmap in zip(axs.ravel(),[obsmask.reshape(H,W),x,error[1].reshape(H,W),error[4].reshape(H,W)],
  ['Celdas con PC auténticos','Distancia a evidencia (km)','Radio empírico PC2 (90 %)','Radio empírico PC5 (90 %)'],['Greys','viridis','magma','magma']):
  im=ax.imshow(a,extent=ext,origin='upper',interpolation='nearest',cmap=cmap);ax.set_title(tit,weight='bold');ax.set_xlabel('Este (km)');ax.set_ylabel('Norte (km)');fig.colorbar(im,ax=ax,shrink=.83)
 fig.suptitle('Trazabilidad espacial y error empírico adaptativo',fontsize=15,weight='bold');fig.savefig(FIG/'02_EVIDENCIA_DISTANCIA_Y_ERROR_90.png',dpi=170,bbox_inches='tight');plt.close(fig)
 # stat metrics cross-correlation
 d=pd.read_csv(VAL/'comparacion_test_581_SIN_COINCIDENCIAS.csv');subset=d.query('producto in ["V4_PERFIL","V5_COPULA"]')
 pivot=subset.pivot(index='metrica',columns='producto',values='valor')
 fig,axs=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
 for ax,met in zip(axs,['KS_medio','error_matriz_correlacion_Frob','W1_proyecciones']):
  values=pivot.loc[met]
  ax.bar(['V4','V5'],[values['V4_PERFIL'],values['V5_COPULA']]);ax.set_title(met.replace('_',' '),weight='bold');ax.set_ylabel('Menor es mejor');
  for i,v in enumerate([values['V4_PERFIL'],values['V5_COPULA']]):ax.text(i,v,f'{v:.3f}',ha='center',va='bottom',fontsize=10)
 fig.suptitle('Contraste estadístico estricto · 581 perfiles sin coincidencias',weight='bold',fontsize=14)
 fig.savefig(FIG/'03_TEST_RESERVADO_MULTIVARIANTE.png',dpi=160,bbox_inches='tight');plt.close(fig)
 # geometric performance CV and coverage
 fig,axs=plt.subplots(1,2,figsize=(14,4.7),layout='constrained')
 ss=summary;ii=np.arange(7);w=.35
 axs[0].bar(ii-w/2,ss.cobertura_CQR_estimada,width=w,label='Error adaptativo CQR')
 axs[0].bar(ii+w/2,ss.cobertura_constante_estimada,width=w,label='Error global')
 axs[0].axhline(.9,ls='--',lw=1.2,color='black',label='90 % nominal');axs[0].set_ylim(0,1.05)
 axs[0].set_xticks(ii,BANDS);axs[0].set_title('Cobertura fuera de bloque (descriptiva)',weight='bold');axs[0].legend(fontsize=8)
 axs[1].bar(ii-w/2,ss.anchura_median_CQR,width=w,label='Adaptativa')
 axs[1].bar(ii+w/2,ss.anchura_median_constante,width=w,label='Constante')
 axs[1].set_xticks(ii,BANDS);axs[1].set_title('Anchura mediana de intervalos (unidades PCA)',weight='bold');axs[1].legend(fontsize=8)
 fig.savefig(FIG/'04_VALIDACION_INTERVALOS_ESPACIALES.png',dpi=170,bbox_inches='tight');plt.close(fig)
 # 2x3 FDE
 P,S=score
 fig,axs=plt.subplots(2,3,figsize=(15,9),layout='constrained')
 for row,x,label in [(0,P,'Modelo espacial'),(1,S,'Perfil estadístico')]:
  dat=[np.median(x,axis=0),np.quantile(x,.95,axis=0)-np.quantile(x,.05,axis=0),np.mean(x>=.7,axis=0)]
  titles=['Mediana FDE','Amplitud P95−P05','Fracción de puntajes ≥ 0,70']
  for c,(v,t) in enumerate(zip(dat,titles)):
   im=axs[row,c].imshow(v.reshape(H,W),extent=ext,cmap='viridis',vmin=0,vmax=1 if c!=1 else np.quantile(v,.98),interpolation='nearest')
   axs[row,c].set_title(label+' | '+t,fontsize=10,weight='bold');axs[row,c].set_xlabel('Este (km)');axs[row,c].set_ylabel('Norte (km)');fig.colorbar(im,ax=axs[row,c],fraction=.045,pad=.02)
 fig.suptitle('Sensibilidad de FDE-FT bajo 40 campos PCA simulados',weight='bold',fontsize=14)
 fig.savefig(FIG/'05_INCERTIDUMBRE_DEL_PUNTAJE_FDE.png',dpi=165,bbox_inches='tight');plt.close(fig)


def main():
 t=time.time()
 old,prof,trans,crs=read_tif(GIS/'PCA7_V4_ESPACIAL_PREDICCION_7B.tif')
 stat0,pp,_,_=read_tif(GIS/'PCA7_V4_PERFIL_ESTADISTICO_3000_7B.tif')
 quality,_,_,_=read_tif(GIS/'CALIDAD_CELDAS.tif')
 assert old.shape==(7,110,118) and stat0.shape==old.shape and crs.to_epsg()==3579
 H,W=prof['height'],prof['width'];N=H*W
 spatial=old.reshape(7,-1).T.astype(float)
 stats=stat0.reshape(7,-1).T.astype(float)
 anchor=quality[0].ravel()==1;assert anchor.sum()==763
 assert np.array_equal(old[:,anchor.reshape(H,W)],stat0[:,anchor.reshape(H,W)])
 rr,cc=np.indices((H,W));xy=np.column_stack([trans.c+(cc.ravel()+.5)*trans.a,trans.f+(rr.ravel()+.5)*trans.e])
 anchors_xy=xy[anchor]
 ref=pd.read_csv(INPUT/'013_Random.csv')[BANDS].to_numpy(float)
 cal,val,test=reference_partition(ref)
 V5,chosen,dirs=choose_transport(stats,anchor,cal,val)
 geotiff('PCA7_V5_COPULA_ORIGINAL_LIKE_7B.tif',V5.T.reshape(7,H,W),prof,BANDS,
  'Perfil marginal V4 más corrección multivariante calibrada en validación de datos sin coordenadas; anclas exactas')
 geotiff('PCA7_V5_ESPACIAL_RECOMENDADO_7B.tif',old,prof,BANDS,
  'V4 espacial preservado como predictor de posición por no existir ganancia geoespacial demostrada para corrección distribucional')
 dat=[]
 for name,arr in [('V4_ESPACIAL',spatial),('V4_PERFIL',stats),('V5_COPULA',V5)]:
  for q,y in eval_dist(arr,test,dirs).items():dat.append(dict(producto=name,metrica=q,valor=y))
 pd.DataFrame(dat).to_csv(VAL/'comparacion_V4_V5_test_reservado.csv',index=False)
 # Stronger audit: omit PCA profiles duplicated in original geolocated training/pretext sources.
 known_pc=np.vstack([pd.read_csv(INPUT/'02_Train_PCA.csv')[BANDS].to_numpy(float),pd.read_csv(INPUT/'03_Train_Pretext.csv')[BANDS].to_numpy(float)])
 known_signatures={tuple(z) for z in known_pc}
 strict=np.asarray([z for z in test if tuple(z) not in known_signatures]);assert len(strict)==581
 pd.DataFrame(strict,columns=BANDS).to_csv(VAL/'perfiles_test_581_sin_coincidencias.csv',index=False)
 pd.DataFrame([z for z in test if tuple(z) in known_signatures],columns=BANDS).to_csv(VAL/'perfiles_test_26_excluidos_por_coincidencia.csv',index=False)
 strictly=[]
 for label,arr in [('V4_ESPACIAL',spatial),('V4_PERFIL',stats),('V5_COPULA',V5)]:
  for key,val0 in eval_dist(arr,strict,dirs).items():strictly.append(dict(producto=label,metrica=key,valor=val0))
 pd.DataFrame(strictly).to_csv(VAL/'comparacion_test_581_SIN_COINCIDENCIAS.csv',index=False)
 cov_ref=corrs(strict);cov_v4=corrs(stats);cov_v5=corrs(V5)
 pd.DataFrame(cov_ref,index=BANDS,columns=BANDS).to_csv(VAL/'matriz_correlacion_REFERENCIA_test.csv')
 pd.DataFrame(cov_v4,index=BANDS,columns=BANDS).to_csv(VAL/'matriz_correlacion_V4.csv')
 pd.DataFrame(cov_v5,index=BANDS,columns=BANDS).to_csv(VAL/'matriz_correlacion_V5.csv')
 oof=pd.read_csv(VAL/'oof_preds.csv').sort_values('id_celda')
 assert (oof.id_celda.values==np.flatnonzero(anchor)).all()
 X=oof[['E_centro','N_centro']].to_numpy(float);Y=np.column_stack([oof[f'{j}_OBS'] for j in BANDS])
 assert np.max(np.abs(spatial[anchor]-Y))<5e-5
 q90,dist,pred,truth,cv,summary=uncertainty_model(oof,X,anchors_xy,Y,xy,anchor,prof,spatial)
 geotiff('V5_DISTANCIA_A_DATO_AUTENTICO_M.tif',dist.reshape(H,W),prof,['DISTANCIA_M'],'Separación hasta observación PC más cercana')
 # Conservatively distinguish direct data, 3km supported, >3km and high predictive uncertainty.
 absnorm=q90/np.maximum(.05,Y.std(axis=0)[:,None])
 risk=np.mean(absnorm,axis=0)
 geotiff('V5_INDICE_RIESGO_INTERPOLACION.tif',risk.reshape(H,W),prof,['RIESGO_NORMALIZADO_7_BANDAS'],
  'Media de radios de error P90/SD por banda, indicador descriptivo, no probabilidad de error')
 coverage=np.select([anchor,dist<=3000,dist<=6000,dist<=10000],[1,2,3,4],default=5).astype(float)
 geotiff('V5_PROCEDENCIA_1_OBSERVADO_2_3KM_3_6KM_4_10KM_5_LEJOS.tif',coverage.reshape(H,W),prof,['ESTADO'],
  '1 original; 2 <=3km; 3 3-6 km; 4 6-10km; 5 >10km; clasificacion de soporte no de probabilidad')
 # Conservative region: 3km AND estimated P90 less than 1 SD in five of seven channels
 confid=((q90<Y.std(axis=0)[:,None]).sum(axis=0)>=5)&(dist<=3000)
 confid[anchor]=True
 geotiff('V5_MASCARA_SOPORTE_CERCANO_5DE7.tif',confid.reshape(H,W).astype(float),prof,['SUPORTE_1_SI_0_NO'],
  'Filtro propuesto: <=3km y q90 menor que 1 SD en >=5 PCs (heurístico)')
 restrict=spatial.T.reshape(7,H,W).copy();restrict[:,~confid.reshape(H,W)]=-9999.
 geotiff('PCA7_V5_SOLO_SOPORTE_CERCANO_7B.tif',restrict,prof,BANDS,
  'Modelo espacial V4 restringido a soporte cercano; NoData no representa ausencia de minerales')
 w=INPUT/'autoencoder_fine.h5'
 ens,sc=simulate(spatial,V5,anchor,q90,xy,anchors_xy,w,prof,nsim=40)
 plot_outputs(spatial,V5,anchor,dist,q90,summary,pd.DataFrame(dat),cv,sc,prof)
 report={
  'date':'2026-10-27','workflow':'V5 condicionada a observaciones PCA existentes',
  'geometry':'EPSG:3579, 110x118 celdas de 1200m (inferido desde CSV; artículo menciona 1100m)',
  'original_tif_recovered':False,'cells':N,'original_cells':int(anchor.sum()),'estimated_cells':int((~anchor).sum()),
  'ref_sizes':{'train':len(cal),'validation':len(val),'test':len(test)},
  'copula_choice':{k:float(v) for k,v in chosen.items()},
  'heldout_statistic':{q:{k:float(v) for k,v in eval_dist(a,test,dirs).items()} for q,a in [('V4',stats),('V5',V5)]},
  'heldout_statistic_strict_nonoverlap_581':{q:{k:float(v) for k,v in eval_dist(a,strict,dirs).items()} for q,a in [('V4',stats),('V5',V5)]},
  'heldout_strict_n':len(strict),'overlap_excluded':len(test)-len(strict),
  'empirical_coverage_CQR_7band_mean':float(summary.cobertura_CQR_estimada.mean()),
  'empirical_coverage_constant_7band_mean':float(summary.cobertura_constante_estimada.mean()),
  'mask_cells':int(confid.sum()),
  'ensemble':ens,
  'limitations':['La prueba estadística de 607 observaciones no contiene coordenadas.','Los intervalos adaptativos no garantizan cobertura nominal bajo dependencia espacial.','Simulaciones muestran incertidumbre condicionada al modelo, no posición de depósitos verificadas.','La evaluación de la red neuronal es sensibilidad de puntaje, no validación de reservas.','El archivo fuente 02_PCA.tif original continúa ausente.']}
 (VAL/'METADATOS_V5_AUDITABLE.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
 print('V5 RESULTS',json.dumps({k:v for k,v in report.items() if k in ('copula_choice','heldout_statistic','empirical_coverage_CQR_7band_mean','mask_cells','ensemble')},indent=2))
 print('elapsed_s',round(time.time()-t,1))

if __name__=='__main__':main()
