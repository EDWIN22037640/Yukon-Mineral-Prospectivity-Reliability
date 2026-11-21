"""Auditoría de confiabilidad Yukón — validación aleatoria vs espacial.
Uso: python 02_codigo/analisis_final.py (desde la raíz del proyecto).
Datos: originales del repositorio TransferProspectivityLearning (2024).
Modelo FDE-FT REENTRENADO por partición, pesos del autoencoder original.
No se utiliza el ráster reconstruido para el contraste principal.
"""
from __future__ import annotations
import json, os, hashlib, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import h5py
import torch
import torch.nn.functional as F
from torch import nn
from scipy.spatial import cKDTree
from sklearn.model_selection import StratifiedKFold, StratifiedGroupKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (roc_auc_score, average_precision_score, balanced_accuracy_score, f1_score,
precision_score, recall_score, brier_score_loss, log_loss, confusion_matrix, roc_curve, precision_recall_curve)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
warnings.filterwarnings('ignore', category=FutureWarning)

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'01_fuentes'; OUT=ROOT/'03_resultados'; FIG=ROOT/'04_figuras'
OUT.mkdir(exist_ok=True,parents=True);FIG.mkdir(exist_ok=True,parents=True)
PARTS=ROOT/'06_reproducibilidad'/'particiones_intermedias'; PARTS.mkdir(exist_ok=True,parents=True)
PCC=[f'PC{i}' for i in range(1,8)]
SEED=20261027
np.random.seed(SEED)
torch.set_num_threads(1)

class FDEFT(nn.Module):
    """7-100-8-6-4-2-1; encoder pretrained on geological pixels, fine-tune supervised inside fold."""
    def __init__(self):
        super().__init__()
        sizes=[7,100,8,6,4,2]
        lay=[]
        for a,b in zip(sizes[:-1],sizes[1:]): lay.extend([nn.Linear(a,b),nn.ReLU()])
        self.encoder=nn.Sequential(*lay)
        self.head=nn.Linear(2,1)
        self._read_encoder_weights()
    def _read_encoder_weights(self):
        with h5py.File(DATA/'modelo_encoder_original.h5','r') as hh:
            with torch.no_grad():
                for i in range(5):
                    name='dense' if i==0 else f'dense_{i}'
                    w=np.array(hh['model_weights'][name][name]['kernel:0']); b=np.array(hh['model_weights'][name][name]['bias:0'])
                    self.encoder[2*i].weight.copy_(torch.from_numpy(w.T))
                    self.encoder[2*i].bias.copy_(torch.from_numpy(b))
    def forward(self,x):return self.head(self.encoder(x)).squeeze(-1)

def fde_train_predict(Xtr,ytr,Xte,seed,epochs=1500):
    torch.manual_seed(seed); model=FDEFT()
    tx=torch.tensor(np.asarray(Xtr,dtype='float32'));ty=torch.tensor(np.asarray(ytr,dtype='float32'))
    vx=torch.tensor(np.asarray(Xte,dtype='float32'))
    npos=np.sum(ytr==1);nneg=np.sum(ytr==0)
    # Inverse class frequency, equivalent positive-to-negative loss weight n0/n1
    posw=torch.tensor(float(nneg/max(npos,1)),dtype=torch.float32)
    optimizer=torch.optim.Adam([{'params':model.encoder.parameters(),'lr':5e-5},
                                {'params':model.head.parameters(),'lr':1e-3}],weight_decay=1e-5)
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        logits=model(tx)
        loss=F.binary_cross_entropy_with_logits(logits,ty,pos_weight=posw)
        loss.backward();optimizer.step()
    model.eval()
    with torch.no_grad():return torch.sigmoid(model(vx)).numpy().ravel()

def saved_fde_predict(X):
    """Verificación por h5py del modelo original ya entrenado con todos los datos (NO CV)."""
    xx=np.asarray(X,float)
    with h5py.File(DATA/'FDE_FT_original_completo.h5','r') as hh:
        for i in range(6):
            name=('dense' if i==0 else f'dense_{i}') if i!=5 else 'new'
            layer=hh['model_weights'][name][name]
            xx=xx@np.asarray(layer['kernel:0'])+np.asarray(layer['bias:0'])
            xx=np.maximum(xx,0) if i!=5 else 1/(1+np.exp(-np.clip(xx,-50,50)))
    return xx.ravel()

def fit_predict(name,xtr,ytr,xte,fold_seed):
    if name=='RF':
        model=RandomForestClassifier(n_estimators=400,min_samples_leaf=2,class_weight='balanced_subsample',
                                    max_features='sqrt',random_state=fold_seed,n_jobs=1)
        model.fit(xtr,ytr);return model.predict_proba(xte)[:,1]
    if name=='LR':
        model=make_pipeline(StandardScaler(),LogisticRegression(C=1.0,class_weight='balanced',max_iter=3000,random_state=fold_seed))
        model.fit(xtr,ytr);return model.predict_proba(xte)[:,1]
    if name=='FDE-FT':return fde_train_predict(xtr,ytr,xte,fold_seed)
    raise ValueError(name)

def ece(y,p,bins=10):
    edges=np.linspace(0,1,bins+1);idx=np.clip(np.digitize(p,edges[1:-1]),0,bins-1)
    return float(sum(np.sum(idx==k)*abs(np.mean(y[idx==k])-np.mean(p[idx==k])) for k in range(bins) if np.any(idx==k))/len(y))

def metrics(y,p):
    p=np.clip(np.asarray(p,dtype=float),1e-6,1-1e-6);y=np.asarray(y,dtype=int)
    zz=(p>=.5).astype(int)
    return dict(n=len(y),n_pos=int(y.sum()),AUC=roc_auc_score(y,p) if np.unique(y).size==2 else np.nan,
                AP=average_precision_score(y,p),F1=f1_score(y,zz,zero_division=0),
                recall=recall_score(y,zz,zero_division=0), precision=precision_score(y,zz,zero_division=0),
                balanced_accuracy=balanced_accuracy_score(y,zz),
                Brier=brier_score_loss(y,p),log_loss=log_loss(y,p,labels=[0,1]),ECE10=ece(y,p))

def make_group(coord,blocks,shift=0):
    v=np.floor(coord/blocks+shift).astype(int)
    return (v[:,0]-v[:,0].min())*1000+(v[:,1]-v[:,1].min())

def grouped_boot(primary, y, block30, B=1800):
    # Paired group bootstrap: conditional on trained OOF predictions, not independent inference on full training process.
    rs=np.random.default_rng(909)
    groups=np.unique(block30); ids={g:np.where(block30==g)[0] for g in groups}
    keys={ (row.protocolo,row.modelo):row for row in primary.itertuples(index=False) }
    cases=[('aleatoria','RF'),('espacial30','RF'),('espacial30_buffer3','RF'),
           ('espacial30','LR'),('espacial30','FDE-FT'),('aleatoria','FDE-FT'),('espacial20','RF')]
    probs={k:np.array(keys[k].probabilidades) for k in cases if k in keys}
    observed={k:roc_auc_score(y,p) for k,p in probs.items()}
    draws={k:[] for k in cases if k in probs}
    deltas={'RF_aleatoria_menos_espacial30':[], 'FDE_menos_RF_espacial30':[],
            'RF_espacial30_menos_espacial30_buffer3':[]}
    for b in range(B):
        sampled=rs.choice(groups,size=len(groups),replace=True)
        ii=np.concatenate([ids[g] for g in sampled])
        if np.unique(y[ii]).size!=2:continue
        mb={k:roc_auc_score(y[ii],p[ii]) for k,p in probs.items()}
        for k,v in mb.items():draws[k].append(v)
        if ('aleatoria','RF') in mb and ('espacial30','RF') in mb:
            deltas['RF_aleatoria_menos_espacial30'].append(mb['aleatoria','RF']-mb['espacial30','RF'])
        if ('espacial30','FDE-FT') in mb and ('espacial30','RF') in mb:
            deltas['FDE_menos_RF_espacial30'].append(mb['espacial30','FDE-FT']-mb['espacial30','RF'])
        if ('espacial30','RF') in mb and ('espacial30_buffer3','RF') in mb:
            deltas['RF_espacial30_menos_espacial30_buffer3'].append(mb['espacial30','RF']-mb['espacial30_buffer3','RF'])
    bb=[]
    for (protocol,model),v in draws.items():
        if v:bb.append(dict(tipo='AUC',contraste=protocol+' '+model,estimacion=observed[protocol,model],
                            IC95_inf=np.quantile(v,.025),IC95_sup=np.quantile(v,.975), B=len(v)))
    for k,v in deltas.items():
        v=np.asarray(v);bb.append(dict(tipo='Diferencia AUC',contraste=k,
                                       estimacion=float({'RF_aleatoria_menos_espacial30': observed['aleatoria','RF']-observed['espacial30','RF'], 'FDE_menos_RF_espacial30': observed['espacial30','FDE-FT']-observed['espacial30','RF'], 'RF_espacial30_menos_espacial30_buffer3': observed['espacial30','RF']-observed['espacial30_buffer3','RF']}[k]), IC95_inf=float(np.quantile(v,.025)),
                                       IC95_sup=float(np.quantile(v,.975)),B=len(v),
                                       p_bootstrap_exploratorio=float(min(1,2*min(np.mean(v<=0),np.mean(v>=0))))))
    return pd.DataFrame(bb)

def save_figures(pred_df,metric_df,primary,blocks, audited):
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.right':False,'axes.spines.top':False,
                         'axes.titleweight':'bold','font.size':10,'savefig.dpi':180})
    models=['RF','LR','FDE-FT']; protocols=['aleatoria','espacial20','espacial30','espacial30_buffer3']
    labels=['Aleatoria','Espacial 20 km','Espacial 30 km','Espacial 30 km + 3 km separación']
    cols={'RF':'#155e75','LR':'#d97706','FDE-FT':'#6d28d9'}
    fig,ax=plt.subplots(figsize=(10.8,5.5)); x=np.arange(4)
    for k,m in enumerate(models):
        vals=[metric_df[(metric_df.protocolo==p)&(metric_df.modelo==m)].AUC.mean() for p in protocols]
        e=[metric_df[(metric_df.protocolo==p)&(metric_df.modelo==m)].AUC.std(ddof=1) for p in protocols]
        ax.bar(x+(k-1)*.24,vals,width=.225,label=m,color=cols[m],alpha=.87)
        ax.errorbar(x+(k-1)*.24,vals,yerr=e,fmt='none',capsize=4,color='#30353d',lw=1)
        for x0,val in zip(x+(k-1)*.24,vals):ax.text(x0,val+.016,f'{val:.3f}',fontsize=7,ha='center')
    ax.set_xticks(x,labels);ax.set_ylim(0,1.05);ax.set_ylabel('AUC ROC');ax.set_title('Comparación homogénea de los tres algoritmos\nVariabilidad entre dos réplicas de validación')
    ax.legend(ncol=3,frameon=False,loc='lower left');ax.grid(axis='y',alpha=.15);fig.tight_layout()
    fig.savefig(FIG/'01_AUC_PROTOCOLOS_TRES_MODELOS.png',bbox_inches='tight');plt.close(fig)

    fig,axs=plt.subplots(1,3,figsize=(14,4.7),sharex=True,sharey=True)
    for a,m in zip(axs,models):
        for p,l in [('aleatoria','Aleatoria'),('espacial30','Espacial 30 km'),('espacial30_buffer3','Espacial + buffer')]:
            row=primary[(primary.protocolo==p)&(primary.modelo==m)].iloc[0]
            y=np.asarray(row.etiquetas); pp=np.asarray(row.probabilidades)
            fpr,tpr,_=roc_curve(y,pp);a.plot(fpr,tpr,lw=2,label=f'{l}: {roc_auc_score(y,pp):.3f}')
        a.plot([0,1],[0,1],ls='--',color='gray',alpha=.6);a.set_title(m);a.set_xlabel('Falsos positivos');a.grid(alpha=.18);a.legend(fontsize=7,loc='lower right')
    axs[0].set_ylabel('Verdaderos positivos');fig.suptitle('Curvas ROC · Predicciones fuera de muestra (réplica primaria)',fontweight='bold');fig.tight_layout()
    fig.savefig(FIG/'02_ROC_CV_COMPARATIVO.png',bbox_inches='tight');plt.close(fig)

    fig,axs=plt.subplots(1,3,figsize=(13.5,4.8),sharex=True,sharey=True)
    for a,m in zip(axs,models):
        for p,l,ls in [('aleatoria','Aleatoria','-'),('espacial30','Espacial 30 km','--')]:
            row=primary[(primary.protocolo==p)&(primary.modelo==m)].iloc[0]
            yy=np.asarray(row.etiquetas);pp=np.asarray(row.probabilidades)
            bins=np.linspace(0,1,6); xx=[];obs=[];cts=[]
            for lo,hi in zip(bins[:-1],bins[1:]):
                mm=(pp>=lo)&(pp<(hi if hi<1 else 1.00001))
                if mm.sum()>=5:
                    xx.append(pp[mm].mean());obs.append(yy[mm].mean());cts.append(mm.sum())
            a.plot(xx,obs,'o',linestyle=ls,label=f'{l} (Brier={brier_score_loss(yy,pp):.3f})')
        a.plot([0,1],[0,1],color='gray',ls=':',lw=1.3);a.set_title(m);a.grid(alpha=.13);a.set_xlabel('Puntaje medio predicho');a.legend(fontsize=7,loc='upper left')
    axs[0].set_ylabel('Frecuencia empírica positiva');fig.suptitle('Diagnóstico de calibración · 5 intervalos (≥ 5 casos por intervalo)',fontweight='bold');fig.tight_layout()
    fig.savefig(FIG/'03_CALIBRACION_BRIER.png',bbox_inches='tight');plt.close(fig)

    fig,ax=plt.subplots(figsize=(9.6,5.3))
    v=audited.copy();v=v[v['ESTE']>0];m=v.DEP==1
    ax.scatter(v.loc[~m,'ESTE']/1000,v.loc[~m,'NORTE']/1000,c='#6b7280',s=18,alpha=.65,label='Sin ocurrencia',edgecolors='none')
    ax.scatter(v.loc[m,'ESTE']/1000,v.loc[m,'NORTE']/1000,c='#b91c1c',s=24,alpha=.9,label='Ocurrencia',edgecolors='none')
    for x0 in np.arange(np.floor(v.ESTE.min()/30000)*30,np.ceil(v.ESTE.max()/30000)*30+30,30): ax.axvline(x0,color='#0284c7',alpha=.18,lw=.7)
    for y0 in np.arange(np.floor(v.NORTE.min()/30000)*30,np.ceil(v.NORTE.max()/30000)*30+30,30): ax.axhline(y0,color='#0284c7',alpha=.18,lw=.7)
    ax.set_xlabel('Este (km, EPSG:3579)');ax.set_ylabel('Norte (km, EPSG:3579)');ax.set_title('Puntos originales y retícula de validación espacial de 30 km')
    ax.set_aspect('equal');ax.legend(frameon=False);fig.tight_layout();fig.savefig(FIG/'04_BLOQUES_Y_PUNTOS_ORIGINALES.png',bbox_inches='tight');plt.close(fig)

    fig,axs=plt.subplots(1,2,figsize=(11,4.5))
    for i,p in enumerate(['aleatoria','espacial30']):
        a=axs[i]
        for m in models:
            row=primary[(primary.protocolo==p)&(primary.modelo==m)].iloc[0]
            yy=np.asarray(row.etiquetas);pp=np.asarray(row.probabilidades)
            prec,rec,_=precision_recall_curve(yy,pp)
            a.plot(rec,prec,lw=1.8,label=f'{m}: {average_precision_score(yy,pp):.3f}',color=cols[m])
        a.axhline(y.mean(),color='#444',ls=':',label=f'Prevalencia: {y.mean():.3f}')
        a.set(xlabel='Sensibilidad',ylabel='Precisión',xlim=(0,1),ylim=(0,1.03),title='Aleatoria' if i==0 else 'Espacial 30 km');a.grid(alpha=.16);a.legend(fontsize=8)
    fig.suptitle('Curvas precisión–recall (mismas observaciones)',fontweight='bold');fig.tight_layout();fig.savefig(FIG/'05_PRECISION_RECALL.png',bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
    t0=time.time()
    train=pd.read_csv(DATA/'02_Train_PCA.csv'); raw=pd.read_csv(DATA/'01_Train_VO.csv'); external=pd.read_csv(DATA/'04_Validation_Points.csv')
    assert len(train)==len(raw)==313 and np.array_equal(train.DEP.values,raw.DEP.values)
    all_data=pd.concat([train,raw[['ESTE','NORTE']]],axis=1)
    valid=(all_data.ESTE>0)&(all_data.NORTE>0)
    usable=all_data.loc[valid].copy().drop_duplicates(subset=PCC).reset_index(drop=True)
    X=usable[PCC].values.astype('float32');y=usable.DEP.astype(int).to_numpy();xy=usable[['ESTE','NORTE']].to_numpy()
    # Signature matches are exact at the published 5-decimal precision.
    d_train={tuple(x) for x in train[PCC].values}
    matches=external[PCC].apply(lambda r:tuple(r.values) in d_train,axis=1)
    external2=external.assign(COINCIDE_FIRMA_ENTRENAMIENTO=matches.values)
    external2.to_csv(OUT/'AUDITORIA_REGISTROS_VALIDACION.csv',index=False)
    train_pair=pd.concat([train,raw[['ESTE','NORTE']]],axis=1)
    grouptrain=train_pair.groupby(PCC,sort=False).agg(repeticiones=('DEP','size'),etiquetas_distintas=('DEP','nunique')).reset_index()
    grouptrain[grouptrain.repeticiones>1].to_csv(OUT/'AUDITORIA_FIRMAS_REPETIDAS_ENTRENAMIENTO.csv',index=False)
    audit=dict(original_train=313, original_positives=int((train.DEP==1).sum()), original_negatives=int((train.DEP==0).sum()),
               invalid_coordinates=int((~valid).sum()), repeated_rows_by_signature=int(train.duplicated(PCC).sum()),
               valid_coordinate_unique_signatures=len(usable),usable_positive=int(y.sum()),usable_negative=int(len(y)-y.sum()),
               external_rows=len(external),external_labels=external.DEP.value_counts().to_dict(),
               external_matching_rows=int(matches.sum()),external_matching_unique_signatures=int(external.loc[matches,PCC].drop_duplicates().shape[0]),
               external_independent_rows=int((~matches).sum()),external_independent_class_count=external.loc[~matches,'DEP'].value_counts().to_dict(),
               contradictory_labels_for_same_train_signature=int((grouptrain.etiquetas_distintas>1).sum()),
               external_coordinates_available=False, original_raster_available=False,
               spatial_coordinates_system='EPSG:3579 (fuentes originales)')
    (OUT/'AUDITORIA_INVENTARIO.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')
    results=[]; preds=[]; foldstat=[]; model_names=['RF','LR','FDE-FT']
    replicates=[(0,17,0),(1,29,0.39)]
    protocols=['aleatoria','espacial20','espacial30','espacial30_buffer3']
    mode=os.environ.get('YUKON_MODE','aggregate')
    selected_protocol=os.environ.get('YUKON_PROTOCOL','aleatoria')
    selected_rep=int(os.environ.get('YUKON_REPLICA','0'))
    if mode=='run':
        protocols=[selected_protocol]
        replicates=[x for x in replicates if x[0]==selected_rep]
    else:
        protocols=[]
        replicates=[]
    for protocolo in protocols:
        for rep,seed,shift in replicates:
            if protocolo=='aleatoria':
                fold_splits=list(StratifiedKFold(n_splits=5,shuffle=True,random_state=seed).split(X,y))
                blockgroups=np.full(len(X),-1)
            else:
                blocksize=20000 if protocolo=='espacial20' else 30000
                blockgroups=make_group(xy,blocksize,shift)
                fold_splits=list(StratifiedGroupKFold(n_splits=5,shuffle=True,random_state=seed).split(X,y,blockgroups))
            P={m:np.full(len(X),np.nan) for m in model_names}
            for j,(it,iv) in enumerate(fold_splits):
                trainidx=np.asarray(it)
                testidx=np.asarray(iv)
                nearest_before=float(np.min(cKDTree(xy[trainidx]).query(xy[testidx])[0]))
                cut=0
                if protocolo=='espacial30_buffer3':
                    distances=cKDTree(xy[testidx]).query(xy[trainidx])[0]
                    new=trainidx[distances>=3000]
                    cut=len(trainidx)-len(new)
                    trainidx=new
                mindist=float(np.min(cKDTree(xy[trainidx]).query(xy[testidx])[0]))
                assert len(set(trainidx).intersection(testidx))==0 and y[trainidx].sum()>1 and (y[trainidx]==0).sum()>1
                foldstat.append(dict(protocolo=protocolo,replica=rep,fold=j,n_train=len(trainidx),n_test=len(testidx),
                                  positive_train=int(y[trainidx].sum()),positive_test=int(y[testidx].sum()),
                                  min_distancia_antes_m=float(nearest_before), min_distancia_despues_m=mindist,
                                  train_excluidos_buffer=cut, num_bloques=len(np.unique(blockgroups)) if protocolo!='aleatoria' else 0))
                for m in model_names:
                    prob=fit_predict(m,X[trainidx],y[trainidx],X[testidx],SEED+int(seed)*1000+j*50+model_names.index(m))
                    P[m][testidx]=prob
            assert all(np.isfinite(p).all() for p in P.values())
            for m,p in P.items():
                row=dict(protocolo=protocolo,modelo=m,replica=rep,**metrics(y,p))
                results.append(row)
                for idx,(yt,yp) in enumerate(zip(y,p)):
                    preds.append(dict(id_unico=idx,protocolo=protocolo,modelo=m,replica=rep,verdad=int(yt),puntaje=float(yp),
                                      ESTE=xy[idx,0],NORTE=xy[idx,1]))
            print('TERMINADO',protocolo,'replica',rep,'AUC',[(m,round(metrics(y,P[m])['AUC'],3)) for m in model_names], 'elapsed',round(time.time()-t0,1),flush=True)
    if mode=='run':
        stem=f'{selected_protocol}_{selected_rep}'
        pd.DataFrame(results).to_csv(PARTS/f'_PARTIAL_METRICS_{stem}.csv',index=False)
        pd.DataFrame(preds).to_csv(PARTS/f'_PARTIAL_PREDS_{stem}.csv',index=False)
        pd.DataFrame(foldstat).to_csv(PARTS/f'_PARTIAL_FOLDS_{stem}.csv',index=False)
        print('EXIT_PARTIAL',stem,flush=True)
        raise SystemExit(0)
    all_metric_files=sorted(PARTS.glob('_PARTIAL_METRICS_*.csv'))
    all_pred_files=sorted(PARTS.glob('_PARTIAL_PREDS_*.csv'))
    all_fold_files=sorted(PARTS.glob('_PARTIAL_FOLDS_*.csv'))
    assert len(all_metric_files)==8 and len(all_pred_files)==8 and len(all_fold_files)==8, (len(all_metric_files),len(all_pred_files),len(all_fold_files))
    results=pd.concat([pd.read_csv(q) for q in all_metric_files],ignore_index=True)
    preds=pd.concat([pd.read_csv(q) for q in all_pred_files],ignore_index=True)
    foldstat=pd.concat([pd.read_csv(q) for q in all_fold_files],ignore_index=True)
    protocols=['aleatoria','espacial20','espacial30','espacial30_buffer3']
    met=pd.DataFrame(results);met.to_csv(OUT/'METRICAS_OOF_POR_REPLICA.csv',index=False)
    pp=pd.DataFrame(preds);pp.to_csv(OUT/'PREDICCIONES_FUERA_DE_MUESTRA_TODAS.csv',index=False)
    fds=pd.DataFrame(foldstat);fds.to_csv(OUT/'AUDITORIA_PARTICIONES_Y_DISTANCIAS.csv',index=False)
    summary=met.groupby(['protocolo','modelo'],sort=False).agg(n_replicas=('AUC','size'),
      AUC_medio=('AUC','mean'),AUC_sd=('AUC','std'),AP_medio=('AP','mean'),F1_medio=('F1','mean'),
      sensibilidad_media=('recall','mean'),precision_media=('precision','mean'),balanced_accuracy_medio=('balanced_accuracy','mean'),
      Brier_medio=('Brier','mean'),LogLoss_medio=('log_loss','mean'),ECE10_medio=('ECE10','mean')).reset_index()
    summary.to_csv(OUT/'RESULTADOS_COMPARACION_CONSOLIDADA.csv',index=False)
    primary=[]
    for prot in protocols:
        for m in model_names:
            d=pp[(pp.protocolo==prot)&(pp.modelo==m)&(pp.replica==0)].sort_values('id_unico')
            primary.append(dict(protocolo=prot,modelo=m,etiquetas=d.verdad.to_numpy(),probabilidades=d.puntaje.to_numpy()))
    prim=pd.DataFrame(primary)
    boots=grouped_boot(prim,y,make_group(xy,30000,0),B=1800)
    boots.to_csv(OUT/'IC95_BOOTSTRAP_BLOQUES_CONTRASTES.csv',index=False)
    # External test with the original saved complete model: diagnostic, not a legitimate spatial external CV.
    saved=saved_fde_predict(external[PCC].values)
    er=[]
    for desc,mask in [('Completo 40',np.ones(len(external),bool)),('Coincidencia 24',matches.to_numpy()),('Sin coincidencia 16',~matches.to_numpy())]:
        yy=external.loc[mask,'DEP'].to_numpy();p=saved[mask]
        er.append(dict(subconjunto=desc,positivos=int(yy.sum()),negativos=int((yy==0).sum()),modelo='FDE-FT guardado 2024',**metrics(yy,p)))
    pd.DataFrame(er).to_csv(OUT/'DIAGNOSTICO_MODELO_PUBLICADO_MUESTRA_EXTERNA.csv',index=False)
    # Ranking: evidence of robust model, not assert universal superiority or geological discovery.
    save_figures(pp,met,prim,make_group(xy,30000),usable)
    (OUT/'METODO_Y_LIMITACIONES.json').write_text(json.dumps({
      'data':'Original PC1..PC7 and coordinates of source repo, not interpolated rasters',
      'data_dedup':'289 unique PC signatures, coordinates 0/0 removed (not inventing locations)',
      'unlabelled_pretrain':'Keras original AE encoder pretrained on full region covariates; possible transductive covariate use',
      'FDE_FT_implementation':'PyTorch, 5 ReLU encoder layers (weights imported), output initialized each fold; weighted BCE 1500 epochs',
      'FDE_FT_learning_rates':'encoder 5e-5, new sigmoid head 1e-3, weight_decay 1e-5, Adam',
      'FDE_not_exact':'Adapted training schedule, not exact replication of 6000-epoch original TensorFlow code',
      'RF':'400 trees, max_features=sqrt, min_samples_leaf=2, balanced_subsample, fixed across folds',
      'LR':'fold-only StandardScaler + LogisticRegression C1 balanced',
      'outer_split':'StratifiedKFold or StratifiedGroupKFold, 5 folds, two replications; 20/30 km grid with origin-shift sensitivity; 3 km train-exclusion buffer on 30 km experiment',
      'calibration':'Out-of-fold Brier, ECE10 (small-sample descriptive), reliability bins; no posthoc calibration fitted to heldout',
      'bootstrap':'1800 paired 30 km cluster resamples conditional on OOF predicted scores. Not inferential independent CV replicates; exploratory',
      'external_limitation':'40 records no coordinates, 24 rows overlap with training signature, nonoverlap contains only 2 negatives',
      'raster_reconstruction_limitation':'original 02_PCA.tif unavailable; 94.12% grid estimated; only sensitivity context',
      'evaluation_note':'Metrics are of occurrence labels at sampled points; predicted scores are not calibrated prevalence or deposit probabilities'
      },indent=2,ensure_ascii=False),encoding='utf-8')
    print('\nAUDIT',json.dumps(audit,ensure_ascii=False));print('\nSUMMARY\n',summary.to_string(index=False));print('\nCI\n',boots.to_string(index=False));print('TOTAL seconds',time.time()-t0)
