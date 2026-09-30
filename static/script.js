const $ = id => document.getElementById(id);
const ids = ["nominal_v","fault_current","pickup","fault_duration","dead_time","max_reclose","bus_v","line_v","min_bus_v_pu","max_delta_v_pu","bus_f","line_f","max_delta_f","phase_angle","max_phase","fault_clears"];

function data(){
  const d={}; ids.forEach(id=>d[id]=$(id).value); return d;
}
function setCheck(id,val){
  const e=$(id); e.classList.remove("ok","bad");
  e.querySelector("i").textContent=val?"✓ PASS":"✕ FAIL";
  e.classList.add(val?"ok":"bad");
}
function clearChecks(){
  ["checkOver","checkBus","checkLine","checkDV","checkDF","checkPhase","checkCount"].forEach(id=>{
    const e=$(id);e.classList.remove("ok","bad");e.querySelector("i").textContent="—";
  });
}
function resetVisual(){
  document.body.classList.remove("running");
  $("recloserBox").classList.remove("open");
  $("faultZone").classList.remove("fault","isolated");
  $("faultText").textContent="LOAD"; $("faultSub").textContent="Energized";
  $("cbText").textContent="CLOSED"; $("scenarioBadge").textContent="NORMAL";
  $("globalStatus").innerHTML="<span></span> READY";
  $("decisionResult").textContent="WAITING FOR SIMULATION";
  $("decisionResult").className="decision-result";
  const d=data();
  $("mBus").textContent=d.bus_v+" kV"; $("mLine").textContent=d.line_v+" kV";
  $("mDV").textContent=((Math.abs(Number(d.bus_v)-Number(d.line_v))/Number(d.nominal_v))*100).toFixed(1)+" %";
  $("mDF").textContent=Math.abs(Number(d.bus_f)-Number(d.line_f)).toFixed(2)+" Hz";
  $("mPhase").textContent=d.phase_angle+"°"; $("mCount").textContent="0 / "+d.max_reclose;
  $("busLabel").textContent=d.bus_v+" kV • "+d.bus_f+" Hz";
  clearChecks();
  $("eventLog").innerHTML='<div class="empty">Chưa có sự kiện. Nhấn “CHẠY MÔ PHỎNG”.</div>';
}
function addEvent(ev){
  const log=$("eventLog"); const empty=log.querySelector(".empty"); if(empty) empty.remove();
  const row=document.createElement("div"); row.className="event "+(ev.type||"");
  row.innerHTML=`<span class="time">${ev.time}</span>${ev.text}`; log.appendChild(row); log.scrollTop=log.scrollHeight;
}
function updateMetrics(d,res){
  $("mBus").textContent=d.bus_v+" kV"; $("mLine").textContent=d.line_v+" kV";
  $("mDV").textContent=(res.metrics.delta_v_pu*100).toFixed(1)+" %";
  $("mDF").textContent=res.metrics.delta_f.toFixed(2)+" Hz";
  $("mPhase").textContent=d.phase_angle+"°";
  $("mCount").textContent=`${res.reclose_count} / ${d.max_reclose}`;
}
async function run(){
  resetVisual(); document.body.classList.add("running");
  $("globalStatus").innerHTML="<span></span> RUNNING"; $("eventLog").innerHTML="";
  const d=data();
  try{
    const r=await fetch("/api/simulate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)});
    const res=await r.json(); if(!res.ok) throw new Error(res.error||"Simulation error");
    updateMetrics(d,res);
    for(const ev of res.events){
      addEvent(ev);
      const t=ev.text.toLowerCase();
      if(t.includes("fault detected")){ $("faultZone").classList.add("fault"); $("faultText").textContent="FAULT"; $("faultSub").textContent="Abnormal"; $("scenarioBadge").textContent="FAULT"; }
      if(t.includes("cb open")||t.includes("trip")){ $("recloserBox").classList.add("open"); $("cbText").textContent="OPEN"; $("faultZone").classList.add("isolated"); }
      if(t.includes("dead time")){ $("faultZone").classList.add("isolated"); $("scenarioBadge").textContent="CHECKING"; }
      if(t.includes("auto reclose")&&t.includes("closed")){ $("recloserBox").classList.remove("open"); $("cbText").textContent="CLOSED"; $("scenarioBadge").textContent="RECLOSING"; $("faultZone").classList.remove("isolated"); }
      if(t.includes("fault cleared")){ $("faultZone").classList.remove("fault","isolated"); $("faultText").textContent="LOAD"; $("faultSub").textContent="Energized"; }
      if(t.includes("lockout")){ $("scenarioBadge").textContent="LOCKOUT"; $("recloserBox").classList.add("open"); $("cbText").textContent="LOCKOUT"; }
      await new Promise(resolve=>setTimeout(resolve,430));
    }
    const c=res.checks;
    setCheck("checkOver",c.overcurrent); setCheck("checkBus",c.bus_voltage_ok); setCheck("checkLine",c.line_voltage_ok);
    setCheck("checkDV",c.voltage_diff_ok); setCheck("checkDF",c.frequency_ok); setCheck("checkPhase",c.phase_ok);
    setCheck("checkCount",res.reclose_count<=Number(d.max_reclose));
    const dr=$("decisionResult"); dr.textContent=res.outcome_label;
    dr.className="decision-result "+(res.outcome==="SUCCESS"?"success":(res.outcome==="NORMAL"?"info":"danger"));
    if(res.outcome==="SUCCESS"){ $("globalStatus").innerHTML="<span></span> SYSTEM RESTORED"; $("scenarioBadge").textContent="RESTORED"; }
    else if(res.outcome==="LOCKOUT"){ $("globalStatus").innerHTML="<span></span> LOCKOUT"; }
    else if(res.outcome==="OPERATOR"){ $("globalStatus").innerHTML="<span></span> OPERATOR REQUIRED"; }
    else $("globalStatus").innerHTML="<span></span> NORMAL";
  }catch(e){$("decisionResult").textContent="ERROR: "+e.message;$("decisionResult").className="decision-result danger";$("globalStatus").innerHTML="<span></span> ERROR";}
}
$("runBtn").addEventListener("click",run);
$("resetBtn").addEventListener("click",resetVisual);
$("faultBtn").addEventListener("click",()=>{
  $("fault_current").value=Math.max(Number($("pickup").value)+0.5,2.5);
  $("fault_clears").value="yes"; run();
});
resetVisual();
