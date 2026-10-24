'use strict';
const menu=document.querySelector('#menu-toggle'), sidebar=document.querySelector('#sidebar'), backdrop=document.querySelector('.nav-backdrop');
function closeMenu(){sidebar.classList.remove('visible');menu?.setAttribute('aria-expanded','false');backdrop.hidden=true;}
menu?.addEventListener('click',()=>{const open=sidebar.classList.toggle('visible');menu.setAttribute('aria-expanded',String(open));backdrop.hidden=!open;});
backdrop?.addEventListener('click',closeMenu);
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeMenu();});
sidebar?.querySelectorAll('a').forEach(a=>a.addEventListener('click',closeMenu));
const themeButton=document.querySelector('.theme-toggle');
function setTheme(value){document.documentElement.dataset.theme=value;themeButton?.setAttribute('aria-label',value==='light'?'Chuyển giao diện tối':'Chuyển giao diện sáng');}
try{setTheme(localStorage.getItem('arena-theme')||'dark');}catch{setTheme('dark');}
themeButton?.addEventListener('click',()=>{const value=document.documentElement.dataset.theme==='light'?'dark':'light';setTheme(value);try{localStorage.setItem('arena-theme',value);}catch{}});
document.querySelectorAll('.nav-item').forEach(a=>{if(new URL(a.href).pathname===location.pathname){a.classList.add('active');a.setAttribute('aria-current','page');}});
document.querySelectorAll('[data-print]').forEach(b=>b.addEventListener('click',()=>window.print()));
document.querySelectorAll('[data-back]').forEach(b=>b.addEventListener('click',()=>{if(history.length>1)history.back();else location.assign('/');}));
// Password visibility never changes the field value or sends a request.
document.querySelectorAll('input[type=password]').forEach(input=>{const wrap=document.createElement('div');wrap.className='password-control';input.before(wrap);wrap.append(input);const button=document.createElement('button');button.type='button';button.textContent='Hiện';button.setAttribute('aria-label','Hiện mật khẩu');button.addEventListener('click',()=>{const show=input.type==='password';input.type=show?'text':'password';button.textContent=show?'Ẩn':'Hiện';button.setAttribute('aria-label',show?'Ẩn mật khẩu':'Hiện mật khẩu');});wrap.append(button);});
const resultForm=document.querySelector('#kda-form');
function checkLineup(){
 if(!resultForm)return true;
 const counts=new Map();let chosen=0;
 resultForm.querySelectorAll('[name=selected]').forEach(box=>{
  const row=box.closest('tr'),team=resultForm.elements['team_'+box.value].value;
  if(!counts.has(team))counts.set(team,0);
  if(box.checked){counts.set(team,counts.get(team)+1);chosen++;}
  row.classList.toggle('unselected',!box.checked);
  row.querySelectorAll('input[type=number],select').forEach(el=>{el.disabled=!box.checked;if(el.type==='number'&&!el.name.startsWith('g_'))el.required=box.checked;});
 });
 const valid=counts.size===2&&[...counts.values()].every(n=>n===5);
 document.querySelector('#lineup-feedback').textContent=`Ra sân: ${chosen}/10 · Mỗi đội: ${[...counts.values()].join(' / ')} người${valid?' · Đội hình hợp lệ':' · Cần đúng 5 người mỗi đội'}`;
 return valid;
}
resultForm?.addEventListener('change',checkLineup);checkLineup();
document.querySelectorAll('form').forEach(form=>form.addEventListener('submit',event=>{
 if(form===resultForm&&!checkLineup()){event.preventDefault();document.querySelector('#lineup-feedback').scrollIntoView({block:'center'});return;}
 if(form.dataset.confirm&&!confirm(form.dataset.confirm)){event.preventDefault();return;}
 if(form.dataset.sending){event.preventDefault();return;}
 form.dataset.sending='1';
 setTimeout(()=>form.querySelectorAll('button[type=submit],button:not([type])').forEach(b=>{b.disabled=true;b.dataset.label=b.textContent;b.textContent='Đang xử lý…';}),0);
}));
window.addEventListener('pageshow',()=>document.querySelectorAll('form').forEach(f=>{delete f.dataset.sending;f.querySelectorAll('button[data-label]').forEach(b=>{b.disabled=false;b.textContent=b.dataset.label;delete b.dataset.label;});}));
const search=document.querySelector('#event-search');let selectedFilter='all';
const normalize=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLocaleLowerCase('vi');
function filterEvents(){let found=0;const key=normalize(search?.value.trim()||'');document.querySelectorAll('[data-event-name]').forEach(card=>{card.hidden=!normalize(card.dataset.eventName).includes(key)||(selectedFilter!=='all'&&card.dataset.eventStatus!==selectedFilter);if(!card.hidden)found++;});const empty=document.querySelector('#search-empty');if(empty)empty.hidden=found>0;const count=document.querySelector('#filter-count');if(count)count.textContent=found+' giải đấu';}
search?.addEventListener('input',filterEvents);
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{selectedFilter=button.dataset.filter;document.querySelectorAll('[data-filter]').forEach(b=>{const active=b===button;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});filterEvents();}));filterEvents();
document.querySelectorAll('[data-roster]').forEach(box=>box.addEventListener('change',()=>{if(box.checked)document.querySelectorAll('[data-roster="'+box.dataset.roster+'"]').forEach(other=>{if(other!==box)other.checked=false;});const count=document.querySelector('#roster-count');if(count)count.textContent=`Đã chọn ${document.querySelectorAll('[name="starters"]:checked').length}/5 chính · ${document.querySelectorAll('[name="reserves"]:checked').length} dự bị`;}));
resultForm?.addEventListener('keydown',event=>{if(event.ctrlKey&&event.key==='Enter'){event.preventDefault();event.currentTarget.requestSubmit();}});
const live=document.querySelector('[data-live-event]');
if(live){let signature=null,busy=false;
 async function poll(){if(document.hidden||busy)return;busy=true;try{const response=await fetch(`/api/events/${live.dataset.liveEvent}/state`,{cache:'no-store'});if(!response.ok)throw Error();const data=await response.json(),next=data.status+'|'+data.signature;
 if(signature!==null&&next!==signature){const response2=await fetch(location.href,{cache:'no-store'});if(!response2.ok)throw Error();const page=new DOMParser().parseFromString(await response2.text(),'text/html');for(const id of ['live-region','standings']){const replacement=page.querySelector('#'+id),current=document.querySelector('#'+id);if(replacement&&current)current.replaceWith(replacement);}}
 signature=next;live.textContent='Đã đồng bộ · '+new Date().toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
 }catch{live.textContent='Mất kết nối · tự thử lại sau 8 giây';}finally{busy=false;}}
 poll();setInterval(poll,8000);
}
