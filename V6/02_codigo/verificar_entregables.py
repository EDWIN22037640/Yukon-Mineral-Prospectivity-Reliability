"""Static verification: zip/readability, numbers, prediction dimensions and consistency."""
from pathlib import Path
import json
import hashlib
import pandas as pd
import numpy as np
from zipfile import ZipFile
import rasterio
root=Path(__file__).resolve().parents[1]
res=root/'03_resultados'
a=json.loads((res/'AUDITORIA_INVENTARIO.json').read_text(encoding='utf-8'))
b=json.loads((res/'AUDITORIA_EFECTO_RASTER_V5.json').read_text(encoding='utf-8'))
met=pd.read_csv(res/'RESULTADOS_COMPARACION_CONSOLIDADA.csv')
raw=pd.read_csv(res/'PREDICCIONES_FUERA_DE_MUESTRA_TODAS.csv')
inter=pd.read_csv(res/'RESULTADOS_CALIBRACION_ESPACIAL_ANIDADA.csv')
fds=pd.read_csv(res/'AUDITORIA_PARTICIONES_Y_DISTANCIAS.csv')
ci=pd.read_csv(res/'IC95_BOOTSTRAP_BLOQUES_CONTRASTES.csv')
assert a['original_train']==313 and a['valid_coordinate_unique_signatures']==289 and a['external_matching_rows']==24
assert a['external_independent_class_count']=={'1':14,'0':2}
assert len(raw)==289*4*3*2 and raw[['id_unico','protocolo','modelo','replica']].duplicated().sum()==0
assert not raw.puntaje.isna().any()
assert len(met)==12 and (met.n_replicas==2).all()
assert len(inter)==6 and len(fds)==40
assert fds.n_train.min()>0 and fds.positive_test.min()>=4
assert fds[fds.protocolo=='espacial30_buffer3'].min_distancia_despues_m.min()>=3000
assert b['celdas_totales']==12980 and b['celdas_originales_sin_alteracion']==763
assert b['celdas_cambian_categoria_umbral_0_70']==547
for filepath in root.glob('07_rasters_sensibilidad_V5/*.tif'):
    with rasterio.open(filepath) as tif:
        assert str(tif.crs)=='EPSG:3579' and tif.width==118 and tif.height==110
for f in root.glob('05_informe/*.docx'):
    with ZipFile(f) as z:assert z.testzip() is None and 'word/document.xml' in z.namelist()
for f in root.glob('05_informe/*.pdf'):
    assert f.stat().st_size>100_000 and f.read_bytes()[:4]==b'%PDF'
for key,p in [ ('aleatoria',.8622), ('espacial30',.7823) ]:
    x=float(met[(met.modelo=='RF') & (met.protocolo==key)].AUC_medio.iloc[0]);assert abs(x-p)<.001
report={'estado':'Verificación aprobada','firma_fuentes':'CSV originales, pesos H5 originales',
        'filas_CV_unicas':289,'predicciones_OOF':int(len(raw)),'protocolos':4,'repeticiones':2,
        'folds_total':int(len(fds)),'resultados_metricas':int(len(met)),
        'pruebas_calibracion':int(len(inter)),'raster_celdas':int(b['celdas_totales']),
        'raster_celdas_originales':int(b['celdas_originales_sin_alteracion']),
        'n_articulos_o_informes_word':len(list(root.glob('05_informe/*.docx'))),
        'n_articulos_o_informes_pdf':len(list(root.glob('05_informe/*.pdf'))),
        'bootstrap_comparaciones':ci[ci.tipo=='Diferencia AUC'].contraste.tolist()}
(res/'VERIFICACION_FINAL_DEL_PROYECTO.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
