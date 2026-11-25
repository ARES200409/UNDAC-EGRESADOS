/* V11. Gráficos agregados. No carga ni muestra datos personales. */
(() => {
'use strict';
const section = document.querySelector('[data-v11-graficos]');
if (!section) return;
const source = document.getElementById('v11-data-inicial');
const status = document.getElementById('v11-status');
const btn = document.getElementById('v11-refrescar');
let datos;try { datos=JSON.parse(source?.textContent||'{}'); } catch(e) { return; }
const instancias = new Map();
const byId = (id)=>document.getElementById('v11-chart-'+id);
const empty = (id)=>document.getElementById('v11-empty-'+id);
const colors = ()=>{const dark=document.documentElement.dataset.theme==='dark';return {ink: dark?'#f3fbff':'#0b3c70',muted:dark?'#bfd4e5':'#536e86',grid:dark?'#3d5e71':'#d4e9f4',accent:'#1497ed',sky:'#4ed5e0',grey:dark?'#486d81':'#bed4e1'};};
function barOption(names,values,vertical=false) {
  const c=colors();return {animationDuration:350,tooltip:{trigger:'axis',axisPointer:{type:'shadow'}},grid:{left:38,right:18,bottom:vertical?55:25,top:20,containLabel:true},
    xAxis: vertical?{type:'category',data:names,axisLabel:{color:c.muted,interval:0,rotate:names.length>5?25:0},axisLine:{lineStyle:{color:c.grid}}}:{type:'value',minInterval:1,axisLabel:{color:c.muted},splitLine:{lineStyle:{color:c.grid}}},
    yAxis: vertical?{type:'value',minInterval:1,axisLabel:{color:c.muted},splitLine:{lineStyle:{color:c.grid}}}:{type:'category',data:names,axisLabel:{color:c.muted},axisLine:{lineStyle:{color:c.grid}}},
    series:[{type:'bar',data:values,itemStyle:{color:c.accent,borderRadius:vertical?[5,5,0,0]:[0,5,5,0]},barMaxWidth:40,label:{show:true,position:vertical?'top':'right',color:c.ink}}]};}
function donutOption(yes,no,yesTitle,noTitle){const c=colors();return {tooltip:{trigger:'item',formatter:'{b}: {c} ({d}%)'},legend:{bottom:0,textStyle:{color:c.muted}},series:[{type:'pie',radius:['50%','70%'],center:['50%','44%'],label:{show:false},data:[{name:yesTitle,value:yes,itemStyle:{color:c.accent}},{name:noTitle,value:no,itemStyle:{color:c.grey}}]}]};}
function svgNode(tag,attributes={},value=''){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [key,val] of Object.entries(attributes))n.setAttribute(key,String(val));if(value)n.textContent=value;return n;}
/* Si ECharts no carga, los gráficos se dibujan en SVG local. Nunca usa innerHTML con datos de usuario. */
function svgFallback(container,option,id){
  const c=colors(),s=svgNode('svg',{viewBox:'0 0 670 240',width:'100%',height:'100%',role:'img','aria-label':'Gráfico '+id});
  const series=option.series?.[0];if(!series)return;
  if(series.type==='bar'){
    const names=(option.xAxis?.type==='category'?option.xAxis.data:option.yAxis?.data)||[];
    const values=series.data||[],max=Math.max(1,...values.map(Number)),n=Math.max(1,names.length);
    values.forEach((v,i)=>{
      const y=12+i*(215/n),h=Math.min(28,175/n),w=420*Number(v)/max;
      const label=String(names[i]||'').slice(0,26);
      s.appendChild(svgNode('text',{x:12,y:y+h*.8,fill:c.muted,'font-size':14},label));
      s.appendChild(svgNode('rect',{x:205,y,width:420,height:h,rx:5,fill:c.grid,opacity:0.45}));
      const bar=svgNode('rect',{x:205,y,width:w,height:h,rx:5,fill:c.accent});
      bar.appendChild(svgNode('title',{},`${names[i]}: ${v}`));s.appendChild(bar);
      s.appendChild(svgNode('text',{x:Math.min(625,212+w),y:y+h*.8,fill:c.ink,'font-size':13,'font-weight':700},String(v)));
    });
  }else if(series.type==='pie'){
    const parts=series.data||[],v1=Number(parts[0]?.value||0),v2=Number(parts[1]?.value||0),total=v1+v2;
    const x=245,y=105,radius=75,circ=2*Math.PI*radius;
    s.appendChild(svgNode('circle',{cx:x,cy:y,r:radius,fill:'none',stroke:c.grey,'stroke-width':24}));
    if(total>0){const arc=svgNode('circle',{cx:x,cy:y,r:radius,fill:'none',stroke:c.accent,'stroke-width':24,'stroke-dasharray':`${circ*(v1/total)} ${circ}`,'stroke-dashoffset':0,transform:`rotate(-90 ${x} ${y})`});arc.appendChild(svgNode('title',{},`${parts[0].name}: ${v1}`));s.appendChild(arc);}
    s.appendChild(svgNode('text',{x,y:107,fill:c.ink,'font-weight':800,'font-size':22,'text-anchor':'middle'},total>0?`${(100*v1/total).toFixed(1)} %`:'N/D'));
    s.appendChild(svgNode('circle',{cx:438,cy:93,r:6,fill:c.accent}));
    s.appendChild(svgNode('text',{x:451,y:98,fill:c.muted,'font-size':13},`${(parts[0]?.name||'Con registro').slice(0,25)}: ${v1}`));
    s.appendChild(svgNode('circle',{cx:438,cy:128,r:6,fill:c.grey}));
    s.appendChild(svgNode('text',{x:451,y:133,fill:c.muted,'font-size':13},`${(parts[1]?.name||'Sin registro').slice(0,25)}: ${v2}`));
  }
  container.replaceChildren(s);
}
function render(id,active,option){const box=byId(id), message=empty(id);if(!box)return;
  if(!active){box.style.display='none';if(message)message.hidden=false;return;}
  box.style.display='block';if(message)message.hidden=true;
  if(!window.echarts){svgFallback(box,option,id);return;}
  let chart=instancias.get(id);if(!chart){box.replaceChildren();chart=window.echarts.init(box,null,{renderer:'svg'});instancias.set(id,chart);}chart.setOption(option,true);chart.resize();}
function update(){const p=datos.promociones||[],cu=datos.curriculas||[],total=Number(datos.total||0),con=Math.min(Number(datos.cuentas||0),total),empleo=Math.min(Number(datos.empleos||0),total);
 render('promociones',p.length>0,barOption(p.map(x=>x.anio),p.map(x=>x.total),true));
 const role=section.querySelector('[data-role]')?.dataset.role;
 const part=role==='utsag'?Math.min(Number(datos.participantes_encuestas||0),total):con;
 if(role==='utsag' && total>0 && part===0){ const m=empty('cobertura');if(m)m.textContent='Aún no se recibieron respuestas a encuestas en el ámbito autorizado. 0 respuestas no representa ausencia de participación futura.';}
 render('cobertura',total>0 && (role!=='utsag' || part>0),donutOption(part,total-part,role==='utsag'?'Con respuestas':'Con cuenta',role==='utsag'?'Sin respuesta registrada':'Sin cuenta activa'));
 if(total>0 && empleo===0){const m=empty('empleo');if(m)m.textContent='Ningún egresado ha registrado un empleo actual. Esto NO equivale a desempleo ni a una tasa de empleabilidad.';}
 render('empleo',total>0 && empleo>0,donutOption(empleo,total-empleo,'Empleo actual declarado','Sin empleo actual registrado'));
 render('curriculas',cu.length>0,barOption(cu.map(x=>x.nombre),cu.map(x=>x.total)));}
function resize(){instancias.forEach(c=>c.resize());}
update();
window.addEventListener('resize',resize,{passive:true});window.addEventListener('nexo:theme-changed',update);
if(btn){btn.addEventListener('click',async()=>{btn.disabled=true;status.textContent='Consultando indicadores autorizados en MySQL…';try{const res=await fetch(section.dataset.api,{credentials:'same-origin',headers:{Accept:'application/json'},cache:'no-store'});if(!res.ok)throw new Error('HTTP '+res.status);const body=await res.json();datos=body.indicadores;update();status.textContent='Indicadores actualizados desde MySQL. Los datos no informados no equivalen a resultados negativos.';}catch(e){status.textContent='No fue posible actualizar. Puedes recargar la página y volver a intentarlo.';}finally{btn.disabled=false;}});}
})();
