import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const dir=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(dir,'dados_levantamento.json'),'utf8'));
const wb=Workbook.create();
const fmt='#,##0.00;(#,##0.00);"-"';
const pct1='0.0%;(0.0%);"-"',pct2='0.00%;(0.00%);"-"';
const col=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const nrow=(s,label)=>6+s.rows.findIndex(r=>r[0]===label);
const names=new Map();
const qaSelection=process.env.CSG_QA_SHEETS?new Set(process.env.CSG_QA_SHEETS.split('|')):null;
for(const s of data.sheets){
  if(s.name.length>31)throw new Error(`Nome longo: ${s.name}`);
  names.set(s.name,wb.worksheets.add(s.name));
}
const formulas=[];
for(const s of data.sheets){
  const sh=names.get(s.name), nc=s.headers.length,nr=s.rows.length,last=nr+5;
  sh.showGridLines=false;
  if(['Síntese anual','Situação real','DRE','Custos e despesas','Endividamento','2_Debentures','3 Carteira','Fluxo acumulado'].includes(s.name))sh.tabColor='#263E59';
  const area=sh.getRange(`A1:${col(nc-1)}${Math.max(last,6)}`);
  area.format.font={name:'Arial',size:10,color:'#243449'};area.format.rowHeight=22;area.format.verticalAlignment='center';
  sh.getRange('A2').values=[[s.name+' | CSG']];sh.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:'#263E59'};
  sh.getRange('A3').values=[['Data-base: 30/09/2026 • R$ • PENDENTE = conclusão em aberto • ESTIMADO = premissa declarada']];
  sh.getRange('A3').format.font={name:'Arial',size:9,italic:true,color:'#657387'};
  const head=sh.getRange(`A5:${col(nc-1)}5`);head.values=[s.headers];
  head.format={fill:'#263E59',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:40,wrapText:true,verticalAlignment:'center',horizontalAlignment:'center'};
  if(nr){
    const values=s.rows.map(r=>s.headers.map((_,i)=>r[i]??null));
    sh.getRange(`A6:${col(nc-1)}${last}`).values=values;
    for(let j=0;j<nc;j++){
      const header=String(s.headers[j]),isYear=/^202[2-6]/.test(header)||/acumulado/i.test(header);
      const nums=values.filter(r=>typeof r[j]==='number').length;
      const money=/R\$|valor|saldo|débit|crédit|despesa|calculado|referência|diferença|preço|receita|face|deságio|financeiro|principal|juros|líquido|entrada|saída|movimento ECD|DRE oficial/i.test(header);
      const id=/código|classificação|cpf|cnpj|documento|contrato|conta|série|ano$|linha$|parcelas|quantidade|tamanho|bytes|lançamento|nº|número|prazo|dias/i.test(header);
      const numeric=nums>0;
      sh.getRange(`${col(j)}5:${col(j)}${last}`).format.columnWidth=isYear?19:(id?20:(numeric?22:42));
      if(j===0)sh.getRange(`A5:A${last}`).format.columnWidth=/ano|data|código|mês|arquivo/i.test(header)?23:55;
      if(/fonte|premissa|pendência|ressalva|tratamento|método|observ|histórico|contrapartida|detalhe|duplicidade/i.test(header))sh.getRange(`${col(j)}5:${col(j)}${last}`).format.columnWidth=/fonte/i.test(header)?75:65;
      if(/SHA/i.test(header))sh.getRange(`${col(j)}5:${col(j)}${last}`).format.columnWidth=84;
      if(/devedor|credor\/|titular/i.test(header))sh.getRange(`${col(j)}5:${col(j)}${last}`).format.columnWidth=55;
      if(/^posição$|^série$/i.test(header)){sh.getRange(`${col(j)}5:${col(j)}${last}`).format.columnWidth=12;sh.getRange(`${col(j)}6:${col(j)}${last}`).format.horizontalAlignment='center';}
      if(/mês\/aba/i.test(header))sh.getRange(`${col(j)}6:${col(j)}${last}`).setNumberFormat('@');
      if(numeric){sh.getRange(`${col(j)}6:${col(j)}${last}`).setNumberFormat(/%/.test(header)?pct2:(/^ano$/i.test(header)?'0':((isYear||money)&&(!id||/R\$/.test(header))?fmt:'#,##0')));sh.getRange(`${col(j)}6:${col(j)}${last}`).format.horizontalAlignment='right';}
      // Datas suportadas pela fonte ficam como datas reais, IDs permanecem texto.
      if(/data|vencimento|aquisição|primeiro lançamento|último lançamento|1ª|última/i.test(header)){
        for(let i=0;i<values.length;i++)if(/^\d{4}-\d{2}-\d{2}$/.test(String(values[i][j]??''))){
          const cell=sh.getRange(`${col(j)}${i+6}`);cell.values=[[new Date(values[i][j]+'T12:00:00Z')]];cell.setNumberFormat('dd/mm/yyyy');
        }
      }
    }
    const percentColumns=s.percent_columns||[];
    for(const j of percentColumns)sh.getRange(`${col(j)}6:${col(j)}${last}`).setNumberFormat(pct2);
    if(nr>15){sh.freezePanes.freezeRows(5);if(nc>7)sh.freezePanes.freezeColumns(1);}
    // Filtros nativos nas bases detalhadas, sem alterar a ordem das fontes.
    if(nr>40){const tab=sh.tables.add(`A5:${col(nc-1)}${last}`,true,'CSG_'+String(data.sheets.indexOf(s)+1));tab.showFilterButton=true;}
    for(let i=0;i<values.length;i++){
      const row=i+6,label=String(values[i][0]??''), ratio=/margem|\/ total|\/ receita|% sobre/i.test(label);
      const annual=s.headers.slice(1,6).every((h,j)=>String(h).startsWith(String(2022+j)));
      if(annual){
        if(ratio){sh.getRange(`B${row}:G${row}`).setNumberFormat(pct1);sh.getRange(`A${row}:G${row}`).format.font.italic=true;}
        if(s.name==='Indicadores'&&!/R\$|custo médio|recuperável/i.test(label))sh.getRange(`B${row}:G${row}`).setNumberFormat('0.00"x"');
        if(/\(quantidade\)/i.test(label))sh.getRange(`B${row}:G${row}`).setNumberFormat('#,##0');
        if(s.name==='Síntese anual'){
          const add=/Resultado do período|Custo histórico|Receita bruta acumulada|Receitas totais/.test(label);
          formulas.push([sh,`G${row}`,add?`=SUM(B${row}:F${row})`:`=F${row}`]);
        }else if(['Custos e despesas','DRE','DRE gerencial'].includes(s.name)&&!ratio&&values[i].slice(1,6).every(x=>typeof x==='number')){
          formulas.push([sh,`G${row}`,`=SUM(B${row}:F${row})`]);
        }
      }
      if(/TOTAL|^Lucro \/|^Saldo final|^Variação líquida|^PL incluindo|^Passivo exigível|^Resultado (bruto|operacional|antes)|^Custo histórico|^Receitas totais/i.test(label)){
        sh.getRange(`A${row}:${col(Math.min(nc-1,6))}${row}`).format.fill='#E8EEF3';sh.getRange(`A${row}:${col(Math.min(nc-1,6))}${row}`).format.font.bold=true;
      }
    }
    // Campos textuais longos ficam integralmente legíveis com quebra e altura calculada.
    // Somente colunas de texto são quebradas, nunca números e identificadores.
    for(let i=0;i<values.length;i++){
      let lines=1;
      for(let j=0;j<nc;j++){
        if(typeof values[i][j]!=='string'||values[i][j].length<32)continue;
        const header=String(s.headers[j]);const capacity=/SHA/i.test(header)?90:(/fonte/i.test(header)?75:(j===0?55:(/devedor|titular/i.test(header)?55:42)));
        const cell=sh.getRange(`${col(j)}${i+6}`);cell.format.wrapText=true;cell.format.verticalAlignment='top';
        lines=Math.max(lines,Math.ceil(values[i][j].length/capacity));
      }
      if(lines>1)sh.getRange(`A${i+6}:${col(nc-1)}${i+6}`).format.rowHeight=Math.min(320,lines*13+8);
    }
    const text=sh.getRange(`A6:${col(nc-1)}${last}`);
    text.conditionalFormats.add('containsText',{text:'PENDENTE',format:{fill:'#FFF2D8',font:{color:'#88591C'}}});
    text.conditionalFormats.add('containsText',{text:'DIVERGÊNCIA',format:{fill:'#FCE5E5',font:{bold:true,color:'#A02020'}}});
  }
}
// Fórmulas simples mantêm as somas e os indicadores auditáveis e atualizáveis.
const costs=data.sheets.find(s=>s.name==='Custos e despesas');
const costsh=names.get(costs.name),costTotal=nrow(costs,'TOTAL CUSTOS/DESPESAS + DEDUÇÕES');
for(let j=1;j<=6;j++){
  formulas.push([costsh,`${col(j)}${costTotal}`,`=SUM(${col(j)}6:${col(j)}${costTotal-1})`]);
  for(let i=0;i<costs.rows.length;i++)if(String(costs.rows[i][0]).includes('/ total'))formulas.push([costsh,`${col(j)}${i+6}`,`=${col(j)}${i+5}/${col(j)}${costTotal}`]);
}
const dre=data.sheets.find(s=>s.name==='DRE'),dresh=names.get('DRE');
const cash=data.sheets.find(s=>s.name==='Fluxo acumulado');
if(cash){
  const sh=names.get(cash.name),rOpen=nrow(cash,'Saldo inicial do disponível R$'),rIn=nrow(cash,'Débitos no disponível: movimentos contábeis R$'),rOut=nrow(cash,'Créditos no disponível: movimentos contábeis R$'),rNet=nrow(cash,'Variação líquida do disponível R$'),rClose=nrow(cash,'Saldo final do disponível R$');
  formulas.push([sh,`G${rOpen}`,`=B${rOpen}`],[sh,`G${rIn}`,`=SUM(B${rIn}:F${rIn})`],[sh,`G${rOut}`,`=SUM(B${rOut}:F${rOut})`]);
  for(let j=1;j<=6;j++){
    const c=col(j);
    formulas.push([sh,`${c}${rNet}`,`=${c}${rIn}-${c}${rOut}`],[sh,`${c}${rClose}`,`=${c}${rOpen}+${c}${rNet}`]);
  }
}
for(let j=1;j<=6;j++){
  const c=col(j),r=label=>nrow(dre,label),f=(label,formula)=>formulas.push([dresh,`${c}${r(label)}`,formula]);
  f('Receita líquida',`=SUM(${c}${r('Receita bruta')}:${c}${r('(-) Deduções da receita')})`);
  f('Resultado bruto',`=SUM(${c}${r('Receita líquida')}:${c}${r('(-) Custo da operação (grupo 3.1)')})`);
  f('Resultado operacional antes do financeiro',`=SUM(${c}${r('Resultado bruto')}:${c}${r('(-) Indedutíveis')})`);
  f('Resultado antes de IR/CSLL',`=SUM(${c}${r('Resultado operacional antes do financeiro')}:${c}${r('(-) Demais despesas financeiras')})`);
  f('Lucro / (prejuízo) líquido',`=SUM(${c}${r('Resultado antes de IR/CSLL')}:${c}${r('(-) IR/CSLL')})`);
  f('Margem bruta sobre receita líquida',`=${c}${r('Resultado bruto')}/${c}${r('Receita líquida')}`);
  f('Margem líquida sobre receita bruta',`=${c}${r('Lucro / (prejuízo) líquido')}/${c}${r('Receita bruta')}`);
  f('Juros debêntures / receita bruta',`=-${c}${r('(-) Juros de debêntures')}/${c}${r('Receita bruta')}`);
}
for(const [sh,cell,f]of formulas)sh.getRange(cell).formulas=[[f]];
wb.recalculate();
await fs.mkdir(path.join(dir,'qa'),{recursive:true});
const checks=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:50},summary:'Verificação final de fórmulas'});
await fs.writeFile(path.join(dir,'qa','formula_check.ndjson'),checks.ndjson);
const inspect=await wb.inspect({kind:'table',range:"'DRE'!A5:H33",include:'values,formulas',tableMaxRows:29,tableMaxCols:8,maxChars:12000});
await fs.writeFile(path.join(dir,'qa','DRE_check.ndjson'),inspect.ndjson);
for(const s of data.sheets){
  if(qaSelection&&!qaSelection.has(s.name))continue;
  const lastCol=Math.min(s.headers.length-1,6),lastRow=Math.min(s.rows.length+5,13);
  const img=await wb.render({sheetName:s.name,range:`A1:${col(lastCol)}${lastRow}`,scale:1.25,format:'png'});
  await fs.writeFile(path.join(dir,'qa',s.name.replace(/[^a-zA-Z0-9_-]/g,'_')+'.png'),new Uint8Array(await img.arrayBuffer()));
}
for(const [sheetName,range,suffix] of [['Endividamento','H5:M17','saldos'],['DRE','A20:G32','resultado'],['Conciliação','A5:G12','fontes'],['Top20 carteira','A5:H13','completo']]){
  if(qaSelection&&!qaSelection.has(sheetName))continue;
  const img=await wb.render({sheetName,range,scale:1.25,format:'png'});
  await fs.writeFile(path.join(dir,'qa',sheetName.replace(/[^a-zA-Z0-9_-]/g,'_')+'_'+suffix+'.png'),new Uint8Array(await img.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);
await file.save(path.join(dir,'levantamento_financeiro_CSG_2022-06_a_2026-09.xlsx'));
console.log(JSON.stringify({sheets:data.sheets.length,formulas:formulas.length,output:'levantamento_financeiro_CSG_2022-06_a_2026-09.xlsx'}));
