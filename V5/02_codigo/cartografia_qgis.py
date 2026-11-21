from pathlib import Path
import rasterio, geopandas as gpd
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parents[1];GIS=R/'03_GeoTIFF_QGIS';FIG=R/'05_figuras';SRC=R/'01_fuentes'
left,top,pix,w,h=159050.,977585.,1200.,118,110
extent=[left/1000,(left+pix*w)/1000,(top-pix*h)/1000,top/1000]
coords=lambda df:np.stack((df['ESTE']/1000,df['NORTE']/1000),axis=1)
raw=pd.read_csv(SRC/'01_Train_VO.csv');raw=raw[(raw.ESTE>0)&(raw.NORTE>0)]
actual=raw[raw.DEP==1];neg=raw[raw.DEP==0]
GDF=gpd.GeoDataFrame(raw.copy(),geometry=gpd.points_from_xy(raw.ESTE,raw.NORTE),crs='EPSG:3579')
with rasterio.open(GIS/'PCA7_V5_ESPACIAL_RECOMENDADO_7B.tif') as src:
 arr=src.read().reshape(7,-1).T;msk=np.zeros(len(arr),bool)
with rasterio.open(GIS/'V5_PROCEDENCIA_1_OBSERVADO_2_3KM_3_6KM_4_10KM_5_LEJOS.tif') as d:
 msk=d.read(1).reshape(-1)==1
row,col=np.indices((h,w));x=left+(col.ravel()+.5)*pix;y=top-(row.ravel()+.5)*pix
obs=pd.DataFrame(arr[msk],columns=[f'PC{j}' for j in range(1,8)]);obs['E_CELDA']=x[msk];obs['N_CELDA']=y[msk];obs['ID_CELDA']=np.flatnonzero(msk)
GOBS=gpd.GeoDataFrame(obs,geometry=gpd.points_from_xy(obs.E_CELDA,obs.N_CELDA),crs='EPSG:3579')
out=GIS/'V5_PUNTOS_GEOLOGICOS_REALES.gpkg'
if out.exists():out.unlink()
GOBS.to_file(out,layer='PCA_763_CELDAS',driver='GPKG')
GDF.to_file(out,layer='ENTRENAMIENTO_312',driver='GPKG')

paths=[GIS/'V5_FDE_PUNTAJE_ESPACIAL_SIN_RUIDO.tif',GIS/'V5_FDE_PUNTAJE_COPULA_SIN_RUIDO.tif',GIS/'V5_ESPACIAL_FDE_MEDIANA.tif',GIS/'V5_ESPACIAL_FRACCION_PUNTAJE_MAYOR_070.tif']
arrs=[]
for p in paths:
 with rasterio.open(p) as r:arrs.append(r.read(1))

def add_scale(ax):
 x0=extent[0]+5;y0=extent[2]+9
 ax.plot([x0,x0+20],[y0,y0],color='black',lw=2.5,solid_capstyle='butt');
 for ii in (0,10,20):ax.plot([x0+ii,x0+ii],[y0-1,y0+1],color='black',lw=1)
 ax.text(x0+10,y0+2.0,'20 km',ha='center',fontsize=8,color='black')

def add_north(ax):
 x0=extent[1]-9; y0=extent[3]-8
 ax.annotate('',xy=(x0,y0+5),xytext=(x0,y0),arrowprops=dict(arrowstyle='-|>',color='black',lw=1.7))
 ax.text(x0,y0+6,'N',fontsize=10,weight='bold',ha='center')

fig,axs=plt.subplots(2,2,figsize=(14,13.2),dpi=160)
fig.subplots_adjust(left=.07,right=.95,bottom=.17,top=.89,wspace=.18,hspace=.27)
labels=['A. FDE-FT · entrada V4 espacial','B. FDE-FT · perfil PCA V5 corregido','C. Mediana de 40 realizaciones espaciales','D. Frecuencia de puntajes FDE ≥ 0,70']
for ax,data,title in zip(axs.ravel(),arrs,labels):
 im=ax.imshow(data,extent=extent,cmap='RdYlGn_r',vmin=0,vmax=1,origin='upper',interpolation='nearest',aspect='equal')
 ax.scatter(neg.ESTE/1000,neg.NORTE/1000,s=8,facecolor='white',edgecolor='black',linewidths=.45,alpha=.80,zorder=5)
 ax.scatter(actual.ESTE/1000,actual.NORTE/1000,s=11,facecolor='black',edgecolor='white',linewidths=.42,zorder=5)
 ax.set_title(title,fontsize=11,weight='bold');ax.set_xlabel('Este (km) · EPSG:3579');ax.set_ylabel('Norte (km) · EPSG:3579');ax.tick_params(labelsize=8)
 add_scale(ax);add_north(ax)
cax=fig.add_axes([.28,.112,.44,.018])
cb=fig.colorbar(im,cax=cax,orientation='horizontal')
cb.set_label('A-C: puntaje FDE-FT (0–1) | D: fracción de simulaciones (0–1)',fontsize=9)
fig.legend(handles=[Line2D([0],[0],marker='o',color='none',markerfacecolor='black',markeredgecolor='white',markersize=7,label='Entrenamiento con ocurrencia'),Line2D([0],[0],marker='o',color='none',markerfacecolor='white',markeredgecolor='black',markersize=7,label='Entrenamiento sin ocurrencia')],loc='lower center',ncol=2,bbox_to_anchor=(.5,.057),fontsize=9,frameon=False)
fig.suptitle('YUKÓN | MAPAS COMPARATIVOS DE PROSPECTIVIDAD · V5',fontsize=17,weight='bold',y=.98)
fig.text(.5,.944,'Resultados exploratorios derivados de PCA reconstruido; no son reproducciones del mapa original ni recursos minerales',ha='center',fontsize=9)
fig.text(.5,.020,'No se dibujan fallas geológicas: no consta una capa oficial descargada y verificada en esta entrega.',ha='center',fontsize=9)
fig.savefig(FIG/'06_CARTOGRAFIA_COMO_ARTICULO_PROSPECTIVIDAD.png',dpi=210,bbox_inches='tight');fig.savefig(FIG/'06_CARTOGRAFIA_COMO_ARTICULO_PROSPECTIVIDAD.pdf',bbox_inches='tight');plt.close(fig)
print('MAPA listo + GPKG',out)
