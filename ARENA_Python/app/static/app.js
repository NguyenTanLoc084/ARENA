'use strict';
const menu=document.querySelector('#menu-toggle');
menu?.addEventListener('click',()=>{const open=document.querySelector('#sidebar').classList.toggle('visible');menu.setAttribute('aria-expanded',String(open));});
document.querySelectorAll('[data-print]').forEach(b=>b.addEventListener('click',()=>window.print()));
document.querySelectorAll('[data-back]').forEach(b=>b.addEventListener('click',()=>{if(history.length>1)history.back();else location.assign('/');}));
document.querySelectorAll('form').forEach(form=>form.addEventListener('submit',event=>{
 if(form.dataset.confirm&&!confirm(form.dataset.confirm)){event.preventDefault();return;}
 if(form.dataset.sending){event.preventDefault();return;}
 form.dataset.sending='1';
 // Defer disabling so the clicked button's name/value is included in form data.
 setTimeout(()=>form.querySelectorAll('button').forEach(b=>{b.disabled=true;b.dataset.label=b.textContent;b.textContent='Đang xử lý…';}),0);
}));
window.addEventListener('pageshow',()=>document.querySelectorAll('form').forEach(f=>{delete f.dataset.sending;f.querySelectorAll('button').forEach(b=>{b.disabled=false;if(b.dataset.label)b.textContent=b.dataset.label;});}));
const search=document.querySelector('#event-search');
search?.addEventListener('input',()=>{let found=0;const key=search.value.trim().toLocaleLowerCase('vi');document.querySelectorAll('[data-event-name]').forEach(card=>{card.hidden=!card.dataset.eventName.includes(key);if(!card.hidden)found++;});document.querySelector('#search-empty').hidden=found>0;});
document.querySelectorAll('[data-roster]').forEach(box=>box.addEventListener('change',()=>{if(box.checked)document.querySelectorAll('[data-roster="'+box.dataset.roster+'"]').forEach(other=>{if(other!==box)other.checked=false;});const count=document.querySelector('#roster-count');if(count)count.textContent=`Đã chọn ${document.querySelectorAll('[name="starters"]:checked').length}/5 chính · ${document.querySelectorAll('[name="reserves"]:checked').length} dự bị`;}));
document.querySelector('#kda-form')?.addEventListener('keydown',event=>{if(event.ctrlKey&&event.key==='Enter'){event.preventDefault();event.currentTarget.requestSubmit();}});
const live=document.querySelector('[data-live-event]');
if(live){
 let signature=null,busy=false;
 async function poll(){
  if(document.hidden||busy)return;busy=true;
  try{
   const response=await fetch(`/api/events/${live.dataset.liveEvent}/state`,{cache:'no-store'});if(!response.ok)throw Error('offline');
   const data=await response.json();const next=data.status+'|'+data.signature;
   if(signature!==null&&next!==signature){const response2=await fetch(location.href,{cache:'no-store'});if(!response2.ok)throw Error('offline');const page=new DOMParser().parseFromString(await response2.text(),'text/html');const replacement=page.querySelector('#live-region');if(replacement)document.querySelector('#live-region').replaceWith(replacement);}
   signature=next;live.textContent='Đã đồng bộ · '+new Date().toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  }catch{live.textContent='Mất kết nối · tự thử lại sau 8 giây';}
  finally{busy=false;}
 }
 poll();setInterval(poll,8000);
}
