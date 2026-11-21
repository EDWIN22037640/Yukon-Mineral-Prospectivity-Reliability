#!/usr/bin/env python3
"""Diagnóstico reproducible de autocorrelación espacial de PC1–PC7, Yukón.

Fuente: YUKON_CIERRE_CIENTIFICO_V6.zip; 289 firmas PCA depuradas como analisis_final.py.
Semivariograma clásico isotrópico por intervalos de distancia y modelo exponencial.
Las cifras son diagnósticas; los puntos no son una muestra aleatoria uniforme del territorio.
"""
from pathlib import Path
import argparse
import io, zipfile
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Semivariogramas PCA para las 289 firmas depuradas de Yukón')
parser.add_argument('--source', type=Path, default=Path('YUKON_CIERRE_CIENTIFICO_V6.zip'), help='Archivo ZIP original del V6')
parser.add_argument('--output', type=Path, default=Path('resultados_variogramas'), help='Carpeta de salida')
args = parser.parse_args()
SOURCE = args.source
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)
PC = [f'PC{i}' for i in range(1,8)]
ROOT = 'YUKON_CIERRE_CIENTIFICO_V6/01_fuentes/'

with zipfile.ZipFile(SOURCE) as z:
    pca = pd.read_csv(io.BytesIO(z.read(ROOT+'02_Train_PCA.csv')))
    vo = pd.read_csv(io.BytesIO(z.read(ROOT+'01_Train_VO.csv')))
assert len(pca)==len(vo)==313 and (pca['DEP'].values==vo['DEP'].values).all()
merged = pd.concat([pca, vo[['ESTE','NORTE']]], axis=1)
valid = (merged['ESTE']>0)&(merged['NORTE']>0)
ana = merged.loc[valid].drop_duplicates(subset=PC, keep='first').reset_index(drop=True)
assert len(ana)==289 and int((ana.DEP==1).sum())==71 and int((ana.DEP==0).sum())==218

# Las columnas ESTE y NORTE estan en metros EPSG:3579.
dkm = pdist(ana[['ESTE','NORTE']].to_numpy(dtype=float))/1000
X = ana[PC].to_numpy(dtype=float)

# La matriz de índices para binning se recalcula segun una distancia máxima y ancho.
def binned_variogram(values, width=5, max_lag=100):
    lims=np.arange(0,max_lag+width,width,dtype=float)
    binid=np.digitize(dkm,lims,right=False)-1
    semivar=0.5*pdist(values[:,None], metric='sqeuclidean')
    rows=[]
    for b in range(len(lims)-1):
        pair=(binid==b)
        n=int(pair.sum())
        rows.append({'lag_desde_km':lims[b], 'lag_hasta_km':lims[b+1],
                     'h_medio_km':float(dkm[pair].mean()) if n else np.nan,
                     'n_pares':n, 'semivarianza':float(semivar[pair].mean()) if n else np.nan})
    return pd.DataFrame(rows)

# Exponencial con parametrización por alcance práctico r = nivel 95% de la meseta.
# Gamma(h) = nugget + partial_sill * (1 - exp(-[-ln(0.05)]*h/r)), h>0.
FACTOR=-np.log(.05)
def exp_semivariogram(h,nugget,partial,r):
    return nugget+partial*(1-np.exp(-FACTOR*np.asarray(h)/r))

def spherical_semivariogram(h,nu,ps,r):
    x=np.asarray(h)/r
    return nu + ps*np.where(x<1, 1.5*x-0.5*x**3, 1.)

def fitting(bins, values, model='exponential', weighted=True, max_lag=100):
    good=(bins['n_pares']>=30) & np.isfinite(bins['semivarianza'])
    bb=bins.loc[good]
    h=bb['h_medio_km'].to_numpy(dtype=float)
    gamma=bb['semivarianza'].to_numpy(dtype=float)
    n=bb['n_pares'].to_numpy(dtype=float)
    sample_var=float(np.var(values,ddof=1))
    w=np.sqrt(n/n.max()) if weighted else np.ones(len(n))
    f=exp_semivariogram if model=='exponential' else spherical_semivariogram
    def fun(t):
        return w*(f(h,*t)-gamma)/sample_var
    upper=[2*sample_var, 4*sample_var, 4*max_lag]
    best=None
    for starting in [[0, sample_var, 20],[.1*sample_var, .9*sample_var, 35],[.3*sample_var,.7*sample_var,60],[.5*sample_var,.5*sample_var,100]]:
        fit=least_squares(fun,starting,bounds=([0,0,1], upper), max_nfev=5000,xtol=1e-12,ftol=1e-12,gtol=1e-12)
        sse=float(np.sum(fun(fit.x)**2))
        if best is None or sse < best['sse']:
            best={'nugget':fit.x[0], 'partial_sill':fit.x[1], 'alcance_km':fit.x[2], 'sse':sse,
                  'success':bool(fit.success), 'message':fit.message}
    yhat=f(h,best['nugget'],best['partial_sill'],best['alcance_km'])
    ybar=np.average(gamma,weights=w**2)
    ss0=float(np.sum((w*(gamma-ybar))**2));ss1=float(np.sum((w*(gamma-yhat))**2))
    best['r2_semivariograma']=1-ss1/ss0 if ss0>0 else np.nan
    best['meseta']=best['nugget']+best['partial_sill']
    best['varianza_muestral']=sample_var
    best['n_intervalos']=len(bb)
    best['n_pares_en_intervalos']=int(n.sum())
    return best

rows=[]; sens=[]; empirical=[]
for k,col in enumerate(PC):
    v=X[:,k]
    b=binned_variogram(v,5,100)
    b.insert(0,'componente',col)
    empirical.append(b)
    fit=fitting(b,v)
    rows.append({'componente':col, 'alcance_efectivo_km':fit['alcance_km'],
                 'efecto_pepita':fit['nugget'], 'meseta_total':fit['meseta'],
                 'varianza_muestral':fit['varianza_muestral'],
                 'r2_descriptivo_ajuste':fit['r2_semivariograma'],
                 'n_pares_hasta_100km':int((dkm<100).sum()),
                 'n_intervalos_5km':fit['n_intervalos']})
    for cutoff in [60,80,100,120]:
      for width in [4,5,10]:
        bb=binned_variogram(v,width,cutoff)
        for model in ['exponential','spherical']:
            ff=fitting(bb,v,model=model,max_lag=cutoff)
            sens.append({'componente':col,'modelo':model,'corte_maximo_km':cutoff,
                         'intervalo_km':width,'alcance_km':ff['alcance_km'],
                         'r2_descriptivo':ff['r2_semivariograma'],
                         'nugget':ff['nugget'],'meseta':ff['meseta']})

primary=pd.DataFrame(rows)
sens=pd.DataFrame(sens)
emp=pd.concat(empirical,ignore_index=True)
primary['alcance_redondeado_km']=primary['alcance_efectivo_km'].round(1)
primary['relacion_bloques_20km']=np.where(primary['alcance_efectivo_km']<=20,'>= alcance (orientativo)','< alcance (orientativo)')
primary['relacion_bloques_30km']=np.where(primary['alcance_efectivo_km']<=30,'>= alcance (orientativo)','< alcance (orientativo)')

primary.to_csv(OUT/'resumen_alcances_PC1_PC7.csv',index=False,encoding='utf-8-sig')
emp.to_csv(OUT/'semivariogramas_empiricos_5km_100km.csv',index=False,encoding='utf-8-sig')
sens.to_csv(OUT/'sensibilidad_alcances_lag_y_modelo.csv',index=False,encoding='utf-8-sig')

# Panel A4 horizontal en calidad alta, usando estilo editorial neutro y coma decimal.
fig,axes=plt.subplots(4,2,figsize=(12,13),sharex=True)
for k,col in enumerate(PC):
    ax=axes.flat[k]
    b=emp[emp.componente==col]
    res=primary.loc[primary.componente==col].iloc[0]
    xx=np.linspace(0,100,300)
    fit=exp_semivariogram(xx,res.efecto_pepita,res.meseta_total-res.efecto_pepita,res.alcance_efectivo_km)
    ax.plot(b.h_medio_km,b.semivarianza,'o',ms=4.2,label='Semivariograma empírico')
    ax.plot(xx,fit,'-',lw=1.7,label='Ajuste exponencial')
    ax.axvline(20,color='gray',ls='--',alpha=.8,lw=1.1)
    ax.axvline(30,color='gray',ls=':',alpha=.9,lw=1.4)
    ax.set_title(f'{col} | alcance efectivo: {res.alcance_efectivo_km:0.1f} km'.replace('.',','),loc='left',fontsize=11)
    ax.set_ylabel('Semivarianza')
    ax.grid(alpha=.16)
    if k>=4:ax.set_xlabel('Distancia entre puntos (km)')
axes.flat[7].axis('off')
handles,labels=axes.flat[0].get_legend_handles_labels()
fig.legend(handles+ [plt.Line2D([],[],color='gray',ls='--',lw=1.1),plt.Line2D([],[],color='gray',ls=':',lw=1.4)],
           labels + ['20 km: bloque','30 km: bloque'],loc='lower right',bbox_to_anchor=(.9,.08),fontsize=9,frameon=False)
fig.suptitle('Yukón | Autocorrelación espacial de siete componentes PCA',fontsize=16,weight='bold',y=.985)
fig.text(.5,.023,'289 firmas únicas; EPSG:3579; intervalos de 5 km; distancia máxima de 100 km. Ajuste ponderado por n.º de pares.',
         ha='center',fontsize=9)
fig.tight_layout(rect=(0,.045,1,.96),h_pad=2.5)
fig.savefig(OUT/'figura_semivariogramas_PC1_PC7.png',dpi=190,bbox_inches='tight')
plt.close(fig)

# Figura en una sola altura para el cuerpo de un artículo (opcional)
fig,ax=plt.subplots(figsize=(9,4.5))
ax.bar(primary.componente,primary.alcance_efectivo_km)
ax.axhline(20,ls='--',lw=1.2,color='grey',label='20 km')
ax.axhline(30,ls=':',lw=1.5,color='black',label='30 km')
for i,v in enumerate(primary.alcance_efectivo_km):ax.text(i,v+1,f'{v:.1f}'.replace('.',','),ha='center',fontsize=9)
ax.set_ylabel('Alcance efectivo exploratorio (km)')
ax.set_title('Alcances prácticos del modelo exponencial para PC1–PC7')
ax.set_ylim(0,max(primary.alcance_efectivo_km)*1.2)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(OUT/'figura_resumen_alcances.png',dpi=220,bbox_inches='tight')
plt.close(fig)

print('\nRESUMEN (tabla principal):\n',primary[['componente','alcance_redondeado_km','r2_descriptivo_ajuste']].to_string(index=False))
print('\nSENSIBILIDAD EXPONENCIAL, cortes 80/100/120 km, ancho 5 km:\n',sens[(sens.modelo=='exponential')&(sens.intervalo_km==5)&(sens.corte_maximo_km.isin([80,100,120]))].pivot(index='componente',columns='corte_maximo_km',values='alcance_km').round(1).to_string())
print('\nSENSIBILIDAD EXPONENCIAL, corte 100 km, ancho 4/5/10km:\n',sens[(sens.modelo=='exponential')&(sens.corte_maximo_km==100)].pivot(index='componente',columns='intervalo_km',values='alcance_km').round(1).to_string())
print('\nSENSIBILIDAD MODELO, corte 100 km, ancho 5km:\n',sens[(sens.corte_maximo_km==100)&(sens.intervalo_km==5)].pivot(index='componente',columns='modelo',values='alcance_km').round(1).to_string())
print('\nfiles')
for x in OUT.iterdir():print(x,x.stat().st_size)
