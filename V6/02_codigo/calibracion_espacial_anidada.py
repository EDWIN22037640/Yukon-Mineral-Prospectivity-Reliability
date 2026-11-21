"""Nested spatial held-out sigmoid calibration; compares SAME base model raw vs calibrated."""
import os, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.model_selection import StratifiedGroupKFold,GroupShuffleSplit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
from scipy.special import logit
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analisis_final import ROOT,DATA,OUT,FIG,PCC,fit_predict,metrics,make_group
xy0=pd.read_csv(DATA/'01_Train_VO.csv');p0=pd.read_csv(DATA/'02_Train_PCA.csv')
d=pd.concat([p0,xy0[['ESTE','NORTE']]],axis=1)
d=d[(d.ESTE>0)&(d.NORTE>0)].drop_duplicates(PCC).reset_index(drop=True)
X=d[PCC].to_numpy(dtype='float32');y=d.DEP.astype(int).to_numpy();xy=d[['ESTE','NORTE']].to_numpy()
groups=make_group(xy,30000,0)
outer=list(StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=17).split(X,y,groups))
preds=[];cal_splits=[]
for fold,(itra,iv) in enumerate(outer):
    cands=list(GroupShuffleSplit(n_splits=30,test_size=.23,random_state=710+fold).split(X[itra],y[itra],groups[itra]))
    chosen=None
    for left,mid in cands:
        if int(y[itra[mid]].sum())>=4 and int((y[itra[mid]]==0).sum())>=4 and int(y[itra[left]].sum())>=12:
            chosen=(itra[left],itra[mid]);break
    if chosen is None:raise RuntimeError('calibration inner split class issue')
    it,ic=chosen
    assert set(it).isdisjoint(ic) and set(it).isdisjoint(iv) and set(ic).isdisjoint(iv)
    assert set(groups[it]).isdisjoint(set(groups[ic])) and set(groups[it]).isdisjoint(set(groups[iv]))
    cal_splits.append(dict(fold=fold,n_model_train=len(it),n_calibration=len(ic),n_test=len(iv),
        positive_model_train=int(y[it].sum()),positive_calibration=int(y[ic].sum()),positive_test=int(y[iv].sum()),
        calibration_groups=len(np.unique(groups[ic]))))
    for m in ['RF','LR','FDE-FT']:
        sd=10102026+fold*37+['RF','LR','FDE-FT'].index(m)
        p_cal=fit_predict(m,X[it],y[it],X[ic],sd)
        p_test=fit_predict(m,X[it],y[it],X[iv],sd) # deterministic identical base fit with same seed
        calib=LogisticRegression(C=1.0,solver='lbfgs',max_iter=1000,random_state=sd)
        calib.fit(logit(np.clip(p_cal,1e-5,1-1e-5)).reshape(-1,1),y[ic])
        p_new=calib.predict_proba(logit(np.clip(p_test,1e-5,1-1e-5)).reshape(-1,1))[:,1]
        for j,q,r in zip(iv,p_test,p_new):preds.append(dict(row=int(j),fold=fold,modelo=m,etiqueta=int(y[j]),
                                              sin_calibrar=float(q),platt_espacial=float(r)))
    print('INNER DONE',fold,flush=True)
pd.DataFrame(cal_splits).to_csv(OUT/'AUDITORIA_PARTICIONES_CALIBRACION_INTERNA.csv',index=False)
pr=pd.DataFrame(preds);pr.to_csv(OUT/'PREDICCIONES_CALIBRACION_ESPACIAL_ANIDADA.csv',index=False)
res=[]
for m in ['RF','LR','FDE-FT']:
    pp=pr[pr.modelo==m].sort_values('row');y_=pp.etiqueta.to_numpy()
    for tag,col in [('Sin calibración','sin_calibrar'),('Sigmoide interna','platt_espacial')]:
        mm=metrics(y_,pp[col].to_numpy());res.append(dict(modelo=m,metodo=tag,**mm))
r=pd.DataFrame(res);r.to_csv(OUT/'RESULTADOS_CALIBRACION_ESPACIAL_ANIDADA.csv',index=False)
fig,axs=plt.subplots(1,3,figsize=(14,4.4),sharex=True,sharey=True)
for ax,m in zip(axs,['RF','LR','FDE-FT']):
    dd=pr[pr.modelo==m]
    for col,label,color in [('sin_calibrar','Original','#c17b08'),('platt_espacial','Platt interna','#087e86')]:
        yy=dd.etiqueta.to_numpy();pp=dd[col].to_numpy();x=[];v=[]
        for lo,hi in zip(np.linspace(0,1,6)[:-1],np.linspace(0,1,6)[1:]):
            idx=(pp>=lo)&(pp<hi if hi<1 else pp<=hi)
            if idx.sum()>=5:x.append(pp[idx].mean());v.append(yy[idx].mean())
        ax.plot(x,v,'o-',color=color,lw=2,label=f'{label}: Brier={brier_score_loss(yy,pp):.3f}')
    ax.plot([0,1],[0,1],ls='--',color='gray',alpha=.6);ax.set_title(m,fontweight='bold');ax.grid(alpha=.13);ax.legend(fontsize=7)
    ax.set_xlabel('Puntaje predicho')
axs[0].set_ylabel('Frecuencia positiva observada');fig.suptitle('Calibración interna honesta · bloque espacial de prueba nunca usado para ajustar',fontweight='bold');fig.tight_layout()
fig.savefig(FIG/'08_CALIBRACION_PLATT_ESPACIAL_ANIDADA.png',dpi=180,bbox_inches='tight');plt.close(fig)
print(r.to_string(index=False))
