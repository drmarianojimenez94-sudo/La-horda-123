import json
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(__file__).parent
data=json.loads((root/'report.json').read_text())
assert len(data['holdout'])==3 and len(data['training'])==3
styles=getSampleStyleSheet()
out=root/'comparativo_90_dias.pdf'
doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=1.7*cm,leftMargin=1.7*cm)
story=[Paragraph('Agente cripto | Backtest historico',styles['Title']),Spacer(1,12),
Paragraph('Datos: Binance Spot USDT, velas de 1 hora. Capital inicial: 200 USDT por estrategia. Tres perfiles: conservadora, agresiva y adaptativa.',styles['BodyText']),Spacer(1,12),
Paragraph('IMPORTANTE: el motor actual utiliza aproximadamente 60 dias de entrenamiento y 30 dias de evaluacion fuera de muestra. NO representa 90 dias de operacion fuera de muestra.',styles['BodyText']),Spacer(1,12)]
for key,title in [('training','Entrenamiento (aprox. 60 dias)'),('holdout','Evaluacion fuera de muestra (aprox. 30 dias)')]:
 story.append(Paragraph(title,styles['Heading2']))
 rows=[['Estrategia','Inicial','Final','Retorno','Trades','Caida max.']]
 for v in data[key]:
  rows.append([v['strategy'],str(v['initial_usdt']),str(v['final_usdt']),str(v['return_pct'])+'%',str(v['trades']),str(v['max_drawdown_pct'])+'%'])
 table=Table(rows,colWidths=[3.1*cm,2.1*cm,2.1*cm,2.5*cm,2*cm,2.8*cm],repeatRows=1)
 table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#18324f')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.35,colors.lightgrey),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f5f9')]),('FONTSIZE',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9)]))
 story.extend([table,Spacer(1,14)])
 fig,ax=plt.subplots(figsize=(7,2.8))
 vals=data[key];bars=ax.bar([x['strategy'] for x in vals],[x['return_pct'] for x in vals])
 ax.axhline(0,color='black',lw=.7);ax.set_ylabel('Retorno neto (%)');ax.set_title(title)
 fig.tight_layout();img=root/(key+'.png');fig.savefig(img,dpi=150);plt.close(fig)
 story.extend([Image(str(img),width=15*cm,height=6*cm),Spacer(1,12)])
story.append(Paragraph('Metodologia y limitaciones',styles['Heading2']))
story.append(Paragraph('El universo se selecciona por volumen actual de 24 horas, lo que introduce sesgo retrospectivo. Las operaciones usan aproximaciones de comisiones, spread y deslizamiento; no incluyen libro de ordenes ni ejecuciones parciales. Las reglas se basan en desviacion estadistica de cierres horarios, con salidas por objetivo, stop o tiempo. Los resultados historicos no garantizan rendimiento futuro.',styles['BodyText']))
story.append(Spacer(1,10))
story.append(Paragraph('Pares analizados: '+', '.join(data['pairs']),styles['BodyText']))
doc.build(story)
assert out.exists() and out.stat().st_size>5000
print('PDF creado:',out,'bytes:',out.stat().st_size)
