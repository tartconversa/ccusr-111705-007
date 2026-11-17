"""本地业务页面交互。"""

def detail_fragment(item):
    return "<button id=\"access\" aria-haspopup=\"dialog\">服务说明</button><div id=\"access-dialog\" role=\"dialog\" hidden><button id=\"dismiss\">关闭说明</button><p>键盘可达的服务条款</p></div><select id=\"floor\"><option>一层</option><option>二层</option></select><output id=\"service-day\">周二开放</output><script>let floor=document.querySelector('#floor'),dialog=document.querySelector('#access-dialog'),access=document.querySelector('#access');floor.onchange=()=>{dialog.hidden=true;document.querySelector('#service-day').textContent=floor.value==='一层'?'周二开放':'周四开放'};access.onclick=()=>{dialog.hidden=false;document.querySelector('#dismiss').focus()};document.querySelector('#dismiss').onclick=()=>{dialog.hidden=true;access.focus()};</script>"

def source_extension(item):
    return f"""<output id="assistance-preview" data-service="{item['id']}"></output><script>(()=>{{
let assistance=document.querySelector('#assistance-preview'),floor=document.querySelector('#floor'),dialog=document.querySelector('#access-dialog');
let viewedFloor='';floor.addEventListener('change',()=>{{assistance.textContent='';viewedFloor='';}});
document.querySelector('#access').addEventListener('click',()=>{{viewedFloor=floor.value;}});
document.querySelector('#preview').addEventListener('click',()=>{{assistance.textContent=floor.value+' / '+document.querySelector('#service-day').textContent+'：'+(viewedFloor===floor.value?'服务说明已打开':'说明待核对');}});
}})();</script>"""
