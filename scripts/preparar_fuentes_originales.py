#!/usr/bin/env python3
"""Preparar entradas de terceros desde ZIP oficial descargado por la persona que reproduce.
No sube, distribuye ni descarga datos; solamente copia localmente archivos ya obtenidos.
Ejemplo: python scripts/preparar_fuentes_originales.py /ruta/TransferProspectivityLearning-main.zip
"""
import argparse, zipfile, hashlib, pathlib

PARSER=argparse.ArgumentParser()
PARSER.add_argument('zip_original', type=pathlib.Path, help='ZIP del repositorio de Mantilla-Dulcey')
PARSER.add_argument('--destino', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
PARSER.add_argument('--sobrescribir', action='store_true')
args=PARSER.parse_args()
MAP={
 'V5':{
   '013_Random.csv':'Data/013_Random.csv',
   '01_Train_VO.csv':'Data/01_Train_VO.csv',
   '02_Train_PCA.csv':'Data/02_Train_PCA.csv',
   '03_Train_Pretext.csv':'Data/03_Train_Pretext.csv',
   '04_Validation_Points.csv':'Data/04_Validation_Points.csv',
   'autoencoder_fine.h5':'Models/EXPERIMENT_I/autoencoder_fine.h5',
 },
 'V6':{
   '01_Train_VO.csv':'Data/01_Train_VO.csv',
   '02_Train_PCA.csv':'Data/02_Train_PCA.csv',
   '04_Validation_Points.csv':'Data/04_Validation_Points.csv',
   'FDE_FT_original_completo.h5':'Models/EXPERIMENT_I/autoencoder_fine.h5',
   'modelo_encoder_original.h5':'Models/PRETRAINED_MODELS/modelo_encoder.h5',
 }
}
with zipfile.ZipFile(args.zip_original) as z:
    for version, files in MAP.items():
        for dstname, tail in files.items():
            hits=[n for n in z.namelist() if n.endswith('/'+tail)]
            if len(hits)!=1:raise RuntimeError(f'Falta o no es único: {tail}; encontrados={hits}')
            target=args.destino/version/'01_fuentes'/dstname
            target.parent.mkdir(parents=True,exist_ok=True)
            data=z.read(hits[0]);sha=hashlib.sha256(data).hexdigest()
            if target.exists() and not args.sobrescribir:
                if hashlib.sha256(target.read_bytes()).hexdigest()!=sha:
                    raise FileExistsError(f'Archivo existente con diferente hash: {target}')
                print('Ya instalado:',target)
                continue
            target.write_bytes(data)
            print(f'{version}: {dstname} ({len(data)} bytes, SHA256 {sha})')
print('Entradas instaladas LOCALMENTE. Están excluidas del seguimiento Git por .gitignore.')
